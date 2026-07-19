import { mapEntities } from "../model/entities";
import { entityIds } from "../model/entityIds";
import type { CatalogOptionsViewModel, MapEntityViewModel } from "./viewModels";
import { catalogEntityTypes } from "./viewModels";

export const districtIds = {
  central: "20000000-0000-4000-8000-000000000001",
  north: "20000000-0000-4000-8000-000000000002",
  east: "20000000-0000-4000-8000-000000000003",
  south: "20000000-0000-4000-8000-000000000004",
  west: "20000000-0000-4000-8000-000000000005",
} as const;

const metadata: Partial<
  Record<
    string,
    { districtId: string; periodFrom: number | null; periodTo: number | null }
  >
> = {
  [entityIds.grozny]: {
    districtId: districtIds.central,
    periodFrom: 1818,
    periodTo: null,
  },
  [entityIds.shelkovskaya]: {
    districtId: districtIds.north,
    periodFrom: 1710,
    periodTo: null,
  },
  [entityIds.naurskaya]: {
    districtId: districtIds.north,
    periodFrom: 1642,
    periodTo: null,
  },
  [entityIds.shali]: {
    districtId: districtIds.central,
    periodFrom: 1200,
    periodTo: null,
  },
  [entityIds.vedeno]: {
    districtId: districtIds.south,
    periodFrom: 1200,
    periodTo: null,
  },
  [entityIds.kurchaloy]: {
    districtId: districtIds.east,
    periodFrom: 1700,
    periodTo: null,
  },
  [entityIds.itumKali]: {
    districtId: districtIds.south,
    periodFrom: 1100,
    periodTo: null,
  },
  [entityIds.urusMartan]: {
    districtId: districtIds.west,
    periodFrom: 1700,
    periodTo: null,
  },
  [entityIds.argun]: {
    districtId: districtIds.central,
    periodFrom: 1800,
    periodTo: null,
  },
  [entityIds.nozhayYurt]: {
    districtId: districtIds.east,
    periodFrom: 1200,
    periodTo: null,
  },
  [entityIds.shatoy]: {
    districtId: districtIds.south,
    periodFrom: 1200,
    periodTo: null,
  },
  [entityIds.benoy]: {
    districtId: districtIds.east,
    periodFrom: 1200,
    periodTo: null,
  },
  [entityIds.tsentaroy]: {
    districtId: districtIds.east,
    periodFrom: 1600,
    periodTo: null,
  },
  [entityIds.achkhoyMartan]: {
    districtId: districtIds.west,
    periodFrom: 1700,
    periodTo: null,
  },
  [entityIds.gudermes]: {
    districtId: districtIds.east,
    periodFrom: 1700,
    periodTo: null,
  },
  [entityIds.znamenskoye]: {
    districtId: districtIds.north,
    periodFrom: 1800,
    periodTo: null,
  },
};

const entityTypeByKind = {
  place: "settlement",
  person: "person",
  event: "event",
  landmark: "landmark",
  source: "artifact",
} as const;

export const mockMapEntities: MapEntityViewModel[] = mapEntities.map(
  (entity) => {
    const details = metadata[entity.id];
    return {
      ...entity,
      entityType: entityTypeByKind[entity.kind],
      researchStatus:
        entity.id === entityIds.publicEducation ? "needs_review" : "verified",
      title: { ru: entity.name, ce: null },
      districtId: details?.districtId ?? districtIds.central,
      periodFrom: details?.periodFrom ?? 1900,
      periodTo: details?.periodTo ?? null,
    };
  },
);

export const mockCatalogOptions: CatalogOptionsViewModel = {
  districts: [
    { id: districtIds.central, title: { ru: "Центральная Чечня", ce: null } },
    { id: districtIds.north, title: { ru: "Северная Чечня", ce: null } },
    { id: districtIds.east, title: { ru: "Восточная Чечня", ce: null } },
    { id: districtIds.south, title: { ru: "Горная Чечня", ce: null } },
    { id: districtIds.west, title: { ru: "Западная Чечня", ce: null } },
  ],
  periods: [
    {
      id: "before-1800",
      title: { ru: "До XIX века", ce: null },
      periodFrom: null,
      periodTo: 1799,
    },
    {
      id: "1800-1916",
      title: { ru: "XIX — начало XX века", ce: null },
      periodFrom: 1800,
      periodTo: 1916,
    },
    {
      id: "1917-1990",
      title: { ru: "XX век", ce: null },
      periodFrom: 1917,
      periodTo: 1990,
    },
    {
      id: "since-1991",
      title: { ru: "Современность", ce: null },
      periodFrom: 1991,
      periodTo: null,
    },
  ],
  entityTypes: [...catalogEntityTypes],
  researchStatuses: ["verified", "needs_review"],
};
