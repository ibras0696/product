export type ExplorerView = "map" | "network" | "timeline";
export type EntityKind = "place" | "person" | "event" | "landmark" | "source";

export interface EntityStats {
  relations: number;
  heroes: number;
  events: number;
  landmarks: number;
  sources: number;
}

export interface MapEntity {
  id: string;
  kind: EntityKind;
  name: string;
  caption: string;
  subtitle: string;
  summary: string;
  image: string;
  stats: EntityStats;
  x: number;
  y: number;
  description: string;
  coordinates: GeoCoordinates;
  virtualAnchorId?: string;
}

export type GeoCoordinates = readonly [longitude: number, latitude: number];

export interface Relation {
  from: string;
  to: string;
  fromKind?: EntityKind;
  fromName?: string;
  toKind?: EntityKind;
  toName?: string;
}

export interface OrbitNode {
  label: string;
  caption: string;
  kind: EntityKind;
  x: number;
  y: number;
}
