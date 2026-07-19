import type { components } from "@/shared/api/schema";

import { normalizeFilters, normalizeSearchFilters } from "./filtering";
import type {
  CatalogEntityType,
  CatalogOptionsViewModel,
  EntityDetailsViewModel,
  ExplorationFilters,
  GraphViewModel,
  MapEntitiesViewModel,
  MapEntityViewModel,
  MediaPageViewModel,
  SearchFilters,
  SearchResultsViewModel,
  SourcePageViewModel,
} from "./viewModels";
import { chechnyaRequestBbox } from "../model/chechnyaBoundary";
import { normalizeTimelineFilters } from "./timelineFilters";
import type {
  TimelineEventsViewModel,
  TimelineFilters,
} from "./timelineViewModels";

type ApiError = components["schemas"]["ApiError"];
type MapResponse = components["schemas"]["ApiResponse_MapEntityCollection_"];
type OptionsResponse = components["schemas"]["ApiResponse_CatalogOptions_"];
type SearchResponse =
  components["schemas"]["ApiResponse_Page_SearchItemView__"];
type TimelineResponse =
  components["schemas"]["ApiResponse_Page_TimelineEventView__"];
type DetailsResponse = components["schemas"]["ApiResponse_EntityDetails_"];
type GraphResponse = components["schemas"]["ApiResponse_GraphView_"];
type SourcesResponse = components["schemas"]["ApiResponse_Page_SourceView__"];
type MediaResponse = components["schemas"]["ApiResponse_Page_PublishedMedia__"];
type MapCollectionData = NonNullable<MapResponse["data"]>;

interface Envelope<T> {
  ok?: boolean;
  data?: T | null;
  error?: ApiError | null;
  meta?: { request_id?: string } | null;
}

const REQUEST_TIMEOUT_MS = 15_000;

function boundedSignal(signal: AbortSignal) {
  return AbortSignal.any([signal, AbortSignal.timeout(REQUEST_TIMEOUT_MS)]);
}

export class ExplorationApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status: number,
    readonly requestId?: string,
  ) {
    super(message);
    this.name = "ExplorationApiError";
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
    throw new ExplorationApiError(
      "Сервер вернул некорректный ответ.",
      "invalid_response",
      response.status,
    );
  }
  if (!response.ok || envelope.ok !== true || envelope.data == null) {
    throw new ExplorationApiError(
      envelope.error?.message ?? "Не удалось загрузить данные.",
      envelope.error?.code ?? "http_error",
      response.status,
      envelope.meta?.request_id,
    );
  }
  return envelope.data;
}

function appendList(
  params: URLSearchParams,
  key: string,
  values: readonly string[],
) {
  values.forEach((value) => {
    params.append(key, value);
  });
}

function appendCommonFilters(
  params: URLSearchParams,
  filters: ExplorationFilters,
) {
  const normalized = normalizeFilters(filters);
  appendList(params, "types", normalized.types);
  appendList(params, "research_statuses", normalized.researchStatuses);
  if (normalized.districtId) params.set("district_id", normalized.districtId);
  if (normalized.periodFrom !== null)
    params.set("period_from", String(normalized.periodFrom));
  if (normalized.periodTo !== null)
    params.set("period_to", String(normalized.periodTo));
  params.set("limit", String(normalized.limit));
}

function entityKind(
  type: MapEntityViewModel["entityType"],
): MapEntityViewModel["kind"] {
  if (type === "settlement") return "place";
  if (type === "person") return "person";
  if (type === "event") return "event";
  if (
    type === "artifact" ||
    type === "organization" ||
    type === "university_object"
  ) {
    return "source";
  }
  return "landmark";
}

function mapEntity(
  item: components["schemas"]["MapEntity"],
): MapEntityViewModel {
  return {
    id: item.id,
    entityType: item.type,
    researchStatus: item.research_status,
    kind: entityKind(item.type),
    name: item.title.ru,
    title: item.title,
    districtId: item.district_id ?? "",
    periodFrom: null,
    periodTo: null,
    coordinates: [item.coordinates.longitude, item.coordinates.latitude],
    caption: "",
    subtitle: "",
    summary: "",
    image: item.cover_url ?? "",
    description: "",
    x: 0,
    y: 0,
    stats: {
      relations: item.relations_count,
      heroes: 0,
      events: 0,
      landmarks: 0,
      sources: 0,
    },
  };
}

function mapOptions(
  data: components["schemas"]["CatalogOptions"],
): CatalogOptionsViewModel {
  return {
    districts: data.districts.map((item) => ({
      id: item.id,
      title: item.title,
    })),
    periods: data.periods.map((item) => ({
      id: item.id,
      title: item.title,
      periodFrom: item.period_from,
      periodTo: item.period_to,
    })),
    entityTypes: data.entity_types,
    researchStatuses: data.research_statuses,
  };
}

