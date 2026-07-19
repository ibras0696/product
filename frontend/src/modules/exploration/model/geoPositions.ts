import { entityIds } from "./entityIds";
import type { GeoCoordinates } from "./types";

const grozny: GeoCoordinates = [45.6987, 43.3187];

export const entityGeoPositions: Readonly<Record<string, GeoCoordinates>> = {
  [entityIds.grozny]: grozny,
  [entityIds.shelkovskaya]: [46.3396, 43.5064],
  [entityIds.naurskaya]: [45.3132, 43.6507],
  [entityIds.shali]: [45.9009, 43.1484],
  [entityIds.vedeno]: [46.0952, 42.9689],
  [entityIds.kurchaloy]: [46.0881, 43.2031],
  [entityIds.itumKali]: [45.575, 42.735],
  [entityIds.urusMartan]: [45.5406, 43.1294],
  [entityIds.argun]: [45.8745, 43.2946],
  [entityIds.nozhayYurt]: [46.378, 43.092],
  [entityIds.shatoy]: [45.6886, 42.8714],
  [entityIds.benoy]: [46.466, 42.97],
  [entityIds.tsentaroy]: [46.2261, 43.2551],
  [entityIds.achkhoyMartan]: [45.2847, 43.1896],
  [entityIds.gudermes]: [46.1053, 43.3502],
  [entityIds.znamenskoye]: [45.1287, 43.6782],
  [entityIds.akhmadKadyrov]: [46.19, 43.235],
  [entityIds.tower]: [45.575, 42.74],
  [entityIds.historicMosque]: [45.9016, 43.1469],
  [entityIds.publicEducation]: [46.33, 43.065],
  [entityIds.constitution]: [45.4, 43.38],
  [entityIds.republicRestoration]: [46.04, 43.37],
  [entityIds.archiveCollection]: [45.18, 43.64],
};

export function getEntityGeoPosition(entityId: string): GeoCoordinates {
  return entityGeoPositions[entityId] ?? grozny;
}
