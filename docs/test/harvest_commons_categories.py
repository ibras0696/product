#!/usr/bin/env python3
"""Добавляет фотографии из Commons-категорий объектов Wikidata.

P18 обычно даёт одно главное изображение. P373 указывает категорию Commons;
из неё берутся до трёх файлов, каждый с автором и лицензией. Все результаты
остаются ``needs_review``: принадлежность фотографии объекту проверяет редактор.
"""

from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPARQL_URL = "https://query.wikidata.org/sparql"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "ChechnyaHistoryResearch/1.0"
TAG_RE = re.compile(r"<[^>]+>")
MAX_CATEGORIES = 30
FILES_PER_CATEGORY = 3


def request_json(url: str, params: dict, attempts: int = 4) -> dict:
    request = urllib.request.Request(
        f"{url}?{urllib.parse.urlencode(params)}", headers={"User-Agent": USER_AGENT}
    )
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.load(response)
            time.sleep(1)
            return payload
        except urllib.error.HTTPError as error:
            if attempt + 1 == attempts:
                raise
            delay = 10 * (attempt + 1) if error.code == 429 else 2 ** attempt
            time.sleep(delay)
        except Exception:
            if attempt + 1 == attempts:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def clean(value: str | None) -> str | None:
    if not value:
        return None
    result = re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", value))).strip()
    return result or None


def owners() -> dict[str, str]:
    payload = json.loads((HERE / "harvested_data.json").read_text(encoding="utf-8"))
    result = {}
    for kind, collection in (("place", payload["places"]), ("person", payload["people"]),
                             ("event", payload["events"])):
        for row in collection:
            result[row["external_id"]] = kind
    return result


def categories(owner_map: dict[str, str]) -> list[tuple[str, str, str]]:
    query = """
    SELECT DISTINCT ?item ?category WHERE {
      { ?item wdt:P131* wd:Q5187; wdt:P373 ?category. }
      UNION { ?item wdt:P19/wdt:P131* wd:Q5187; wdt:P570 ?death; wdt:P373 ?category. }
      UNION { ?item wdt:P172 wd:Q31230; wdt:P570 ?death; wdt:P373 ?category. }
    }
    """
    data = request_json(SPARQL_URL, {"format": "json", "query": query})
    result = []
    for binding in data["results"]["bindings"]:
        qid = binding["item"]["value"].rsplit("/", 1)[-1]
        if qid in owner_map:
            result.append((owner_map[qid], qid, f"Category:{binding['category']['value']}"))
    return result[:MAX_CATEGORIES]


def category_files(category_rows: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    result = []
    for kind, qid, category in category_rows:
        data = request_json(COMMONS_API, {
            "action": "query", "format": "json", "list": "categorymembers",
            "cmtitle": category, "cmnamespace": "6", "cmtype": "file",
            "cmlimit": str(FILES_PER_CATEGORY),
        })
        result.extend((kind, qid, item["title"]) for item in data["query"]["categorymembers"])
    return result


def metadata(indexed: list[tuple[str, str, str]]) -> list[dict]:
    existing = json.loads((HERE / "harvested_data.json").read_text(encoding="utf-8"))
    existing_pages = {row["file_page_url"] for row in existing["media_assets"]}
    owners_by_title: dict[str, list[tuple[str, str]]] = {}
    for kind, qid, title in indexed:
        owners_by_title.setdefault(title, []).append((kind, qid))
    result = []
    titles = sorted(owners_by_title)
    for offset in range(0, len(titles), 50):
        data = request_json(COMMONS_API, {
            "action": "query", "format": "json", "prop": "imageinfo",
            "iiprop": "url|extmetadata", "titles": "|".join(titles[offset:offset + 50]),
        })
        for page in data["query"]["pages"].values():
            if not page.get("imageinfo"):
                continue
            info = page["imageinfo"][0]
            if info["descriptionurl"] in existing_pages:
                continue
            meta = info.get("extmetadata", {})
            value = lambda key: meta.get(key, {}).get("value")
            license_name = value("LicenseShortName") or value("License")
            if not license_name:
                continue
            for kind, qid in owners_by_title.get(page["title"], []):
                result.append({
                    "owner_type": kind, "owner_external_id": qid,
                    "commons_title": page["title"], "file_page_url": info["descriptionurl"],
                    "original_url": info["url"], "artist": clean(value("Artist")),
                    "credit": clean(value("Credit")), "license": license_name,
                    "license_url": value("LicenseUrl"), "verification_status": "needs_review",
                    "source": "wikimedia_commons",
                })
    return result


def harvest() -> list[dict]:
    owner_map = owners()
    return metadata(category_files(categories(owner_map)))


if __name__ == "__main__":
    rows = harvest()
    (HERE / "additional_media.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Сохранено дополнительных медиа: {len(rows)}")
