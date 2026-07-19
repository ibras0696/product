import type { components, paths } from "@/shared/api/schema";

import type {
  AdminRelationView,
  AdminSourceView,
  RelationInput,
  RelationListFilters,
  SourceInput,
  SourceListFilters,
} from "../domain/catalog";
import type { AdminCatalogPort } from "./adminCatalogPort";
import { jsonInit, request, requestEnvelope } from "./adminCatalogHttp";

type RelationDto = components["schemas"]["AdminRelation"];
type RelationCreateDto = components["schemas"]["AdminRelationCreate"];
type RelationPatchDto = components["schemas"]["AdminRelationPatch"];
type RelationPageResponse =
  paths["/api/v1/admin/catalog/relations"]["get"]["responses"]["200"]["content"]["application/json"];
type RelationPageDto = NonNullable<RelationPageResponse["data"]>;
type SourceDto = components["schemas"]["AdminSource"];
type SourceCreateDto = components["schemas"]["AdminSourceCreate"];
type SourcePatchDto = components["schemas"]["AdminSourcePatch"];
type SourcePageResponse =
  paths["/api/v1/admin/catalog/sources"]["get"]["responses"]["200"]["content"]["application/json"];
type SourcePageDto = NonNullable<SourcePageResponse["data"]>;
type ResourceMethods = Pick<
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

function params(values: Record<string, string | number | undefined>) {
  const result = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== "") result.set(key, String(value));
  });
  return result;
}

function relationParams(filters: RelationListFilters) {
  return params({
    entity_id: filters.entityId,
    type: filters.type,
    limit: filters.limit,
    offset: filters.offset,
  });
}

function sourceParams(filters: SourceListFilters) {
  return params({
    query: filters.query,
    type: filters.type,
    limit: filters.limit,
    offset: filters.offset,
  });
}

function toRelation(dto: RelationDto): AdminRelationView {
  return {
    id: dto.id,
    sourceEntityId: dto.source_entity_id,
    targetEntityId: dto.target_entity_id,
    type: dto.type,
    title: dto.title,
    description: dto.description,
    periodFrom: dto.period_from,
    periodTo: dto.period_to,
    status: dto.status,
    version: dto.version,
  };
}

function relationCreate(input: RelationInput): RelationCreateDto {
  return {
    expected_version: 0,
    source_entity_id: input.sourceEntityId,
    target_entity_id: input.targetEntityId,
    type: input.type,
    title: input.title,
    description: input.description,
    period_from: input.periodFrom,
    period_to: input.periodTo,
    status: input.status,
  };
}

function relationPatch(
  input: RelationInput,
  version: number,
): RelationPatchDto {
  return {
    expected_version: version,
    type: input.type,
    title: input.title,
    description: input.description,
    period_from: input.periodFrom,
    period_to: input.periodTo,
    status: input.status,
  };
}

function toSource(dto: SourceDto): AdminSourceView {
  return {
    id: dto.id,
    title: dto.title,
    type: dto.type,
    author: dto.author,
    publisher: dto.publisher,
    publicationYear: dto.publication_year,
    url: dto.url,
    archiveReference: dto.archive_reference,
    description: dto.description,
    isVerified: dto.is_verified,
    status: dto.status,
    version: dto.version,
  };
}

function sourceCreate(input: SourceInput): SourceCreateDto {
  return {
    expected_version: 0,
    title: input.title,
    type: input.type,
    author: input.author,
    publisher: input.publisher,
    publication_year: input.publicationYear,
    url: input.url,
    archive_reference: input.archiveReference,
    description: input.description,
    is_verified: input.isVerified,
    status: input.status,
  };
}

function sourcePatch(input: SourceInput, version: number): SourcePatchDto {
  return { ...sourceCreate(input), expected_version: version };
}

export const adminCatalogResourcesApi: ResourceMethods = {
  async listRelations(filters, _permissions, signal) {
    const data = await request<RelationPageDto>(
      `/api/v1/admin/catalog/relations?${relationParams(filters)}`,
      { method: "GET", signal },
    );
    return { items: data.items.map(toRelation), meta: data.meta };
  },
  async createRelation(input, _permissions, signal) {
    const data = await request<RelationDto>(
      "/api/v1/admin/catalog/relations",
      jsonInit("POST", relationCreate(input), signal),
    );
    return toRelation(data);
  },
  async updateRelation(id, input, version, _permissions, signal) {
    const data = await request<RelationDto>(
      `/api/v1/admin/catalog/relations/${encodeURIComponent(id)}`,
      jsonInit("PATCH", relationPatch(input, version), signal),
    );
    return toRelation(data);
  },
  async archiveRelation(id, version, _permissions, signal) {
    await requestEnvelope<never>(
      `/api/v1/admin/catalog/relations/${encodeURIComponent(id)}`,
      jsonInit("DELETE", { expected_version: version }, signal),
    );
    return null;
  },
  async listSources(filters, _permissions, signal) {
    const data = await request<SourcePageDto>(
      `/api/v1/admin/catalog/sources?${sourceParams(filters)}`,
      { method: "GET", signal },
    );
    return { items: data.items.map(toSource), meta: data.meta };
  },
  async createSource(input, _permissions, signal) {
    const data = await request<SourceDto>(
      "/api/v1/admin/catalog/sources",
      jsonInit("POST", sourceCreate(input), signal),
    );
    return toSource(data);
  },
  async updateSource(id, input, version, _permissions, signal) {
    const data = await request<SourceDto>(
      `/api/v1/admin/catalog/sources/${encodeURIComponent(id)}`,
      jsonInit("PATCH", sourcePatch(input, version), signal),
    );
    return toSource(data);
  },
  async archiveSource(id, version, _permissions, signal) {
    await requestEnvelope<never>(
      `/api/v1/admin/catalog/sources/${encodeURIComponent(id)}`,
      jsonInit("DELETE", { expected_version: version }, signal),
    );
    return null;
  },
};
