-- Схема исследовательской БД «История Чечни».
-- Назначение: собрать проверяемые факты о местностях, личностях (героях),
-- событиях (в т.ч. войнах), подвигах и о том, где герои жили.
--
-- Принцип достоверности: строки с историческими фактами несут source_id и
-- verification_status. По умолчанию 'needs_review' — данные подтверждает
-- владелец контента ПЕРЕД публикацией (см. BR-008 в TZ.md). ИИ факты не
-- создаёт: этот seed скомпонован из указанных источников.

PRAGMA foreign_keys = ON;

DROP VIEW  IF EXISTS v_hero_birthplaces;
DROP VIEW  IF EXISTS v_place_people;
DROP VIEW  IF EXISTS v_research_queue;
DROP VIEW  IF EXISTS v_fact_evidence;
DROP TABLE IF EXISTS fact_citations;
DROP TABLE IF EXISTS source_documents;
DROP TABLE IF EXISTS coordinate_evidence;
DROP TABLE IF EXISTS media_assets;
DROP TABLE IF EXISTS person_events;
DROP TABLE IF EXISTS residences;
DROP TABLE IF EXISTS deeds;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS people;
DROP TABLE IF EXISTS places;
DROP TABLE IF EXISTS districts;
DROP TABLE IF EXISTS sources;

-- Источники истины для каждого факта.
CREATE TABLE sources (
    id           INTEGER PRIMARY KEY,
    slug         TEXT UNIQUE NOT NULL,
    title        TEXT NOT NULL,
    publisher    TEXT,
    url          TEXT,
    source_type  TEXT CHECK (source_type IN
                   ('encyclopedia','official','museum','media','academic',
                    'dataset','media_repository')),
    reliability  TEXT CHECK (reliability IN ('high','medium','low')) DEFAULT 'medium',
    notes        TEXT
);

-- Административные районы Чеченской Республики.
CREATE TABLE districts (
    id           INTEGER PRIMARY KEY,
    slug         TEXT UNIQUE NOT NULL,
    name_ru      TEXT NOT NULL,
    name_ce      TEXT,
    admin_center TEXT,
    notes        TEXT,
    verification_status TEXT NOT NULL DEFAULT 'needs_review'
                CHECK (verification_status IN ('verified','corroborated','needs_review')),
    source_id INTEGER REFERENCES sources(id)
);

-- Местности: населённые пункты, крепости, башни, мечети, природные объекты,
-- мемориалы и музеи.
CREATE TABLE places (
    id                      INTEGER PRIMARY KEY,
    slug                    TEXT UNIQUE NOT NULL,
    external_id             TEXT UNIQUE,
    source_record_url       TEXT,
    name_ru                 TEXT NOT NULL,
    name_ce                 TEXT,
    alt_names               TEXT,
    place_type              TEXT NOT NULL CHECK (place_type IN
                              ('city','town','village','fortress','tower_complex',
                               'mosque','lake','river','mountain','memorial',
                               'museum','locality')),
    district_id             INTEGER REFERENCES districts(id),
    latitude                REAL,
    longitude               REAL,
    coordinate_accuracy     TEXT NOT NULL DEFAULT 'unknown'
                              CHECK (coordinate_accuracy IN ('exact','approximate','unknown')),
    coordinate_precision_m  REAL CHECK (coordinate_precision_m IS NULL OR coordinate_precision_m >= 0),
    coordinate_source_url   TEXT,
    founded                 TEXT,
    description             TEXT,
    historical_significance TEXT,
    verification_status     TEXT NOT NULL DEFAULT 'needs_review'
                              CHECK (verification_status IN
                                ('verified','corroborated','needs_review')),
    source_id               INTEGER REFERENCES sources(id)
);

-- Личности: герои войн, деятели Кавказской войны, государственные,
-- религиозные и культурные фигуры.
CREATE TABLE people (
    id                  INTEGER PRIMARY KEY,
    slug                TEXT UNIQUE NOT NULL,
    external_id         TEXT UNIQUE,
    source_record_url   TEXT,
    full_name_ru        TEXT NOT NULL,
    full_name_ce        TEXT,
    alt_names           TEXT,
    birth_year          INTEGER,
    birth_date          TEXT,
    death_year          INTEGER,
    death_date          TEXT,
    birthplace_id       INTEGER REFERENCES places(id),
    title               TEXT,
    category            TEXT CHECK (category IN
                          ('wwii_hero','caucasian_war','modern_statesman',
                           'religious','cultural','revolutionary','military',
                           'academic','political','other')),
    occupation          TEXT,
    biography           TEXT,
    verification_status TEXT NOT NULL DEFAULT 'needs_review'
                          CHECK (verification_status IN
                            ('verified','corroborated','needs_review')),
    source_id           INTEGER REFERENCES sources(id)
);

