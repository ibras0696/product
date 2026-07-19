import {
  filterEntities,
  normalizeFilters,
  normalizeSearchFilters,
} from "./filtering";
import { mockCatalogOptions, mockMapEntities } from "./mockCatalogData";
import type {
  CatalogOptionsViewModel,
  ExplorationFilters,
  MapEntitiesViewModel,
  MockScenario,
  SearchFilters,
  SearchResultsViewModel,
} from "./viewModels";

export class ExplorationMockError extends Error {
  readonly code = "service_unavailable";

  constructor() {
    super("Mock exploration service is unavailable");
    this.name = "ExplorationMockError";
  }
}

async function scenarioBoundary(signal: AbortSignal, scenario: MockScenario) {
  signal.throwIfAborted();
  await Promise.resolve();
  signal.throwIfAborted();
  if (scenario === "error") throw new ExplorationMockError();
}

function cloneOptions(): CatalogOptionsViewModel {
  return {
    districts: mockCatalogOptions.districts.map((district) => ({
      ...district,
      title: { ...district.title },
    })),
    periods: mockCatalogOptions.periods.map((period) => ({
      ...period,
      title: { ...period.title },
    })),
    entityTypes: [...mockCatalogOptions.entityTypes],
    researchStatuses: [...mockCatalogOptions.researchStatuses],
  };
}

export interface ExplorationApi {
  getMapEntities(
    filters: ExplorationFilters,
    signal: AbortSignal,
    scenario?: MockScenario,
  ): Promise<MapEntitiesViewModel>;
  getCatalogOptions(
    signal: AbortSignal,
    scenario?: MockScenario,
  ): Promise<CatalogOptionsViewModel>;
  search(
    filters: SearchFilters,
    signal: AbortSignal,
    scenario?: MockScenario,
  ): Promise<SearchResultsViewModel>;
}

export const mockExplorationApi: ExplorationApi = {
  async getMapEntities(filters, signal, scenario = "success") {
    await scenarioBoundary(signal, scenario);
    if (scenario === "empty") {
      return {
        items: [],
        relations: [],
        truncated: false,
        relationsTruncated: false,
      };
    }
    const normalized = normalizeFilters(filters);
    const matches = filterEntities(mockMapEntities, normalized);
    return {
      items: matches.slice(0, normalized.limit),
      relations: [],
      truncated: matches.length > normalized.limit,
      relationsTruncated: false,
    };
  },

  async getCatalogOptions(signal, scenario = "success") {
    await scenarioBoundary(signal, scenario);
    if (scenario === "empty")
      return {
        districts: [],
        periods: [],
        entityTypes: [],
        researchStatuses: [],
      };
    return cloneOptions();
  },

  async search(filters, signal, scenario = "success") {
    await scenarioBoundary(signal, scenario);
    const normalized = normalizeSearchFilters(filters);
    if (normalized.query.length < 2 || normalized.query.length > 100) {
      return {
        items: [],
        meta: { limit: normalized.limit, offset: normalized.offset, total: 0 },
      };
    }
    const matches =
      scenario === "empty" ? [] : filterEntities(mockMapEntities, normalized);
    return {
      items: matches
        .slice(normalized.offset, normalized.offset + normalized.limit)
        .map((entity) => ({
          id: entity.id,
          type: entity.entityType,
          title: { ...entity.title },
          subtitle: entity.subtitle,
          coverUrl: entity.image,
          relationsCount: entity.stats.relations,
        })),
      meta: {
        limit: normalized.limit,
        offset: normalized.offset,
        total: matches.length,
      },
    };
  },
};
