import type { GeoCoordinates, MapEntity } from "../model/historyData";

interface ScreenPoint {
  x: number;
  y: number;
}

export interface MarkerGroup {
  id: string;
  entities: MapEntity[];
  coordinates: GeoCoordinates;
  showLabel: boolean;
}

type ProjectCoordinates = (coordinates: GeoCoordinates) => ScreenPoint;
type UnprojectCoordinates = (point: ScreenPoint) => GeoCoordinates;

function clusterCellSize(zoom: number) {
  if (zoom < 6.5) return 132;
  if (zoom < 7.5) return 108;
  if (zoom < 8.5) return 84;
  if (zoom < 10) return 62;
  return 44;
}

function averageCoordinates(entities: MapEntity[]): GeoCoordinates {
  const total = entities.reduce<GeoCoordinates>(
    (result, entity) => {
      const [longitude, latitude] = entity.coordinates;
      return [result[0] + longitude, result[1] + latitude] as const;
    },
    [0, 0],
  );
  return [total[0] / entities.length, total[1] / entities.length];
}

function stableAngle(id: string) {
  const hash = Array.from(id).reduce(
    (value, character) => (value * 31 + character.charCodeAt(0)) >>> 0,
    0,
  );
  return ((hash % 360) * Math.PI) / 180;
}

function semanticRadius(zoom: number) {
  if (zoom < 6.5) return 58;
  if (zoom < 7.5) return 96;
  return 188;
}

function semanticRing(zoom: number) {
  if (zoom < 6.5) return { capacity: 28, gap: 26 };
  if (zoom < 7.5) return { capacity: 22, gap: 44 };
  return { capacity: 16, gap: 72 };
}

function positionVirtualEntities(
  entities: MapEntity[],
  zoom: number,
  project: ProjectCoordinates,
  unproject?: UnprojectCoordinates,
) {
  if (!unproject) return entities;
  const byId = new Map(entities.map((entity) => [entity.id, entity]));
  const byAnchor = new Map<string, MapEntity[]>();
  entities.forEach((entity) => {
    if (!entity.virtualAnchorId) return;
    const values = byAnchor.get(entity.virtualAnchorId) ?? [];
    values.push(entity);
    byAnchor.set(entity.virtualAnchorId, values);
  });
  const positioned = new Map<string, MapEntity>();
  byAnchor.forEach((values, anchorId) => {
    const anchor = byId.get(anchorId);
    if (!anchor) return;
    const center = project(anchor.coordinates);
    const sorted = [...values].sort((left, right) =>
      left.id.localeCompare(right.id),
    );
    const ringLayout = semanticRing(zoom);
    sorted.forEach((entity, index) => {
      const ring = Math.floor(index / ringLayout.capacity);
      const ringValues = Math.min(
        ringLayout.capacity,
        sorted.length - ring * ringLayout.capacity,
      );
      const slot = index % ringLayout.capacity;
      const angle = stableAngle(anchorId) + (slot / ringValues) * Math.PI * 2;
      const radius = semanticRadius(zoom) + ring * ringLayout.gap;
      const coordinates = unproject({
        x: center.x + Math.cos(angle) * radius,
        y: center.y + Math.sin(angle) * radius,
      });
      positioned.set(entity.id, { ...entity, coordinates });
    });
  });
  return entities.map((entity) => positioned.get(entity.id) ?? entity);
}

function groupEntities(
  entities: MapEntity[],
  selectedId: string,
  zoom: number,
  project: ProjectCoordinates,
) {
  const cellSize = clusterCellSize(zoom);
  const buckets = new Map<string, MapEntity[]>();
  entities.forEach((entity) => {
    if (entity.id === selectedId) return;
    const point = project(entity.coordinates);
    const key = `${String(Math.floor(point.x / cellSize))}:${String(Math.floor(point.y / cellSize))}`;
    const bucket = buckets.get(key) ?? [];
    bucket.push(entity);
    buckets.set(key, bucket);
  });
  const selected = entities.find((entity) => entity.id === selectedId);
  return selected ? [[selected], ...buckets.values()] : [...buckets.values()];
}

function overlaps(
  left: { x: number; y: number; width: number },
  right: { x: number; y: number; width: number },
) {
  return (
    Math.abs(left.x - right.x) < (left.width + right.width) / 2 + 8 &&
    Math.abs(left.y - right.y) < 34
  );
}

function canShowLabel(
  group: MapEntity[],
  selectedId: string,
  zoom: number,
  box: { x: number; y: number; width: number },
  occupied: Array<{ x: number; y: number; width: number }>,
) {
  const important = group.length > 1 || group[0].id === selectedId;
  const candidate = important || zoom >= 10 || group[0].kind === "place";
  return candidate && !occupied.some((item) => overlaps(item, box));
}

export function createMarkerLayout(
  entities: MapEntity[],
  selectedId: string,
  zoom: number,
  project: ProjectCoordinates,
  unproject?: UnprojectCoordinates,
): MarkerGroup[] {
  const positionedEntities = positionVirtualEntities(
    entities,
    zoom,
    project,
    unproject,
  );
  const occupied: Array<{ x: number; y: number; width: number }> = [];
  return groupEntities(positionedEntities, selectedId, zoom, project)
    .sort((left, right) => {
      const leftPriority =
        left[0]?.id === selectedId || left.length > 1 ? 1 : 0;
      const rightPriority =
        right[0]?.id === selectedId || right.length > 1 ? 1 : 0;
      return rightPriority - leftPriority;
    })
    .map((group) => {
      const coordinates = averageCoordinates(group);
      const point = project(coordinates);
      const label =
        group.length > 1 ? `${String(group.length)} объектов` : group[0].name;
      const box = { ...point, width: Math.min(168, label.length * 7 + 34) };
      const showLabel = canShowLabel(group, selectedId, zoom, box, occupied);
      if (showLabel) occupied.push(box);
      return {
        id: group
          .map((entity) => entity.id)
          .sort()
          .join(":"),
        entities: group,
        coordinates,
        showLabel,
      };
    });
}
