// Проекция гео-координат в SVG-пространство для стилизованной арт-карты.
// Форма и границы берутся из реального контура Чечни (chechnyaBoundary.ts),
// поэтому узлы располагаются географически корректно внутри силуэта.
import { chechnyaBoundaryGeoJson } from "../model/chechnyaBoundary";
import type { GeoCoordinates } from "../model/types";

interface ScreenPoint {
  x: number;
  y: number;
}

const ring = chechnyaBoundaryGeoJson.geometry.coordinates[0] as ReadonlyArray<
  readonly [number, number]
>;

const lons = ring.map(([lon]) => lon);
const lats = ring.map(([, lat]) => lat);
const minLon = Math.min(...lons);
const maxLon = Math.max(...lons);
const minLat = Math.min(...lats);
const maxLat = Math.max(...lats);

const midLat = (minLat + maxLat) / 2;
const cosLat = Math.cos((midLat * Math.PI) / 180);
const scale = 640;
const pad = 54;

export const mapWidth = (maxLon - minLon) * cosLat * scale + pad * 2;
export const mapHeight = (maxLat - minLat) * scale + pad * 2;
export const viewBox = `0 0 ${String(mapWidth)} ${String(mapHeight)}`;

export function projectGeo(coordinates: GeoCoordinates): ScreenPoint {
  const [lon, lat] = coordinates;
  return {
    x: pad + (lon - minLon) * cosLat * scale,
    y: pad + (maxLat - lat) * scale,
  };
}

export const boundaryPathD =
  ring
    .map((point, index) => {
      const { x, y } = projectGeo(point);
      return `${index === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ") + " Z";

export const outsideMaskPathD =
  `M 0 0 H ${String(mapWidth)} V ${String(mapHeight)} H 0 Z ` + boundaryPathD;