-- События: войны, сражения, восстания, депортация, основания, строительство.
CREATE TABLE events (
    id                  INTEGER PRIMARY KEY,
    slug                TEXT UNIQUE NOT NULL,
    external_id         TEXT UNIQUE,
    source_record_url   TEXT,
    name_ru             TEXT NOT NULL,
    event_type          TEXT CHECK (event_type IN
                          ('war','battle','uprising','deportation',
                           'founding','construction','other')),
    start_year          INTEGER,
    end_year            INTEGER,
    date_text           TEXT,
    place_id            INTEGER REFERENCES places(id),
    description         TEXT,
    verification_status TEXT NOT NULL DEFAULT 'needs_review'
                          CHECK (verification_status IN
                            ('verified','corroborated','needs_review')),
    source_id           INTEGER REFERENCES sources(id)
);

-- Подвиги: конкретные деяния личности, опционально привязанные к событию/месту.
CREATE TABLE deeds (
    id                  INTEGER PRIMARY KEY,
    person_id           INTEGER NOT NULL REFERENCES people(id),
    event_id            INTEGER REFERENCES events(id),
    place_id            INTEGER REFERENCES places(id),
    year                INTEGER,
    title               TEXT NOT NULL,
    description         TEXT NOT NULL,
    award               TEXT,
    award_date          TEXT,
    verification_status TEXT NOT NULL DEFAULT 'needs_review'
                          CHECK (verification_status IN
                            ('verified','corroborated','needs_review')),
    source_id           INTEGER REFERENCES sources(id)
);

-- Где жили герои: связь личность↔место с типом отношения.
CREATE TABLE residences (
    id        INTEGER PRIMARY KEY,
    person_id INTEGER NOT NULL REFERENCES people(id),
    place_id  INTEGER NOT NULL REFERENCES places(id),
    relation  TEXT NOT NULL CHECK (relation IN
                ('born','lived','worked','died','buried','commemorated')),
    period    TEXT,
    notes     TEXT,
    verification_status TEXT NOT NULL DEFAULT 'needs_review'
                CHECK (verification_status IN ('verified','corroborated','needs_review')),
    source_id INTEGER REFERENCES sources(id),
    UNIQUE (person_id, place_id, relation)
);

-- Участие личностей в событиях (многие-ко-многим).
CREATE TABLE person_events (
    id        INTEGER PRIMARY KEY,
    person_id INTEGER NOT NULL REFERENCES people(id),
    event_id  INTEGER NOT NULL REFERENCES events(id),
    role      TEXT,
    verification_status TEXT NOT NULL DEFAULT 'needs_review'
                CHECK (verification_status IN ('verified','corroborated','needs_review')),
    source_id INTEGER REFERENCES sources(id),
    UNIQUE (person_id, event_id)
);

-- Внешние изображения не копируются в БД: сохраняются Commons URL и лицензия.
CREATE TABLE media_assets (
    id                  INTEGER PRIMARY KEY,
    place_id            INTEGER REFERENCES places(id),
    person_id           INTEGER REFERENCES people(id),
    event_id            INTEGER REFERENCES events(id),
    commons_title       TEXT NOT NULL,
    file_page_url       TEXT NOT NULL,
    original_url        TEXT NOT NULL,
    artist              TEXT,
    credit              TEXT,
    license             TEXT,
    license_url         TEXT,
    verification_status TEXT NOT NULL DEFAULT 'needs_review'
                          CHECK (verification_status IN
                            ('verified','corroborated','needs_review')),
    source_id           INTEGER NOT NULL REFERENCES sources(id),
    CHECK ((place_id IS NOT NULL) + (person_id IS NOT NULL) + (event_id IS NOT NULL) = 1),
    UNIQUE (file_page_url, place_id, person_id, event_id)
);

-- Независимые свидетельства координат. Они не перезаписывают координату места:
-- редактор видит провайдера, расстояние между точками и принимает решение.
CREATE TABLE coordinate_evidence (
    id                  INTEGER PRIMARY KEY,
    place_id            INTEGER NOT NULL REFERENCES places(id),
    provider            TEXT NOT NULL,
    external_id         TEXT NOT NULL,
    latitude            REAL NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude           REAL NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    distance_m          REAL NOT NULL CHECK (distance_m >= 0),
    source_url          TEXT NOT NULL,
    match_method        TEXT NOT NULL,
    verification_status TEXT NOT NULL DEFAULT 'needs_review'
                          CHECK (verification_status IN
                            ('verified','corroborated','needs_review')),
    UNIQUE (place_id, provider, external_id)
);

