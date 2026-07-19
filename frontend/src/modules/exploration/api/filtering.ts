import type {
  CatalogEntityType,
  ExplorationFilters,
  MapEntityViewModel,
  ResearchStatus,
  SearchFilters,
} from "./viewModels";

export const MAP_LIMIT = 1000;
export const SEARCH_LIMIT = 50;

export interface NormalizedFilters {
  query: string;
  types: readonly CatalogEntityType[];
  researchStatuses: readonly ResearchStatus[];
  districtId: string | null;
  periodFrom: number | null;
  periodTo: number | null;
  limit: number;
}

export interface NormalizedSearchFilters extends NormalizedFilters {
  offset: number;
}

function boundedInteger(
  value: number | undefined,
  fallback: number,
  maximum: number,
) {
  if (value === undefined || !Number.isFinite(value)) return fallback;
  return Math.min(Math.max(Math.trunc(value), 1), maximum);
}

export function normalizeFilters(
  filters: ExplorationFilters = {},
): NormalizedFilters {
  return {
    query: filters.query?.trim().toLocaleLowerCase("ru") ?? "",
    types: [...new Set(filters.types ?? [])].sort(),
    researchStatuses: [...new Set(filters.researchStatuses ?? [])].sort(),
    districtId: filters.districtId ?? null,
    periodFrom: filters.periodFrom ?? null,
    periodTo: filters.periodTo ?? null,
    limit: boundedInteger(filters.limit, MAP_LIMIT, MAP_LIMIT),
  };
}

export function normalizeSearchFilters(
  filters: SearchFilters,
): NormalizedSearchFilters {
  const normalized = normalizeFilters({
    ...filters,
    limit: filters.limit ?? 20,
  });
  return {
    ...normalized,
    limit: boundedInteger(filters.limit, 20, SEARCH_LIMIT),
    offset: Math.min(Math.max(Math.trunc(filters.offset ?? 0), 0), 1000),
  };
}

function overlapsPeriod(
  entity: MapEntityViewModel,
  filters: NormalizedFilters,
) {
  const entityFrom = entity.periodFrom ?? Number.NEGATIVE_INFINITY;
  const entityTo = entity.periodTo ?? Number.POSITIVE_INFINITY;
  const requestedFrom = filters.periodFrom ?? Number.NEGATIVE_INFINITY;
  const requestedTo = filters.periodTo ?? Number.POSITIVE_INFINITY;
  return entityFrom <= requestedTo && entityTo >= requestedFrom;
}

export function filterEntities(
  entities: readonly MapEntityViewModel[],
  filters: NormalizedFilters,
) {
  return entities.filter((entity) => {
    if (filters.types.length > 0 && !filters.types.includes(entity.entityType))
      return false;
    if (
      filters.researchStatuses.length > 0 &&
      !filters.researchStatuses.includes(entity.researchStatus)
    )
      return false;
    if (filters.districtId && entity.districtId !== filters.districtId)
      return false;
    if (!overlapsPeriod(entity, filters)) return false;
    return (
      filters.query.length === 0 ||
      entity.name.toLocaleLowerCase("ru").includes(filters.query)
    );
  });
}
