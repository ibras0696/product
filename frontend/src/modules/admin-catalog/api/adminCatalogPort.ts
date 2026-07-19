import type {
  AdminCatalogPermissions,
  AdminEntityView,
  AdminRelationView,
  AdminSourceView,
  AuditView,
  BoundedPage,
  EntityInput,
  EntityListFilters,
  RelationInput,
  RelationListFilters,
  SourceInput,
  SourceListFilters,
} from "../domain/catalog";

export interface CatalogExportFile {
  blob: Blob;
  filename: string;
  contentType: string;
}

export interface AdminCatalogPort {
  listEntities(
    filters: EntityListFilters,
    permissions: AdminCatalogPermissions,
    signal: AbortSignal,
  ): Promise<BoundedPage<AdminEntityView>>;
  createEntity(
    input: EntityInput,
    permissions: AdminCatalogPermissions,
    signal: AbortSignal,
  ): Promise<AdminEntityView>;
  updateEntity(
    id: string,
    input: EntityInput,
    expectedVersion: number,
    permissions: AdminCatalogPermissions,
    signal: AbortSignal,
  ): Promise<AdminEntityView>;
  archiveEntity(
    id: string,
    expectedVersion: number,
    permissions: AdminCatalogPermissions,
    signal: AbortSignal,
  ): Promise<null>;
  listRelations(
    filters: RelationListFilters,
    permissions: AdminCatalogPermissions,
    signal: AbortSignal,
  ): Promise<BoundedPage<AdminRelationView>>;
  createRelation(
    input: RelationInput,
    permissions: AdminCatalogPermissions,
    signal: AbortSignal,
  ): Promise<AdminRelationView>;
  updateRelation(
    id: string,
    input: RelationInput,
    expectedVersion: number,
    permissions: AdminCatalogPermissions,
    signal: AbortSignal,
  ): Promise<AdminRelationView>;
  archiveRelation(
    id: string,
    expectedVersion: number,
    permissions: AdminCatalogPermissions,
    signal: AbortSignal,
  ): Promise<null>;
  listSources(
    filters: SourceListFilters,
    permissions: AdminCatalogPermissions,
    signal: AbortSignal,
  ): Promise<BoundedPage<AdminSourceView>>;
  createSource(
    input: SourceInput,
    permissions: AdminCatalogPermissions,
    signal: AbortSignal,
  ): Promise<AdminSourceView>;
  updateSource(
    id: string,
    input: SourceInput,
    expectedVersion: number,
    permissions: AdminCatalogPermissions,
    signal: AbortSignal,
  ): Promise<AdminSourceView>;
  archiveSource(
    id: string,
    expectedVersion: number,
    permissions: AdminCatalogPermissions,
    signal: AbortSignal,
  ): Promise<null>;
  listAudit(
    limit: number,
    offset: number,
    permissions: AdminCatalogPermissions,
    signal: AbortSignal,
  ): Promise<BoundedPage<AuditView>>;
  exportCatalog(
    format: "json" | "csv",
    status: "published" | "all",
    permissions: AdminCatalogPermissions,
    signal: AbortSignal,
  ): Promise<CatalogExportFile>;
}