-- Конкретные архивные, библиотечные, музейные и биографические документы.
CREATE TABLE source_documents (
    id                  INTEGER PRIMARY KEY,
    slug                TEXT UNIQUE NOT NULL,
    source_id           INTEGER NOT NULL REFERENCES sources(id),
    title               TEXT NOT NULL,
    repository          TEXT,
    document_type       TEXT NOT NULL,
    url                 TEXT UNIQUE NOT NULL,
    publication_year    INTEGER,
    archive_reference   TEXT,
    notes               TEXT,
    verification_status TEXT NOT NULL DEFAULT 'needs_review'
                          CHECK (verification_status IN
                            ('verified','corroborated','needs_review'))
);

-- Цитирование на уровне утверждения, а не только всей карточки.
CREATE TABLE fact_citations (
    id                  INTEGER PRIMARY KEY,
    place_id            INTEGER REFERENCES places(id),
    person_id           INTEGER REFERENCES people(id),
    event_id            INTEGER REFERENCES events(id),
    deed_id             INTEGER REFERENCES deeds(id),
    document_id         INTEGER NOT NULL REFERENCES source_documents(id),
    claim_summary       TEXT NOT NULL,
    page_reference      TEXT,
    verification_status TEXT NOT NULL DEFAULT 'needs_review'
                          CHECK (verification_status IN
                            ('verified','corroborated','needs_review')),
    CHECK ((place_id IS NOT NULL) + (person_id IS NOT NULL) +
           (event_id IS NOT NULL) + (deed_id IS NOT NULL) = 1)
);

CREATE INDEX idx_places_district   ON places(district_id);
CREATE INDEX idx_people_birthplace ON people(birthplace_id);
CREATE INDEX idx_deeds_person      ON deeds(person_id);
CREATE INDEX idx_residences_person ON residences(person_id);
CREATE INDEX idx_residences_place  ON residences(place_id);
CREATE INDEX idx_media_place       ON media_assets(place_id);
CREATE INDEX idx_media_person      ON media_assets(person_id);
CREATE INDEX idx_media_event       ON media_assets(event_id);
CREATE INDEX idx_coordinate_place  ON coordinate_evidence(place_id);
CREATE INDEX idx_citations_place   ON fact_citations(place_id);
CREATE INDEX idx_citations_person  ON fact_citations(person_id);
CREATE INDEX idx_citations_event   ON fact_citations(event_id);

-- Удобные представления для чтения.
CREATE VIEW v_hero_birthplaces AS
SELECT p.full_name_ru AS hero,
       p.title,
       p.birth_year,
       p.death_year,
       pl.name_ru      AS birthplace,
       d.name_ru       AS district
FROM people p
LEFT JOIN places    pl ON pl.id = p.birthplace_id
LEFT JOIN districts d  ON d.id  = pl.district_id
ORDER BY p.birth_year;

CREATE VIEW v_place_people AS
SELECT pl.name_ru   AS place,
       r.relation,
       p.full_name_ru AS person
FROM residences r
JOIN places pl ON pl.id = r.place_id
JOIN people p  ON p.id  = r.person_id
ORDER BY pl.name_ru;

-- Очередь контент-редактора: сначала записи с неизвестной/примерной геолокацией.
CREATE VIEW v_research_queue AS
SELECT 'place' AS entity_type, p.id AS entity_id, p.name_ru AS title,
       p.verification_status, p.coordinate_accuracy, p.coordinate_source_url
FROM places p
WHERE p.verification_status != 'verified' OR p.coordinate_accuracy != 'exact'
UNION ALL
SELECT 'person', p.id, p.full_name_ru, p.verification_status, 'unknown', NULL
FROM people p WHERE p.verification_status != 'verified'
UNION ALL
SELECT 'event', e.id, e.name_ru, e.verification_status, 'unknown', NULL
FROM events e WHERE e.verification_status != 'verified';

CREATE VIEW v_fact_evidence AS
SELECT fc.id AS citation_id,
       COALESCE(pl.name_ru, pe.full_name_ru, ev.name_ru, de.title) AS subject,
       fc.claim_summary, sd.title AS document_title, sd.url,
       s.reliability, fc.verification_status
FROM fact_citations fc
JOIN source_documents sd ON sd.id = fc.document_id
JOIN sources s ON s.id = sd.source_id
LEFT JOIN places pl ON pl.id = fc.place_id
LEFT JOIN people pe ON pe.id = fc.person_id
LEFT JOIN events ev ON ev.id = fc.event_id
LEFT JOIN deeds de ON de.id = fc.deed_id;
