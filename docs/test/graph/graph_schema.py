"""Словарь типов графа и гигиена пользовательского текста.

Здесь только справочные соответствия (place_type -> тип узла, relation -> тип
ребра) и чистые функции нормализации/очистки текста. Никаких обращений к БД или
файловой системе — их держит build_graph.py.
"""

from __future__ import annotations

import math
import re
import sqlite3
import unicodedata

# Прямоугольник Чечни (щедрый, чтобы не терять приграничные объекты, но
# отсекать внешние места из чужих биографий — Анапа, Шлиссельбург и т.п.).
CHECHNYA_LAT = (42.0, 44.2)
CHECHNYA_LON = (44.5, 47.0)
GEO_CONFIRM_M = 2000.0  # порог гео-подтверждения born_in по свидетельству OSM

# Признаки связи с Чечнёй по названию/тексту (для harvested-строк без района).
CHECHNYA_KEYWORDS = (
    "чечен", "чечн", "ичкери", "нохч", "вайнах", "грозн", "аргун", "сунж",
    "терек", "гудермес", "урус март", "ачхой", "шали", "шатой", "ведено",
    "итум", "ножай", "курчал", "шелков", "надтеречн", "наурск", "шарой",
    "серноводск", "кавказск",
)

# place_type исходной БД -> тип узла графа (значения EntityType бэкенда).
PLACE_TYPE_TO_NODE = {
    "city": "settlement", "town": "settlement", "village": "settlement",
    "locality": "settlement",
    "fortress": "landmark", "tower_complex": "landmark", "memorial": "landmark",
    "mosque": "cultural_object", "museum": "cultural_object",
    "lake": "natural_object", "river": "natural_object", "mountain": "natural_object",
}
NODE_FILE = {
    "settlement": "settlements", "person": "people", "event": "events",
    "landmark": "landmarks", "cultural_object": "cultural_objects",
    "natural_object": "natural_objects", "artifact": "discoveries",
}

# Схема бэкенда: EntityType -> категория интерфейса (функция entityKind()
# во frontend/.../exploration/api/explorationApi.ts). Пять категорий легенды карты.
ENTITY_KIND = {
    "person": "person",
    "event": "event",
    "artifact": "source",
    "settlement": "place",
    "natural_object": "place",
    "landmark": "landmark",
    "cultural_object": "landmark",
    "organization": "landmark",
    "university_object": "landmark",
}
CATEGORY_FILE = {
    "place": "naselennye-punkty", "person": "lichnosti", "event": "sobytiya",
    "landmark": "dostoprimechatelnosti", "source": "istochniki",
}
CATEGORY_TITLE = {
    "place": "Населённые пункты", "person": "Личности", "event": "События",
    "landmark": "Достопримечательности", "source": "Источники",
}
PLACE_TYPE_LABEL = {
    "city": "Город", "town": "Город", "village": "Село", "locality": "Населённый пункт",
    "fortress": "Крепость", "tower_complex": "Башенный комплекс", "memorial": "Мемориал",
    "mosque": "Мечеть", "museum": "Музей",
    "lake": "Озеро", "river": "Река", "mountain": "Гора",
}
# residences.relation -> (RelationType бэкенда, человекочитаемый заголовок ребра).
RESIDENCE_RELATION = {
    "born": ("born_in", "Родился в"),
    "lived": ("lived_in", "Жил в"),
    "worked": ("worked_in", "Работал в"),
    "died": ("connected_with", "Умер в"),
    "buried": ("connected_with", "Похоронен в"),
    "commemorated": ("connected_with", "Увековечен в"),
}
JUNK_MARKERS = (
    "Внешний идентификатор", "URL записи источника", "Источник координат",
    "Статус исследования", "заявленная точность", "Точность:", "Wikidata:",
)


# Русские (славянские) личные имена — по ним harvested-персоны, не относящиеся к
# чеченскому корпусу (родившиеся в Грозном русские и т.п.), отсекаются из «Личностей».
# Применяется только к массовым Wikidata-строкам; курируемых героев не трогает.
RUSSIAN_FIRST_NAMES = frozenset({
    "андрей", "николай", "михаил", "владимир", "александр", "сергей", "иван",
    "петр", "дмитрий", "алексей", "виктор", "юрий", "анатолий", "борис",
    "григорий", "василий", "павел", "евгений", "олег", "константин", "леонид",
    "геннадий", "валерий", "вячеслав", "станислав", "вадим", "игорь", "роман",
    "денис", "артем", "кирилл", "федор", "егор", "глеб", "семен", "тимофей",
    "матвей", "аркадий", "валентин", "виталий", "всеволод", "даниил", "ефим",
    "захар", "лев", "родион", "святослав", "тарас", "трофим", "филипп", "яков",
    "эдуард", "герман", "аполлон", "лаврентий", "спиридон",
    "анна", "елена", "ольга", "наталья", "наталия", "татьяна", "ирина",
    "светлана", "екатерина", "марина", "людмила", "галина", "валентина", "нина",
    "вера", "надежда", "любовь", "раиса", "лидия", "зинаида", "антонина",
    "клавдия", "евгения", "полина", "ксения", "дарья", "анастасия", "юлия",
})


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().replace("ё", "е")
    return re.sub(r"[^a-zа-я0-9]+", " ", value).strip()


def looks_russian(name_ru: str) -> bool:
    return any(token in RUSSIAN_FIRST_NAMES for token in norm(name_ru).split())


def clean_text(text: str | None) -> str:
    """Обрезает технический хвост и мусорные маркеры из текста для пользователя."""
    if not text:
        return ""
    cut = len(text)
    for marker in JUNK_MARKERS:
        idx = text.find(marker)
        if idx != -1:
            cut = min(cut, idx)
    return re.sub(r"\s+", " ", text[:cut]).strip(" .;,").strip()


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def in_chechnya(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None:
        return False
    return CHECHNYA_LAT[0] <= lat <= CHECHNYA_LAT[1] and CHECHNYA_LON[0] <= lon <= CHECHNYA_LON[1]


def aliases(alt_names: str | None) -> list[str]:
    if not alt_names:
        return []
    parts = re.split(r"[;,/]", alt_names)
    return [p.strip() for p in parts if p.strip()]


def place_description(row: sqlite3.Row, district_name: str | None) -> tuple[str, bool]:
    """Чистый пользовательский текст места; второй флаг — 'слабое описание'."""
    cleaned = clean_text(row["description"])
    if len(cleaned) >= 12:
        return cleaned, False
    label = PLACE_TYPE_LABEL.get(row["place_type"], "Объект")
    if district_name:
        return f"{label}, {district_name}, Чеченская Республика.", True
    return f"{label}, Чеченская Республика.", True


def provenance(record_url: str | None, coord_url: str | None, evidence: dict | None) -> dict:
    prov: dict[str, object] = {}
    if record_url:
        prov["record_url"] = record_url
    if coord_url and coord_url != record_url:  # не дублируем одинаковые ссылки
        prov["coordinate_source_url"] = coord_url
    if evidence:
        prov["osm_evidence"] = evidence
    return prov
