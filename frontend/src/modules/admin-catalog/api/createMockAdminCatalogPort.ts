import {
  AdminCatalogError,
  type AdminCatalogPermissions,
  type AdminEntityView,
  type AuditView,
  type EntityInput,
  type EntityListFilters,
} from "../domain/catalog";
import type { AdminCatalogPort, CatalogExportFile } from "./adminCatalogPort";
import { seedEntities } from "./mockSeeds";
import { createMockCatalogResources } from "./mockCatalogResources";

const MAX_PAGE = 100;
const MAX_OFFSET = 1000;
const MAX_EXPORT_RECORDS = 10_000;
const MAX_EXPORT_BYTES = 100 * 1024 * 1024;
const actorId = "70000000-0000-4000-8000-000000000001";

function requirePermission(allowed: boolean) {
  if (!allowed) throw new AdminCatalogError("forbidden", "Недостаточно прав");
}

function bounded(value: number | undefined, fallback: number, max: number) {
  return Math.min(Math.max(Math.trunc(value ?? fallback), 0), max);
}

function filterEntities(items: AdminEntityView[], filters: EntityListFilters) {
  const query = filters.query?.trim().toLocaleLowerCase("ru") ?? "";
  return items.filter(
    (item) =>
      (!filters.type || item.type === filters.type) &&
      (!filters.status || item.status === filters.status) &&
      (!query ||
        item.title.ru.toLocaleLowerCase("ru").includes(query) ||
        item.slug.includes(query)),
  );
}

function csvCell(value: string | number) {
  const text = String(value);
  const safe = /^[=+\-@]/.test(text) ? `'${text}` : text;
  return `"${safe.replaceAll('"', '""')}"`;
}

function exportRows(entities: AdminEntityView[]) {
  return entities.map((entity) => ({
    id: entity.id,
    type: entity.type,
    slug: entity.slug,
    title: entity.title.ru,
    status: entity.status,
    relations_count: entity.relationsCount,
    sources_count: entity.sourcesCount,
    media_count: entity.mediaCount,
  }));
}

function makeExport(
  format: "json" | "csv",
  entities: AdminEntityView[],
): CatalogExportFile {
  const rows = exportRows(entities);
  if (format === "json") {
    const contentType = "application/json;charset=utf-8" as const;
    return {
      blob: new Blob([JSON.stringify({ entities: rows })], {
        type: contentType,
      }),
      filename: "catalog-export.json",
      contentType,
    };
  }
  const contentType = "text/csv;charset=utf-8" as const;
  const headers = [
    "id",
    "type",
    "slug",
    "title",
    "status",
    "relations_count",
    "sources_count",
    "media_count",
  ] as const;
  const lines = [
    headers.map(csvCell).join(","),
    ...rows.map((row) => headers.map((key) => csvCell(row[key])).join(",")),
  ];
  return {
    blob: new Blob([lines.join("\r\n")], { type: contentType }),
    filename: "catalog-export.csv",
    contentType,
  };
}

export interface MockAdminCatalogPort extends AdminCatalogPort {
  mockOnlyBumpVersion(id: string): void;
  mockOnlySetExportRecordCount(count: number | null): void;
}

type EntityMethods = Omit<
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

class MockAdminCatalogAdapter implements EntityMethods {
  private entities = seedEntities.map((item) => ({ ...item }));
  private audit: AuditView[] = [];
  private exportCountOverride: number | null = null;
  private sequence = this.entities.length;

  private find(id: string) {
    const entity = this.entities.find((item) => item.id === id);
    if (!entity)
      throw new AdminCatalogError("not_found", "Сущность не найдена");
    return entity;
  }

  private record(
    action: AuditView["action"],
    entityId: string,
    version: number,
  ) {
    this.audit = [
      {
        id: crypto.randomUUID(),
        actorId,
        action,
        resourceType: "entity",
        resourceId: entityId,
        resourceVersion: version,
        createdAt: "2026-07-18T12:00:00Z",
      },
      ...this.audit,
    ];
  }

  private assertVersion(entity: AdminEntityView, expected: number) {
    if (entity.version !== expected)
      throw new AdminCatalogError(
        "conflict",
        "Запись уже изменена другим пользователем",
      );
  }

