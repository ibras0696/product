import { EntityNotFoundError } from "./entitiesPort";
import { MOCK_ENTITY_IDS, mockEntitiesPort } from "./mockEntitiesAdapter";

const signal = new AbortController().signal;

it("resolves representative clickable entities with their correct public types", async () => {
  const allEntities = await Promise.all(
    Object.values(MOCK_ENTITY_IDS).map((entityId) =>
      mockEntitiesPort.getEntity(entityId, signal),
    ),
  );
  expect(allEntities).toHaveLength(23);
  expect(new Set(allEntities.map(({ id }) => id))).toHaveProperty("size", 23);

  const ids = [
    MOCK_ENTITY_IDS.shelkovskaya,
    MOCK_ENTITY_IDS.akhmadKadyrov,
    MOCK_ENTITY_IDS.publicEducation,
    MOCK_ENTITY_IDS.archiveCollection,
  ];
  const entities = await Promise.all(
    ids.map((entityId) => mockEntitiesPort.getEntity(entityId, signal)),
  );
  expect(entities.map(({ type }) => type)).toEqual([
    "settlement",
    "person",
    "event",
    "artifact",
  ]);
  expect(entities.map(({ title }) => title.ru)).toEqual([
    "Шелковская",
    "Ахмат-Хаджи Кадыров",
    "Развитие народного образования",
    "Архивная коллекция",
  ]);

  const bundles = await Promise.all(
    ids.map(async (entityId) => {
      const [sources, media] = await Promise.all([
        mockEntitiesPort.getSources(entityId, 12, 0, signal),
        mockEntitiesPort.getMedia(entityId, 12, 0, signal),
      ]);
      return { sources, media };
    }),
  );
  expect(bundles.every(({ sources }) => sources.meta.total === 1)).toBe(true);
  expect(bundles.every(({ media }) => media.meta.total === 1)).toBe(true);
});

it("keeps unknown IDs outside the published mock catalog", async () => {
  await expect(
    mockEntitiesPort.getEntity("10000000-0000-4000-8000-000000000099", signal),
  ).rejects.toBeInstanceOf(EntityNotFoundError);
});
