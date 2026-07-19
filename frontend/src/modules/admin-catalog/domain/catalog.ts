export type AdminEntityType =
  | "settlement"
  | "person"
  | "event"
  | "landmark"
  | "natural_object"
  | "cultural_object"
  | "organization"
  | "university_object"
  | "artifact";
export type AdminEntityStatus = "draft" | "published" | "archived";
export type AdminRelationType =
  | "born_in"
  | "lived_in"
  | "worked_in"
  | "studied_in"
  | "taught_at"
  | "participated_in"
  | "located_in"
  | "part_of"
  | "created_by"
  | "described_in"
  | "connected_with"
  | "connected_with_chgu";
export type AdminSourceType =
  | "archive_document"
  | "book"
  | "scientific_article"
  | "museum_material"
  | "official_publication"
  | "photo"
  | "audio"
  | "video"
  | "oral_testimony"
  | "web_resource";

export interface LocalizedText {
  ru: string;
  ce: string | null;
}

export interface Coordinates {
  latitude: number;
  longitude: number;
}

export interface AdminCatalogPermissions {
  read: boolean;
  write: boolean;
  export: boolean;
  auditRead: boolean;
}

export interface AdminEntityView {
  id: string;
  type: AdminEntityType;
  slug: string;
  title: LocalizedText;
  shortDescription: LocalizedText;
  fullDescription: LocalizedText;
  coordinates: Coordinates | null;
  periodFrom: number | null;
  periodTo: number | null;
  districtId: string | null;
  status: AdminEntityStatus;
  version: number;
  relationsCount: number;
  sourcesCount: number;
  mediaCount: number;
}

export interface EntityInput {
  type: AdminEntityType;
  slug: string;
  title: LocalizedText;
  shortDescription: LocalizedText;
  fullDescription: LocalizedText;
  coordinates: Coordinates | null;
  periodFrom: number | null;
  periodTo: number | null;
  districtId: string | null;
  status: Exclude<AdminEntityStatus, "archived">;
}

export interface EntityListFilters {
  query?: string;
  type?: AdminEntityType;
  status?: AdminEntityStatus;
  limit?: number;
  offset?: number;
}

export interface AdminRelationView {
  id: string;
  sourceEntityId: string;
  targetEntityId: string;
  type: AdminRelationType;
  title: LocalizedText;
  description: LocalizedText;
  periodFrom: number | null;
  periodTo: number | null;
  status: AdminEntityStatus;
  version: number;
}

export interface RelationInput {
  sourceEntityId: string;
  targetEntityId: string;
  type: AdminRelationType;
  title: LocalizedText;
  description: LocalizedText;
  periodFrom: number | null;
  periodTo: number | null;
  status: Exclude<AdminEntityStatus, "archived">;
}

export interface RelationListFilters {
  entityId?: string;
  type?: AdminRelationType;
  limit?: number;
  offset?: number;
}

export interface AdminSourceView {
  id: string;
  title: string;
  type: AdminSourceType;
  author: string | null;
  publisher: string | null;
  publicationYear: number | null;
  url: string | null;
  archiveReference: string | null;
  description: string;
  isVerified: boolean;
  status: AdminEntityStatus;
  version: number;
}

export interface SourceInput {
  title: string;
  type: AdminSourceType;
  author: string | null;
  publisher: string | null;
  publicationYear: number | null;
  url: string | null;
  archiveReference: string | null;
  description: string;
  isVerified: boolean;
  status: Exclude<AdminEntityStatus, "archived">;
}

export interface SourceListFilters {
  query?: string;
  type?: AdminSourceType;
  limit?: number;
  offset?: number;
}

export interface AuditView {
  id: string;
  actorId: string;
  action: string;
  resourceType: string;
  resourceId: string;
  resourceVersion: number;
  createdAt: string;
}

export interface BoundedPage<T> {
  items: T[];
  meta: { limit: number; offset: number; total: number };
}

export class AdminCatalogError extends Error {
  constructor(
    readonly code:
      | "bad_request"
      | "unauthorized"
      | "forbidden"
      | "conflict"
      | "not_found"
      | "export_too_large"
      | "source_required"
      | "validation_error"
      | "internal_error"
      | "service_unavailable",
    message: string,
  ) {
    super(message);
    this.name = "AdminCatalogError";
  }
}
