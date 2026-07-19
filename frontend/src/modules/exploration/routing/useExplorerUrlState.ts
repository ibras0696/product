import { useCallback } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";

import {
  catalogEntityTypes,
  researchStatuses,
  type CatalogEntityType,
  type ResearchStatus,
} from "../api/viewModels";
import { parseExplorerYear, type ExplorerDateRange } from "../model/dateRange";
import type { ExplorerView } from "../model/historyData";

const views = new Set<ExplorerView>(["map", "network", "timeline"]);
const entityTypes = new Set<string>(catalogEntityTypes);
const allowedResearchStatuses = new Set<string>(researchStatuses);

export interface ExplorerUrlState {
  query: string;
  view: ExplorerView;
  types: CatalogEntityType[];
  researchStatuses: ResearchStatus[];
  districtId: string | null;
  periodId: string | null;
  periodFrom: number | null;
  periodTo: number | null;
  selectedId: string | null;
  modalId: string | null;
}

export interface ExplorerFilterNotice {
  code: "invalid_catalog_filters_removed";
  message: string;
}

const noticeStateKey = "explorerFilterNotice";

function navigationState(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null ? { ...value } : {};
}

function readFilterNotice(value: unknown): ExplorerFilterNotice | null {
  const state = navigationState(value);
  const notice = state[noticeStateKey];
  if (typeof notice !== "object" || notice === null) return null;
  if (!("code" in notice) || !("message" in notice)) return null;
  return notice.code === "invalid_catalog_filters_removed" &&
    typeof notice.message === "string"
    ? { code: notice.code, message: notice.message }
    : null;
}

function stateWithNotice(value: unknown, notice: ExplorerFilterNotice | null) {
  const state = navigationState(value);
  if (notice) return { ...state, [noticeStateKey]: notice };
  return Object.fromEntries(
    Object.entries(state).filter(([key]) => key !== noticeStateKey),
  );
}

function parseState(params: URLSearchParams): ExplorerUrlState {
  const viewValue = params.get("view") as ExplorerView | null;
  return {
    query: params.get("q") ?? "",
    view: viewValue && views.has(viewValue) ? viewValue : "map",
    types: (params.get("types")?.split(",") ?? []).filter(
      (value): value is CatalogEntityType => entityTypes.has(value),
    ),
    researchStatuses: (
      params.get("research_statuses")?.split(",") ?? []
    ).filter((value): value is ResearchStatus =>
      allowedResearchStatuses.has(value),
    ),
    districtId: params.get("district"),
    periodId: params.get("period"),
    periodFrom: parseExplorerYear(params.get("period_from")),
    periodTo: parseExplorerYear(params.get("period_to")),
    selectedId: params.get("entity"),
    modalId: params.get("modal"),
  };
}

function updateParam(
  current: URLSearchParams,
  key: string,
  value: string | null,
) {
  const next = new URLSearchParams(current);
  if (value) next.set(key, value);
  else next.delete(key);
  return next;
}

type SetSearchParams = ReturnType<typeof useSearchParams>[1];

function useParamSetter(setParams: SetSearchParams, locationState: unknown) {
  return useCallback(
    (
      key: string,
      value: string | null,
      replace = true,
      clearNotice = false,
    ) => {
      setParams((current) => updateParam(current, key, value), {
        replace,
        state: clearNotice
          ? stateWithNotice(locationState, null)
          : navigationState(locationState),
      });
    },
    [locationState, setParams],
  );
}

export function useExplorerUrlState() {
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const state = parseState(params);

  const setParam = useParamSetter(setParams, location.state);

  function setTypes(types: readonly CatalogEntityType[]) {
    const value = types.length > 0 ? [...types].sort().join(",") : null;
    setParam("types", value);
  }

  function setResearchStatuses(statuses: readonly ResearchStatus[]) {
    const value = statuses.length > 0 ? [...statuses].sort().join(",") : null;
    setParam("research_statuses", value);
  }

  function setDateRange(range: ExplorerDateRange) {
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        next.delete("period");
        if (range.from === null) next.delete("period_from");
        else next.set("period_from", String(range.from));
        if (range.to === null) next.delete("period_to");
        else next.set("period_to", String(range.to));
        return next;
      },
      {
        replace: true,
        state: stateWithNotice(location.state, null),
      },
    );
  }

  function resetFilters() {
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        [
          "q",
          "types",
          "research_statuses",
          "district",
          "period",
          "period_from",
          "period_to",
          "entity",
        ].forEach((key) => next.delete(key));
        return next;
      },
      { state: stateWithNotice(location.state, null) },
    );
  }

  const removeInvalidCatalogFilters = useCallback(
    (
      removeDistrict: boolean,
      removePeriod: boolean,
      notice: ExplorerFilterNotice,
    ) => {
      setParams(
        (current) => {
          const next = new URLSearchParams(current);
          if (removeDistrict) next.delete("district");
          if (removePeriod) next.delete("period");
          return next;
        },
        {
          replace: true,
          state: stateWithNotice(location.state, notice),
        },
      );
    },
    [location.state, setParams],
  );

  return {
    state,
    filterNotice: readFilterNotice(location.state),
    setQuery: (value: string) => {
      setParam("q", value || null);
    },
    setView: (value: ExplorerView) => {
      setParam("view", value === "map" ? null : value, false);
    },
    setTypes,
    setResearchStatuses,
    setDistrict: (value: string | null) => {
      setParam("district", value, true, true);
    },
    setPeriod: (value: string | null) => {
      setParam("period", value, true, true);
    },
    setDateRange,
    selectEntity: (value: string | null) => {
      setParam("entity", value, false);
    },
    openModal: (value: string) => {
      setParam("modal", value, false);
    },
    closeModal: () => {
      setParam("modal", null, true);
    },
    modalBack: () => {
      void navigate(-1);
    },
    resetFilters,
    removeInvalidCatalogFilters,
  };
}
