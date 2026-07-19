import { useQuery } from "@tanstack/react-query";

import { explorationApi } from "./explorationApi";
import { normalizeFilters, normalizeSearchFilters } from "./filtering";
import type { ExplorationFilters, SearchFilters } from "./viewModels";

export const explorationQueryKeys = {
  all: ["exploration"] as const,
  map: (filters: ExplorationFilters) =>
    [...explorationQueryKeys.all, "map", normalizeFilters(filters)] as const,
  options: () => [...explorationQueryKeys.all, "options"] as const,
  search: (filters: SearchFilters) =>
    [
      ...explorationQueryKeys.all,
      "search",
      normalizeSearchFilters(filters),
    ] as const,
  entity: (id: string) => [...explorationQueryKeys.all, "entity", id] as const,
  graph: (id: string, filters: ExplorationFilters) => {
    const normalized = normalizeFilters(filters);
    return [
      ...explorationQueryKeys.all,
      "graph",
      id,
      2,
      normalized.periodFrom,
      normalized.periodTo,
    ] as const;
  },
  entitySources: (id: string) =>
    [...explorationQueryKeys.all, "entity-sources", id] as const,
  relationSources: (id: string) =>
    [...explorationQueryKeys.all, "relation-sources", id] as const,
  media: (id: string) => [...explorationQueryKeys.all, "media", id] as const,
};

export function useMapEntities(filters: ExplorationFilters) {
  return useQuery({
    queryKey: explorationQueryKeys.map(filters),
    queryFn: ({ signal }) => explorationApi.getMapEntities(filters, signal),
  });
}

export function useCatalogOptions() {
  return useQuery({
    queryKey: explorationQueryKeys.options(),
    queryFn: ({ signal }) => explorationApi.getCatalogOptions(signal),
    staleTime: 300_000,
  });
}

export function useExplorationSearch(filters: SearchFilters) {
  const query = filters.query.trim();
  return useQuery({
    queryKey: explorationQueryKeys.search(filters),
    queryFn: ({ signal }) => explorationApi.search(filters, signal),
    enabled: query.length >= 2 && query.length <= 100,
  });
}

export function useEntityDetails(id: string | null) {
  return useQuery({
    queryKey: explorationQueryKeys.entity(id ?? ""),
    queryFn: ({ signal }) => explorationApi.getEntity(requiredId(id), signal),
    enabled: Boolean(id),
  });
}

export function useEntityGraph(id: string | null, filters: ExplorationFilters) {
  return useQuery({
    queryKey: explorationQueryKeys.graph(id ?? "", filters),
    queryFn: ({ signal }) =>
      explorationApi.getGraph(requiredId(id), filters, signal),
    enabled: Boolean(id),
  });
}

export function useEntitySources(id: string | null) {
  return useQuery({
    queryKey: explorationQueryKeys.entitySources(id ?? ""),
    queryFn: ({ signal }) =>
      explorationApi.getEntitySources(requiredId(id), signal),
    enabled: Boolean(id),
  });
}

export function useRelationSources(id: string | null) {
  return useQuery({
    queryKey: explorationQueryKeys.relationSources(id ?? ""),
    queryFn: ({ signal }) =>
      explorationApi.getRelationSources(requiredId(id), signal),
    enabled: Boolean(id),
  });
}

export function useEntityMedia(id: string | null) {
  return useQuery({
    queryKey: explorationQueryKeys.media(id ?? ""),
    queryFn: ({ signal }) =>
      explorationApi.getEntityMedia(requiredId(id), signal),
    enabled: Boolean(id),
  });
}

function requiredId(id: string | null): string {
  if (!id) throw new Error("Entity query executed without an id");
  return id;
}
