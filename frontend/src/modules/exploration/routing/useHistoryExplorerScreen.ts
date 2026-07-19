import { useCallback, useDeferredValue, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useOnlineStatus } from "@/shared/browser/useOnlineStatus";

import {
  useCatalogOptions,
  useEntityDetails,
  useEntityGraph,
  useEntityMedia,
  useEntitySources,
  useExplorationSearch,
  useMapEntities,
} from "../api/explorationQueries";
import { MAP_LIMIT } from "../api/filtering";
import type {
  CatalogEntityType,
  CatalogOptionsViewModel,
  ExplorationFilters,
  ResearchStatus,
} from "../api/viewModels";
import { useExplorerUrlState } from "./useExplorerUrlState";
import type { ExplorerUrlState } from "./useExplorerUrlState";

interface CatalogFilterValidation {
  invalidDistrict: boolean;
  invalidPeriod: boolean;
}

const focusStateKey = "restoreMapEntityFocus";

function navigationState(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null ? { ...value } : {};
}

function readFocusRequest(value: unknown): string | null {
  const focusId = navigationState(value)[focusStateKey];
  return typeof focusId === "string" ? focusId : null;
}

function validateCatalogFilters(
  state: ExplorerUrlState,
  options?: CatalogOptionsViewModel,
): CatalogFilterValidation {
  if (!options) return { invalidDistrict: false, invalidPeriod: false };
  return {
    invalidDistrict:
      state.districtId !== null &&
      !options.districts.some((item) => item.id === state.districtId),
    invalidPeriod:
      state.periodId !== null &&
      !options.periods.some((item) => item.id === state.periodId),
  };
}

function buildFilters(
  state: ExplorerUrlState,
  options?: CatalogOptionsViewModel,
): ExplorationFilters {
  const district = options?.districts.find(
    (item) => item.id === state.districtId,
  );
  const period = options?.periods.find((item) => item.id === state.periodId);
  const hasDirectDateRange =
    state.periodFrom !== null || state.periodTo !== null;
  const periodFrom = hasDirectDateRange ? state.periodFrom : period?.periodFrom;
  const periodTo = hasDirectDateRange ? state.periodTo : period?.periodTo;
  return {
    query: state.query,
    types: state.types,
    researchStatuses: state.researchStatuses,
    districtId: district?.id,
    periodFrom: periodFrom ?? undefined,
    periodTo: periodTo ?? undefined,
    limit: MAP_LIMIT,
  };
}

function toggledTypes(
  active: readonly CatalogEntityType[],
  all: readonly CatalogEntityType[],
  type: CatalogEntityType,
) {
  if (active.length === 0) return [type];
  const next = new Set(active);
  if (next.has(type)) next.delete(type);
  else next.add(type);
  return next.size === all.length ? [] : [...next];
}

function toggledStatuses(
  active: readonly ResearchStatus[],
  all: readonly ResearchStatus[],
  status: ResearchStatus,
) {
  if (active.length === 0) return [status];
  const next = new Set(active);
  if (next.has(status)) next.delete(status);
  else next.add(status);
  return next.size === all.length ? [] : [...next];
}

function catalogFilterMessage(validation: CatalogFilterValidation) {
  if (validation.invalidDistrict && validation.invalidPeriod) {
    return "Неизвестные район и период удалены из фильтров.";
  }
  return validation.invalidDistrict
    ? "Неизвестный район удалён из фильтров."
    : "Неизвестный период удалён из фильтров.";
}

function useRelatedEntityQueries(
  selectedId: string | null,
  modalId: string | null,
) {
  const graphFilters: ExplorationFilters = {};
  return {
    selectedDetailsQuery: useEntityDetails(selectedId),
    selectedGraphQuery: useEntityGraph(selectedId, graphFilters),
    modalDetailsQuery: useEntityDetails(modalId),
    modalGraphQuery: useEntityGraph(modalId, graphFilters),
    modalSourcesQuery: useEntitySources(modalId),
    modalMediaQuery: useEntityMedia(modalId),
  };
}

export function useHistoryExplorerScreen() {
  const url = useExplorerUrlState();
  const navigate = useNavigate();
  const location = useLocation();
  const online = useOnlineStatus();
  const deferredQuery = useDeferredValue(url.state.query);
  const optionsQuery = useCatalogOptions();
  const catalogValidation = validateCatalogFilters(
    url.state,
    optionsQuery.data,
  );
  const { invalidDistrict, invalidPeriod } = catalogValidation;
  const removeInvalidCatalogFilters = url.removeInvalidCatalogFilters;
  useEffect(() => {
    if (!invalidDistrict && !invalidPeriod) return;
    removeInvalidCatalogFilters(invalidDistrict, invalidPeriod, {
      code: "invalid_catalog_filters_removed",
      message: catalogFilterMessage({ invalidDistrict, invalidPeriod }),
    });
  }, [invalidDistrict, invalidPeriod, removeInvalidCatalogFilters]);
  const filters = buildFilters(url.state, optionsQuery.data);
  const mapQuery = useMapEntities(filters);
  const searchQuery = useExplorationSearch({
    ...filters,
    query: deferredQuery,
    limit: 8,
    offset: 0,
  });
  const entities = mapQuery.data?.items ?? [];
  const selectedId = url.state.selectedId || entities[0]?.id || null;
  const selectedEntity = entities.find((entity) => entity.id === selectedId);
  const entityQueries = useRelatedEntityQueries(selectedId, url.state.modalId);
  const focusEntityId = readFocusRequest(location.state);

  const clearFocusRequest = useCallback(() => {
    const nextState = Object.fromEntries(
      Object.entries(navigationState(location.state)).filter(
        ([key]) => key !== focusStateKey,
      ),
    );
    void navigate(`${location.pathname}${location.search}`, {
      replace: true,
      state: nextState,
    });
  }, [location.pathname, location.search, location.state, navigate]);

  function toggleType(type: CatalogEntityType) {
    const allTypes = optionsQuery.data?.entityTypes ?? [];
    url.setTypes(toggledTypes(url.state.types, allTypes, type));
  }

  function toggleResearchStatus(status: ResearchStatus) {
    const allStatuses = optionsQuery.data?.researchStatuses ?? [];
    url.setResearchStatuses(
      toggledStatuses(url.state.researchStatuses, allStatuses, status),
    );
  }

  return {
    url,
    online,
    optionsQuery,
    filters,
    mapQuery,
    searchQuery,
    deferredQuery,
    filterNotice: url.filterNotice,
    entities,
    selectedId,
    selectedEntity,
    ...entityQueries,
    focusEntityId,
    clearFocusRequest,
    activeTypes: new Set(url.state.types),
    activeResearchStatuses: new Set(url.state.researchStatuses),
    toggleType,
    toggleResearchStatus,
  };
}

export type HistoryExplorerScreen = ReturnType<typeof useHistoryExplorerScreen>;
