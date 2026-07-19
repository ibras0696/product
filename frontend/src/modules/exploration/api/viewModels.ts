import type { components } from "@/shared/api/schema";

import type { MapEntity, Relation } from "../model/types";

export type CatalogEntityType = components["schemas"]["EntityType"];

export type ResearchStatus = components["schemas"]["ResearchStatus"];
export const researchStatuses = [
  "verified",
  "needs_review",
] as const satisfies readonly ResearchStatus[];

export const catalogEntityTypes: readonly CatalogEntityType[] = [
  "settlement",
  "person",
  "event",
  "landmark",
  "natural_object",
  "cultural_object",
  "organization",
  "university_object",
  "artifact",
];

export interface LocalizedTextViewModel {
  ru: string;
  ce: string | null;
}

export interface MapEntityViewModel extends MapEntity {
  entityType: CatalogEntityType;
  researchStatus: ResearchStatus;
  title: LocalizedTextViewModel;
  districtId: string;
  periodFrom: number | null;
  periodTo: number | null;
}

export interface ExplorationFilters {
  query?: string;
  types?: readonly CatalogEntityType[];
  researchStatuses?: readonly ResearchStatus[];
  districtId?: string;
  periodFrom?: number;
  periodTo?: number;
  limit?: number;
}

export interface SearchFilters extends ExplorationFilters {
  query: string;
  offset?: number;
}

export type EntityDetailsViewModel = components["schemas"]["EntityDetails"];
export type GraphViewModel = components["schemas"]["GraphView"];
export type SourcePageViewModel = components["schemas"]["Page_SourceView_"];
export type MediaPageViewModel = components["schemas"]["Page_PublishedMedia_"];

/** Test-fixture scenario only. Production queries never import it. */
export type MockScenario = "success" | "empty" | "error";

export interface MapEntitiesViewModel {
  items: MapEntityViewModel[];
  relations: Relation[];
  truncated: boolean;
  relationsTruncated: boolean;
}

export interface SearchItemViewModel {
  id: string;
  type: CatalogEntityType;
  title: LocalizedTextViewModel;
  subtitle: string;
  coverUrl: string;
  relationsCount: number;
}

export interface SearchResultsViewModel {
  items: SearchItemViewModel[];
  meta: { limit: number; offset: number; total: number };
}

export interface CatalogOptionsViewModel {
  districts: Array<{ id: string; title: LocalizedTextViewModel }>;
  periods: Array<{
    id: string;
    title: LocalizedTextViewModel;
    periodFrom: number | null;
    periodTo: number | null;
  }>;
  entityTypes: CatalogEntityType[];
  researchStatuses: ResearchStatus[];
}