  async listEntities(
    filters: EntityListFilters,
    permissions: AdminCatalogPermissions,
    signal: AbortSignal,
  ) {
    await Promise.resolve();
    signal.throwIfAborted();
    requirePermission(permissions.read);
    const found = filterEntities(this.entities, filters);
    const limit = Math.max(bounded(filters.limit, 20, MAX_PAGE), 1);
    const offset = bounded(filters.offset, 0, MAX_OFFSET);
    return Promise.resolve({
      items: found.slice(offset, offset + limit),
      meta: { limit, offset, total: found.length },
    });
  }

  async createEntity(
    input: EntityInput,
    permissions: AdminCatalogPermissions,
    signal: AbortSignal,
  ) {
    await Promise.resolve();
    signal.throwIfAborted();
    requirePermission(permissions.write);
    this.sequence += 1;
    if (input.status === "published")
      throw new AdminCatalogError(
        "source_required",
        "Сначала добавьте источник",
      );
    const entity: AdminEntityView = {
      id: `60000000-0000-4000-8000-${String(this.sequence).padStart(12, "0")}`,
      ...input,
      version: 1,
      relationsCount: 0,
      sourcesCount: 0,
      mediaCount: 0,
    };
    this.entities = [entity, ...this.entities];
    this.record("catalog.entity.create", entity.id, entity.version);
    return Promise.resolve({ ...entity });
  }

  async updateEntity(
    id: string,
    input: EntityInput,
    expectedVersion: number,
    permissions: AdminCatalogPermissions,
    signal: AbortSignal,
  ) {
    await Promise.resolve();
    signal.throwIfAborted();
    requirePermission(permissions.write);
    const current = this.find(id);
    this.assertVersion(current, expectedVersion);
    if (input.status === "published" && current.sourcesCount === 0)
      throw new AdminCatalogError(
        "source_required",
        "Публикация без источника запрещена",
      );
    const updated = {
      ...current,
      ...input,
      version: current.version + 1,
    };
    this.entities = this.entities.map((item) =>
      item.id === id ? updated : item,
    );
    this.record("catalog.entity.update", id, updated.version);
    return Promise.resolve({ ...updated });
  }

  async archiveEntity(
    id: string,
    expectedVersion: number,
    permissions: AdminCatalogPermissions,
    signal: AbortSignal,
  ) {
    await Promise.resolve();
    signal.throwIfAborted();
    requirePermission(permissions.write);
    const current = this.find(id);
    this.assertVersion(current, expectedVersion);
    this.entities = this.entities.map((item) =>
      item.id === id
        ? {
            ...item,
            status: "archived",
            version: item.version + 1,
          }
        : item,
    );
    this.record("catalog.entity.archive", id, current.version + 1);
    return Promise.resolve(null);
  }

  async listAudit(
    limit: number,
    offset: number,
    permissions: AdminCatalogPermissions,
    signal: AbortSignal,
  ) {
    await Promise.resolve();
    signal.throwIfAborted();
    requirePermission(permissions.auditRead);
    const safeLimit = Math.max(bounded(limit, 20, MAX_PAGE), 1);
    const safeOffset = bounded(offset, 0, MAX_OFFSET);
    return Promise.resolve({
      items: this.audit.slice(safeOffset, safeOffset + safeLimit),
      meta: { limit: safeLimit, offset: safeOffset, total: this.audit.length },
    });
  }

  async exportCatalog(
    format: "json" | "csv",
    status: "published" | "all",
    permissions: AdminCatalogPermissions,
    signal: AbortSignal,
  ) {
    await Promise.resolve();
    signal.throwIfAborted();
    requirePermission(permissions.export);
    const selected =
      status === "all"
        ? this.entities
        : this.entities.filter((item) => item.status === "published");
    if ((this.exportCountOverride ?? selected.length) > MAX_EXPORT_RECORDS)
      throw new AdminCatalogError(
        "export_too_large",
        "Экспорт превышает лимит 10 000 записей",
      );
    const file = makeExport(format, selected);
    if (file.blob.size > MAX_EXPORT_BYTES)
      throw new AdminCatalogError(
        "export_too_large",
        "Экспорт превышает лимит 100 МиБ",
      );
    return file;
  }

  mockOnlyBumpVersion(id: string) {
    this.find(id);
    this.entities = this.entities.map((item) =>
      item.id === id ? { ...item, version: item.version + 1 } : item,
    );
  }

  mockOnlySetExportRecordCount(count: number | null) {
    this.exportCountOverride = count;
  }
}

export function createMockAdminCatalogPort(): MockAdminCatalogPort {
  return Object.assign(
    new MockAdminCatalogAdapter(),
    createMockCatalogResources(),
  );
}
