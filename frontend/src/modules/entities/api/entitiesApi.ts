import type { components } from "@/shared/api/schema";

import type {
  BoundedPage,
  EntityDetails,
  EntityGraph,
  EntitySource,
  PublishedMedia,
} from "../domain/entity";
import { EntityNotFoundError, type EntitiesPort } from "./entitiesPort";

type ApiError = components["schemas"]["ApiError"];
type DetailsResponse = components["schemas"]["ApiResponse_EntityDetails_"];
type GraphResponse = components["schemas"]["ApiResponse_GraphView_"];
type SourcesResponse = components["schemas"]["ApiResponse_Page_SourceView__"];
type MediaResponse = components["schemas"]["ApiResponse_Page_PublishedMedia__"];

interface Envelope<T> {
  ok?: boolean;
  data?: T | null;
  error?: ApiError | null;
}

const REQUEST_TIMEOUT_MS = 15_000;

function boundedSignal(signal: AbortSignal) {
  return AbortSignal.any([signal, AbortSignal.timeout(REQUEST_TIMEOUT_MS)]);
}

class EntitiesApiError extends Error {
  constructor() {
    super("Public entity API request failed");
    this.name = "EntitiesApiError";
  }
}

async function getData<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(path, {
    method: "GET",
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    signal: boundedSignal(signal),
  });
  let envelope: Envelope<T>;
  try {
    envelope = (await response.json()) as Envelope<T>;
  } catch {
    throw new EntitiesApiError();
  }
  if (envelope.error?.code === "not_found") throw new EntityNotFoundError();
  if (!response.ok || envelope.ok !== true || envelope.data == null) {
    throw new EntitiesApiError();
  }
  return envelope.data;
}

function mapDetails(
  item: components["schemas"]["EntityDetails"],
): EntityDetails {
  return {
    id: item.id,
    type: item.type,
    slug: item.slug,
    title: item.title,
    shortDescription: item.short_description,
    fullDescription: item.full_description,
    coordinates: item.coordinates,
    periodFrom: item.period_from,
    periodTo: item.period_to,
    coverUrl: item.cover_url,
    counts: {
      relations: item.relations_count,
      sources: item.sources_count,
      media: item.media_count,
    },
    status: item.status,
    researchStatus: item.research_status,
  };
}

function mapGraph(item: components["schemas"]["GraphView"]): EntityGraph {
  return {
    center: item.center,
    nodes: item.nodes.map((node) => ({
      id: node.id,
      type: node.type,
      title: node.title,
      relationsCount: node.relations_count,
    })),
    edges: item.edges.map((edge) => ({
      id: edge.id,
      sourceId: edge.source_id,
      targetId: edge.target_id,
      type: edge.type,
      title: edge.title,
      description: edge.description,
      sourcesCount: edge.sources_count,
    })),
    hiddenNodesCount: item.hidden_nodes_count,
  };
}

function mapSources(
  page: components["schemas"]["Page_SourceView_"],
): BoundedPage<EntitySource> {
  return {
    items: page.items.map((item) => ({
      id: item.id,
      title: item.title,
      type: item.type,
      author: item.author,
      publisher: item.publisher,
      publicationYear: item.publication_year,
      url: item.url,
      archiveReference: item.archive_reference,
      description: item.description,
      verificationStatus:
        item.type === "oral_testimony" ? "oral_account" : "verified",
    })),
    meta: page.meta,
  };
}

function mapMedia(
  page: components["schemas"]["Page_PublishedMedia_"],
): BoundedPage<PublishedMedia> {
  return {
    items: page.items.map((item) => ({
      id: item.id,
      publicUrl: item.public_url,
      previewUrl: item.preview_url,
      mimeType: item.mime_type,
      width: item.width,
      height: item.height,
      caption: item.caption,
      author: item.author,
      approximateDate: item.approximate_date,
      sourceDescription: item.source_description,
    })),
    meta: page.meta,
  };
}

function pagePath(
  entityId: string,
  resource: "sources" | "media",
  limit: number,
  offset: number,
) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return `/api/v1/entities/${encodeURIComponent(entityId)}/${resource}?${params}`;
}

export const entitiesApi: EntitiesPort = {
  async getEntity(entityId, signal) {
    const data = await getData<NonNullable<DetailsResponse["data"]>>(
      `/api/v1/entities/${encodeURIComponent(entityId)}`,
      signal,
    );
    return mapDetails(data);
  },
  async getGraph(entityId, signal) {
    const data = await getData<NonNullable<GraphResponse["data"]>>(
      `/api/v1/entities/${encodeURIComponent(entityId)}/graph?depth=2&limit=40`,
      signal,
    );
    return mapGraph(data);
  },
  async getSources(entityId, limit, offset, signal) {
    const data = await getData<NonNullable<SourcesResponse["data"]>>(
      pagePath(entityId, "sources", limit, offset),
      signal,
    );
    return mapSources(data);
  },
  async getMedia(entityId, limit, offset, signal) {
    const data = await getData<NonNullable<MediaResponse["data"]>>(
      pagePath(entityId, "media", limit, offset),
      signal,
    );
    return mapMedia(data);
  },
};