export const explorationApi = {
  async getMapEntities(
    filters: ExplorationFilters,
    signal: AbortSignal,
  ): Promise<MapEntitiesViewModel> {
    const params = new URLSearchParams({
      bbox: chechnyaRequestBbox,
      zoom: "6",
    });
    appendCommonFilters(params, filters);
    const data = await getData<MapCollectionData>(
      `/api/v1/map/entities?${params}`,
      signal,
    );
    return {
      items: data.items.map(mapEntity),
      relations: data.relations.map((relation) => ({
        from: relation.source_id,
        to: relation.target_id,
        fromKind: entityKind(relation.source_type),
        fromName: relation.source_title,
        toKind: entityKind(relation.target_type),
        toName: relation.target_title,
      })),
      truncated: data.truncated,
      relationsTruncated: data.relations_truncated,
    };
  },
  async getCatalogOptions(signal: AbortSignal) {
    return mapOptions(
      await getData<NonNullable<OptionsResponse["data"]>>(
        "/api/v1/catalog/options",
        signal,
      ),
    );
  },
  async search(
    filters: SearchFilters,
    signal: AbortSignal,
  ): Promise<SearchResultsViewModel> {
    const normalized = normalizeSearchFilters(filters);
    const params = new URLSearchParams({
      q: filters.query.trim(),
      limit: String(normalized.limit),
      offset: String(normalized.offset),
    });
    appendList(params, "types", normalized.types);
    if (normalized.districtId) params.set("district_id", normalized.districtId);
    if (normalized.periodFrom !== null)
      params.set("period_from", String(normalized.periodFrom));
    if (normalized.periodTo !== null)
      params.set("period_to", String(normalized.periodTo));
    const data = await getData<NonNullable<SearchResponse["data"]>>(
      `/api/v1/search?${params}`,
      signal,
    );
    return {
      items: data.items.map((item) => ({
        id: item.id,
        type: item.type,
        title: item.title,
        subtitle: item.subtitle.ru,
        coverUrl: item.cover_url ?? "",
        relationsCount: item.relations_count,
      })),
      meta: data.meta,
    };
  },
  async getTimelineEvents(
    filters: TimelineFilters,
    signal: AbortSignal,
  ): Promise<TimelineEventsViewModel> {
    const normalized = normalizeTimelineFilters(filters);
    const params = new URLSearchParams({
      limit: String(normalized.limit),
      offset: String(normalized.offset),
    });
    if (normalized.query) params.set("q", normalized.query);
    if (normalized.districtId) params.set("district_id", normalized.districtId);
    if (normalized.periodFrom !== null)
      params.set("period_from", String(normalized.periodFrom));
    if (normalized.periodTo !== null)
      params.set("period_to", String(normalized.periodTo));
    const data = await getData<NonNullable<TimelineResponse["data"]>>(
      `/api/v1/timeline/events?${params}`,
      signal,
    );
    return {
      items: data.items.map((item) => ({
        id: item.id,
        title: item.title.ru,
        shortDescription: item.short_description.ru,
        periodFrom: item.period_from,
        periodTo: item.period_to,
        coordinates: item.coordinates,
      })),
      meta: data.meta,
    };
  },
  getEntity(id: string, signal: AbortSignal): Promise<EntityDetailsViewModel> {
    return getData<NonNullable<DetailsResponse["data"]>>(
      `/api/v1/entities/${encodeURIComponent(id)}`,
      signal,
    );
  },
  getGraph(
    id: string,
    filters: ExplorationFilters,
    signal: AbortSignal,
  ): Promise<GraphViewModel> {
    const normalized = normalizeFilters(filters);
    const params = new URLSearchParams({ depth: "2", limit: "40" });
    if (normalized.periodFrom !== null) {
      params.set("period_from", String(normalized.periodFrom));
    }
    if (normalized.periodTo !== null) {
      params.set("period_to", String(normalized.periodTo));
    }
    return getData<NonNullable<GraphResponse["data"]>>(
      `/api/v1/entities/${encodeURIComponent(id)}/graph?${params}`,
      signal,
    );
  },
  getEntitySources(
    id: string,
    signal: AbortSignal,
  ): Promise<SourcePageViewModel> {
    return getData<NonNullable<SourcesResponse["data"]>>(
      `/api/v1/entities/${encodeURIComponent(id)}/sources?limit=20&offset=0`,
      signal,
    );
  },
  getRelationSources(
    id: string,
    signal: AbortSignal,
  ): Promise<SourcePageViewModel> {
    return getData<NonNullable<SourcesResponse["data"]>>(
      `/api/v1/relations/${encodeURIComponent(id)}/sources?limit=20&offset=0`,
      signal,
    );
  },
  getEntityMedia(id: string, signal: AbortSignal): Promise<MediaPageViewModel> {
    return getData<NonNullable<MediaResponse["data"]>>(
      `/api/v1/entities/${encodeURIComponent(id)}/media?limit=20&offset=0`,
      signal,
    );
  },
};

export type ExplorationApi = typeof explorationApi;
