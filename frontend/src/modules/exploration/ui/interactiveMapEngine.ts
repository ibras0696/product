import type { GeoJSONSource, Map as MapLibreMap, Marker } from "maplibre-gl";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type RefObject,
} from "react";

import type { MapEntity, Relation } from "../model/historyData";
import {
  chechnyaBoundaryGeoJson,
  chechnyaMaskGeoJson,
} from "../model/chechnyaBoundary";
import {
  chechnyaNavigationBounds,
  chechnyaViewBounds,
  MAP_MAX_ZOOM,
  MAP_MIN_ZOOM,
  regionalSelectionZoom,
} from "./mapCamera";
import { chechnyaOutsideMaskLayer, createRelationGeoJson } from "./mapGeoData";
import { renderMapMarkers } from "./mapMarkers";

export type Basemap = "street" | "satellite";
type EngineState = "loading" | "ready" | "unsupported";

const streetTiles =
  import.meta.env.VITE_MAP_TILE_URL ??
  "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const satelliteTiles =
  import.meta.env.VITE_SATELLITE_TILE_URL ??
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";

function createMapStyle() {
  return {
    version: 8 as const,
    sources: {
      street: {
        type: "raster" as const,
        tiles: [streetTiles],
        tileSize: 256,
        maxzoom: 19,
        attribution: "© OpenStreetMap contributors",
      },
      satellite: {
        type: "raster" as const,
        tiles: [satelliteTiles],
        tileSize: 256,
        maxzoom: 19,
        attribution: "Tiles © Esri — Source: Esri and imagery contributors",
      },
    },
    layers: [
      { id: "street", type: "raster" as const, source: "street" },
      { id: "satellite", type: "raster" as const, source: "satellite" },
    ],
  };
}

function hasWebGlSupport() {
  if (typeof WebGLRenderingContext === "undefined") return false;
  try {
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

function zoneGeoJson(entities: MapEntity[]) {
  return {
    type: "FeatureCollection" as const,
    features: entities
      .filter((entity) => entity.kind === "place")
      .map((entity) => ({
        type: "Feature" as const,
        properties: { id: entity.id },
        geometry: {
          type: "Point" as const,
          coordinates: [...entity.coordinates],
        },
      })),
  };
}

function addTerritoryLayers(map: MapLibreMap, entities: MapEntity[]) {
  if (!map.getSource("chechnya-mask")) {
    map.addSource("chechnya-mask", {
      type: "geojson",
      data: chechnyaMaskGeoJson,
    });
    map.addLayer(chechnyaOutsideMaskLayer);
  }
  if (!map.getSource("chechnya-boundary")) {
    map.addSource("chechnya-boundary", {
      type: "geojson",
      data: chechnyaBoundaryGeoJson,
    });
    map.addLayer({
      id: "chechnya-soft-fill",
      type: "fill",
      source: "chechnya-boundary",
      paint: { "fill-color": "#69b488", "fill-opacity": 0.055 },
    });
    map.addLayer({
      id: "chechnya-soft-halo",
      type: "line",
      source: "chechnya-boundary",
      paint: {
        "line-color": "#9ce5b5",
        "line-width": 12,
        "line-opacity": 0.24,
        "line-blur": 7,
      },
    });
    map.addLayer({
      id: "chechnya-outline",
      type: "line",
      source: "chechnya-boundary",
      paint: {
        "line-color": "#d5eadb",
        "line-width": ["interpolate", ["linear"], ["zoom"], 6, 1.2, 10, 2.2],
        "line-opacity": 0.88,
      },
    });
  }
  const zones = zoneGeoJson(entities);
  const zoneSource = map.getSource<GeoJSONSource>("history-zones");
  if (zoneSource) zoneSource.setData(zones);
  else {
    map.addSource("history-zones", { type: "geojson", data: zones });
    map.addLayer(
      {
        id: "history-zones",
        type: "circle",
        source: "history-zones",
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 6, 24, 9, 58],
          "circle-color": "#72b88e",
          "circle-opacity": 0.08,
          "circle-blur": 0.72,
          "circle-stroke-color": "#a7d9b7",
          "circle-stroke-opacity": 0.16,
          "circle-stroke-width": 1,
        },
      },
      "chechnya-outline",
    );
  }
}

function useMapEngine(
  containerRef: RefObject<HTMLDivElement | null>,
  mapRef: RefObject<MapLibreMap | null>,
  markersRef: RefObject<Marker[]>,
  moduleRef: RefObject<typeof import("maplibre-gl") | null>,
) {
  const [state, setState] = useState<EngineState>(() =>
    hasWebGlSupport() ? "loading" : "unsupported",
  );
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    let active = true;
    void import("maplibre-gl")
      .then((maplibre) => {
        if (!active || !hasWebGlSupport()) {
          if (active) setState("unsupported");
          return;
        }
        moduleRef.current = maplibre;
        const map = new maplibre.Map({
          container,
          style: createMapStyle(),
          bounds: chechnyaViewBounds,
          fitBoundsOptions: { padding: 28 },
          maxBounds: chechnyaNavigationBounds,
          minZoom: MAP_MIN_ZOOM,
          maxZoom: MAP_MAX_ZOOM,
          renderWorldCopies: false,
          attributionControl: { compact: true },
        });
        mapRef.current = map;
        map.dragRotate.disable();
        map.touchZoomRotate.disableRotation();
        void map.once("load", () => {
          if (active) setState("ready");
        });
      })
      .catch(() => {
        if (active) setState("unsupported");
      });
    return () => {
      active = false;
      markersRef.current.forEach((marker) => {
        marker.remove();
      });
      markersRef.current = [];
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [containerRef, mapRef, markersRef, moduleRef]);
  return state;
}

