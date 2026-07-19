import type { BoundedPage, EntityGraph } from "../domain/entity";
import { EntityNotFoundError, type EntitiesPort } from "./entitiesPort";
import { catalogSeeds } from "./mock-data/catalogSeeds";
export { MOCK_ENTITY_IDS } from "./mock-data/entityIds";
import { createEntityRecord } from "./mock-data/recordFactory";
import { groznyRecord, nozhayYurtRecord } from "./mock-data/richRecords";
import type { EntityRecord } from "./mock-data/types";

const records = new Map<string, EntityRecord>(
  [groznyRecord, nozhayYurtRecord, ...catalogSeeds.map(createEntityRecord)].map(
    (record) => [record.details.id, record],
  ),
);

function getRecord(entityId: string): EntityRecord {
  const record = records.get(entityId);
  if (!record) throw new EntityNotFoundError();
  return record;
}

function page<T>(items: T[], limit: number, offset: number): BoundedPage<T> {
  const safeLimit = Math.min(Math.max(limit, 1), 50);
  const safeOffset = Math.max(offset, 0);
  return {
    items: items.slice(safeOffset, safeOffset + safeLimit),
    meta: { limit: safeLimit, offset: safeOffset, total: items.length },
  };
}

function graph(entityId: string): EntityGraph {
  const center = getRecord(entityId).details;
  const related = [...records.values()]
    .filter((record) => record.details.id !== entityId)
    .slice(0, 2)
    .map((record) => record.details);
  const nodes = related.map((entity) => ({
    id: entity.id,
    type: entity.type,
    title: entity.title,
    relationsCount: entity.counts.relations,
  }));
  const endpoints = [center, ...related];
  return {
    center: { id: center.id, type: center.type, title: center.title },
    nodes,
    edges: endpoints.slice(0, -1).map((entity, index) => ({
      id: `mock-relation-${entity.id}`,
      sourceId: entity.id,
      targetId: endpoints[index + 1].id,
      type: "connected_with",
      title: { ru: "Историческая связь", ce: null },
      description: { ru: "Подтверждённая связь объектов", ce: null },
      sourcesCount: index + 1,
    })),
    hiddenNodesCount: 0,
  };
}

export const mockEntitiesPort: EntitiesPort = {
  getEntity(entityId, signal) {
    return Promise.resolve().then(() => {
      signal.throwIfAborted();
      return getRecord(entityId).details;
    });
  },
  getGraph(entityId, signal) {
    return Promise.resolve().then(() => {
      signal.throwIfAborted();
      return graph(entityId);
    });
  },
  getSources(entityId, limit, offset, signal) {
    return Promise.resolve().then(() => {
      signal.throwIfAborted();
      return page(getRecord(entityId).sources, limit, offset);
    });
  },
  getMedia(entityId, limit, offset, signal) {
    return Promise.resolve().then(() => {
      signal.throwIfAborted();
      return page(getRecord(entityId).media, limit, offset);
    });
  },
};
