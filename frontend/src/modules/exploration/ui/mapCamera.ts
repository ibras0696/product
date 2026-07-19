export const chechnyaBoundaryBounds: [[number, number], [number, number]] = [
  [44.8322, 42.4755],
  [46.6628, 44.0106],
];

export const chechnyaViewBounds: [[number, number], [number, number]] = [
  [44.35, 42.02],
  [47.12, 44.46],
];

export const chechnyaNavigationBounds: [[number, number], [number, number]] = [
  [43.1, 40.9],
  [48.4, 45.7],
];

export const MAP_MIN_ZOOM = 4.3;
export const MAP_MAX_ZOOM = 18;
export const FALLBACK_MAP_MAX_SCALE = 6;

export const MAX_REGIONAL_SELECTION_ZOOM = 8.2;

export function regionalSelectionZoom(currentZoom: number) {
  return Math.min(currentZoom, MAX_REGIONAL_SELECTION_ZOOM);
}