function syncRelationLayer(
  map: MapLibreMap,
  data: ReturnType<typeof createRelationGeoJson>,
) {
  const source = map.getSource<GeoJSONSource>("history-relations");
  if (source) {
    source.setData(data);
    return;
  }
  map.addSource("history-relations", { type: "geojson", data });
  map.addLayer({
    id: "history-relations",
    type: "line",
    source: "history-relations",
    paint: {
      "line-color": [
        "case",
        ["boolean", ["get", "connected"], false],
        "rgba(222, 243, 234, 0.94)",
        "rgba(191, 213, 205, 0.68)",
      ],
      "line-width": [
        "interpolate",
        ["linear"],
        ["zoom"],
        7,
        ["case", ["boolean", ["get", "connected"], false], 1.4, 0.7],
        11,
        ["case", ["boolean", ["get", "connected"], false], 2.4, 0.7],
      ],
      "line-opacity": [
        "case",
        ["boolean", ["get", "connected"], false],
        0.95,
        0.34,
      ],
    },
  });
}

function useMapContent(
  mapRef: RefObject<MapLibreMap | null>,
  markersRef: RefObject<Marker[]>,
  elementsRef: RefObject<Map<string, HTMLButtonElement>>,
  moduleRef: RefObject<typeof import("maplibre-gl") | null>,
  state: EngineState,
  entities: MapEntity[],
  relations: Relation[],
  selectedId: string,
  onSelect: (id: string) => void,
) {
  useEffect(() => {
    const map = mapRef.current;
    const maplibre = moduleRef.current;
    if (state !== "ready" || !map || !maplibre) return;
    addTerritoryLayers(map, entities);
    const renderMarkers = () => {
      markersRef.current.forEach((marker) => {
        marker.remove();
      });
      markersRef.current = renderMapMarkers({
        map,
        maplibre,
        entities,
        selectedId,
        onSelect,
        elements: elementsRef.current,
      });
    };
    renderMarkers();
    map.on("zoomend", renderMarkers);
    map.on("moveend", renderMarkers);
    const data = createRelationGeoJson(entities, relations, selectedId);
    syncRelationLayer(map, data);
    return () => {
      map.off("zoomend", renderMarkers);
      map.off("moveend", renderMarkers);
    };
  }, [
    elementsRef,
    entities,
    mapRef,
    markersRef,
    moduleRef,
    onSelect,
    relations,
    selectedId,
    state,
  ]);
}

function fitRegion(map: MapLibreMap) {
  map.fitBounds(chechnyaViewBounds, { padding: 28, maxZoom: 7.7 });
}

interface EngineOptions {
  basemap: Basemap;
  entities: MapEntity[];
  relations: Relation[];
  selectedId: string;
  focusEntityId: string | null;
  onSelect: (id: string) => void;
  onFocusRestored: () => void;
}

export function useInteractiveMapEngine(options: EngineOptions) {
  const {
    basemap,
    entities,
    relations,
    selectedId,
    focusEntityId,
    onSelect,
    onFocusRestored,
  } = options;
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markersRef = useRef<Marker[]>([]);
  const elementsRef = useRef(new Map<string, HTMLButtonElement>());
  const moduleRef = useRef<typeof import("maplibre-gl") | null>(null);
  const state = useMapEngine(containerRef, mapRef, markersRef, moduleRef);
  useMapContent(
    mapRef,
    markersRef,
    elementsRef,
    moduleRef,
    state,
    entities,
    relations,
    selectedId,
    onSelect,
  );

  useEffect(() => {
    const map = mapRef.current;
    if (state !== "ready" || !map) return;
    map.setLayoutProperty(
      "street",
      "visibility",
      basemap === "street" ? "visible" : "none",
    );
    map.setLayoutProperty(
      "satellite",
      "visibility",
      basemap === "satellite" ? "visible" : "none",
    );
  }, [basemap, state]);

  useEffect(() => {
    if (state !== "ready" || !focusEntityId) return;
    const map = mapRef.current;
    if (!map) return;
    const restoreFocus = () => {
      onFocusRestored();
      requestAnimationFrame(() => {
        elementsRef.current.get(focusEntityId)?.focus();
      });
    };
    void map.once("moveend", restoreFocus);
    map.easeTo({
      center: [
        ...(entities.find((entity) => entity.id === focusEntityId)
          ?.coordinates ?? chechnyaViewBounds[0]),
      ],
      zoom: regionalSelectionZoom(map.getZoom()),
    });
    return () => {
      map.off("moveend", restoreFocus);
    };
  }, [entities, focusEntityId, onFocusRestored, state]);

  const zoomIn = useCallback(() => {
    mapRef.current?.zoomIn();
  }, []);
  const zoomOut = useCallback(() => {
    mapRef.current?.zoomOut();
  }, []);
  const fit = useCallback(() => {
    if (mapRef.current) fitRegion(mapRef.current);
  }, []);
  return { containerRef, state, zoomIn, zoomOut, fit };
}
