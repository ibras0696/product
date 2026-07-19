import type { Map as MapLibreMap, Marker } from "maplibre-gl";

import type { MapEntity } from "../model/historyData";
import { regionalSelectionZoom } from "./mapCamera";
import { createMarkerLayout, type MarkerGroup } from "./markerLayout";

interface MarkerRenderOptions {
  map: MapLibreMap;
  maplibre: typeof import("maplibre-gl");
  entities: MapEntity[];
  selectedId: string;
  onSelect: (id: string) => void;
  elements: Map<string, HTMLButtonElement>;
}

function createMarkerElement(group: MarkerGroup, selectedId: string) {
  const entity = group.entities[0];
  const clustered = group.entities.length > 1;
  const button = document.createElement("button");
  button.type = "button";
  button.className = clustered
    ? "hx-geo-marker hx-geo-cluster"
    : `hx-geo-marker hx-kind-${entity.kind}`;
  if (!group.showLabel) button.classList.add("hx-geo-marker-label-hidden");
  const label = clustered
    ? `${String(group.entities.length)} объектов`
    : entity.name;
  button.setAttribute("aria-label", label);
  button.setAttribute("aria-pressed", String(entity.id === selectedId));

  const dot = document.createElement("span");
  dot.className = "hx-geo-marker-dot";
  dot.setAttribute("aria-hidden", "true");
  if (clustered) dot.textContent = String(group.entities.length);
  const caption = document.createElement("span");
  caption.className = "hx-geo-marker-label";
  caption.textContent = label;
  button.append(dot, caption);
  return button;
}

function activateGroup(
  map: MapLibreMap,
  group: MarkerGroup,
  onSelect: (id: string) => void,
) {
  const entity = group.entities[0];
  if (group.entities.length === 1) {
    onSelect(entity.id);
    return;
  }
  map.easeTo({
    center: [...group.coordinates],
    zoom: regionalSelectionZoom(map.getZoom() + 1.2),
  });
}

export function renderMapMarkers(options: MarkerRenderOptions): Marker[] {
  const layout = createMarkerLayout(
    options.entities,
    options.selectedId,
    options.map.getZoom(),
    (coordinates) => options.map.project([...coordinates]),
  );
  options.elements.clear();
  return layout.map((group) => {
    const element = createMarkerElement(group, options.selectedId);
    element.addEventListener("click", () => {
      activateGroup(options.map, group, options.onSelect);
    });
    group.entities.forEach((entity) => {
      options.elements.set(entity.id, element);
    });
    return new options.maplibre.Marker({ element, anchor: "center" })
      .setLngLat([...group.coordinates])
      .addTo(options.map);
  });
}
