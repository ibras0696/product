import type { components, paths } from "@/shared/api/schema";

import {
  type AdminEntityView,
  type AuditView,
  type EntityInput,
  type EntityListFilters,
} from "../domain/catalog";
import type { AdminCatalogPort } from "./adminCatalogPort";
import {
  jsonInit,
  request,
  requestEnvelope,
  requestExport,
} from "./adminCatalogHttp";
import { adminCatalogResourcesApi } from "./adminCatalogResourcesApi";

type EntityDto = components["schemas"]["AdminEntity"];
type EntityCreateDto = components["schemas"]["AdminEntityCreate"];
type EntityPatchDto = components["schemas"]["AdminEntityPatch"];
type AuditPageDto = components["schemas"]["AuditPage"];
type EntityPageResponse =
  paths["/api/v1/admin/catalog/entities"]["get"]["responses"]["200"]["content"]["application/json"];
type EntityPageDto = NonNullable<EntityPageResponse["data"]>;

function entityParams(filters: EntityListFilters) {
  const params = new URLSearchParams();
  if (filters.query) params.set("query", filters.query);
  if (filters.type) params.set("type", filters.type);
  if (filters.status) params.set("status", filters.status);
  if (filters.limit !== undefined) params.set("limit", String(filters.limit));
  if (filters.offset !== undefined)
    params.set("offset", String(filters.offset));
  return params;
}

function toEntity(dto: EntityDto): AdminEntityView {
  return {
    id: dto.id,
    type: dto.type,
    slug: dto.slug,
    title: dto.title,
    shortDescription: dto.short_description,
    fullDescription: dto.full_description,
    coordinates: dto.coordinates,
    periodFrom: dto.period_from,
    periodTo: dto.period_to,
    districtId: dto.district_id,
    status: dto.status,
    version: dto.version,
    relationsCount: dto.relations_count,
    sourcesCount: dto.sources_count,
    mediaCount: dto.media_count,
  };
}

function toCreate(input: EntityInput): EntityCreateDto {
  return {
    expected_version: 0,
    type: input.type,
    slug: input.slug,
    title: input.title,
    short_description: input.shortDescription,
    full_description: input.fullDescription,
    coordinates: input.coordinates,
    period_from: input.periodFrom,
    period_to: input.periodTo,
    district_id: input.districtId,
    status: input.status,
  };
}

function toPatch(input: EntityInput, expectedVersion: number): EntityPatchDto {
  return {
    expected_version: expectedVersion,
    slug: input.slug,
    title: input.title,
    short_description: input.shortDescription,
    full_description: input.fullDescription,
    coordinates: input.coordinates,
    period_from: input.periodFrom,
    period_to: input.periodTo,
    district_id: input.districtId,
    status: input.status,
  };
}

function toAudit(dto: components["schemas"]["AuditEntry"]): AuditView {
  return {
    id: dto.id,
    actorId: dto.actor_id,
    action: dto.action,
    resourceType: dto.resource_type,
    resourceId: dto.resource_id,
    resourceVersion: dto.resource_version,
    createdAt: dto.created_at,
  };
}

export const adminCatalogApi: AdminCatalogPort = {
  ...adminCatalogResourcesApi,
  async listEntities(filters, _permissions, signal) {
    const data = await request<EntityPageDto>(
      `/api/v1/admin/catalog/entities?${entityParams(filters)}`,
      { method: "GET", signal },
    );
    return { items: data.items.map(toEntity), meta: data.meta };
  },
  async createEntity(input, _permissions, signal) {
    const data = await request<EntityDto>(
      "/api/v1/admin/catalog/entities",
      jsonInit("POST", toCreate(input), signal),
    );
    return toEntity(data);
  },
  async updateEntity(id, input, expectedVersion, _permissions, signal) {
    const data = await request<EntityDto>(
      `/api/v1/admin/catalog/entities/${encodeURIComponent(id)}`,
      jsonInit("PATCH", toPatch(input, expectedVersion), signal),
    );
    return toEntity(data);
  },
  async archiveEntity(id, expectedVersion, _permissions, signal) {
    await requestEnvelope<never>(
      `/api/v1/admin/catalog/entities/${encodeURIComponent(id)}`,
      jsonInit("DELETE", { expected_version: expectedVersion }, signal),
    );
    return null;
  },
  async listAudit(limit, offset, _permissions, signal) {
    const data = await request<AuditPageDto>(
      `/api/v1/admin/audit?limit=${String(limit)}&offset=${String(offset)}`,
      { method: "GET", signal },
    );
    return {
      items: data.items.map(toAudit),
      meta: { limit: data.limit, offset: data.offset, total: data.total },
    };
  },
  exportCatalog(format, status, _permissions, signal) {
    return requestExport(
      `/api/v1/admin/catalog/export?format=${format}&status=${status}`,
      `catalog-export-${status}.${format}`,
      signal,
    );
  },
};
