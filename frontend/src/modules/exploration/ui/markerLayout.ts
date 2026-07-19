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

const clusterZoom = 8;

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

function groupEntities(
  entities: MapEntity[],
  selectedId: string,
  zoom: number,
  project: ProjectCoordinates,
) {
  if (zoom >= clusterZoom) return entities.map((entity) => [entity]);
  const cellSize = zoom < 7.8 ? 120 : 88;
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
): MarkerGroup[] {
  const occupied: Array<{ x: number; y: number; width: number }> = [];
  return groupEntities(entities, selectedId, zoom, project)
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
