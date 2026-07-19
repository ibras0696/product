import {
  AdminCatalogError,
  type AdminCatalogPermissions,
  type AdminRelationView,
  type AdminSourceView,
} from "../domain/catalog";
import type { AdminCatalogPort } from "./adminCatalogPort";

type Methods = Pick<
  AdminCatalogPort,
  | "listRelations"
  | "createRelation"
  | "updateRelation"
  | "archiveRelation"
  | "listSources"
  | "createSource"
  | "updateSource"
  | "archiveSource"
>;

const relationSeed: AdminRelationView = {
  id: "61000000-0000-4000-8000-000000000001",
  sourceEntityId: "60000000-0000-4000-8000-000000000001",
  targetEntityId: "60000000-0000-4000-8000-000000000002",
  type: "connected_with",
  title: { ru: "Историческая связь", ce: null },
  description: { ru: "Связь двух объектов", ce: null },
  periodFrom: null,
  periodTo: null,
  status: "draft",
  version: 1,
};
const sourceSeed: AdminSourceView = {
  id: "62000000-0000-4000-8000-000000000001",
  title: "Архивная справка",
  type: "archive_document",
  author: null,
  publisher: null,
  publicationYear: null,
  url: null,
  archiveReference: "Ф. 1",
  description: "Описание источника",
  isVerified: true,
  status: "draft",
  version: 1,
};

interface MockCatalogResourceState {
  relations: AdminRelationView[];
  sources: AdminSourceView[];
}

function allowed(permissions: AdminCatalogPermissions, write = false) {
  if (!(write ? permissions.write : permissions.read))
    throw new AdminCatalogError("forbidden", "Недостаточно прав");
}

function page<T>(items: T[], limit = 20, offset = 0) {
  return {
    items: items.slice(offset, offset + limit),
    meta: { limit, offset, total: items.length },
  };
}

export function createMockCatalogResources(): Methods {
  const state: MockCatalogResourceState = {
    relations: [relationSeed],
    sources: [sourceSeed],
  };
  return { ...relationMethods(state), ...sourceMethods(state) };
}

function relationMethods(
  state: MockCatalogResourceState,
): Pick<
  Methods,
  "listRelations" | "createRelation" | "updateRelation" | "archiveRelation"
> {
  return {
    async listRelations(filters, permissions, signal) {
      signal.throwIfAborted();
      allowed(permissions);
      const found = state.relations.filter(
        (item) =>
          (!filters.entityId ||
            [item.sourceEntityId, item.targetEntityId].includes(
              filters.entityId,
            )) &&
          (!filters.type || item.type === filters.type),
      );
      return Promise.resolve(page(found, filters.limit, filters.offset));
    },
    async createRelation(input, permissions, signal) {
      signal.throwIfAborted();
      allowed(permissions, true);
      const item: AdminRelationView = {
        id: crypto.randomUUID(),
        ...input,
        version: 1,
      };
      state.relations = [item, ...state.relations];
      return Promise.resolve(item);
    },
    async updateRelation(id, input, version, permissions, signal) {
      signal.throwIfAborted();
      allowed(permissions, true);
      const current = state.relations.find((item) => item.id === id);
      if (!current)
        throw new AdminCatalogError("not_found", "Связь не найдена");
      if (current.version !== version)
        throw new AdminCatalogError("conflict", "Версия устарела");
      const item = { ...current, ...input, version: version + 1 };
      state.relations = state.relations.map((value) =>
        value.id === id ? item : value,
      );
      return Promise.resolve(item);
    },
    async archiveRelation(id, version, permissions, signal) {
      signal.throwIfAborted();
      allowed(permissions, true);
      const current = state.relations.find((item) => item.id === id);
      if (!current || current.version !== version)
        throw new AdminCatalogError("conflict", "Версия устарела");
      state.relations = state.relations.map((item) =>
        item.id === id
          ? { ...item, status: "archived", version: version + 1 }
          : item,
      );
      return Promise.resolve(null);
    },
  };
}

function sourceMethods(
  state: MockCatalogResourceState,
): Pick<
  Methods,
  "listSources" | "createSource" | "updateSource" | "archiveSource"
> {
  return {
    async listSources(filters, permissions, signal) {
      signal.throwIfAborted();
      allowed(permissions);
      const query = filters.query?.toLocaleLowerCase("ru");
      const found = state.sources.filter(
        (item) =>
          (!query || item.title.toLocaleLowerCase("ru").includes(query)) &&
          (!filters.type || item.type === filters.type),
      );
      return Promise.resolve(page(found, filters.limit, filters.offset));
    },
    async createSource(input, permissions, signal) {
      signal.throwIfAborted();
      allowed(permissions, true);
      const item: AdminSourceView = {
        id: crypto.randomUUID(),
        ...input,
        version: 1,
      };
      state.sources = [item, ...state.sources];
      return Promise.resolve(item);
    },
    async updateSource(id, input, version, permissions, signal) {
      signal.throwIfAborted();
      allowed(permissions, true);
      const current = state.sources.find((item) => item.id === id);
      if (!current)
        throw new AdminCatalogError("not_found", "Источник не найден");
      if (current.version !== version)
        throw new AdminCatalogError("conflict", "Версия устарела");
      const item = { ...current, ...input, version: version + 1 };
      state.sources = state.sources.map((value) =>
        value.id === id ? item : value,
      );
      return Promise.resolve(item);
    },
    async archiveSource(id, version, permissions, signal) {
      signal.throwIfAborted();
      allowed(permissions, true);
      const current = state.sources.find((item) => item.id === id);
      if (!current || current.version !== version)
        throw new AdminCatalogError("conflict", "Версия устарела");
      state.sources = state.sources.map((item) =>
        item.id === id
          ? { ...item, status: "archived", version: version + 1 }
          : item,
      );
      return Promise.resolve(null);
    },
  };
}
