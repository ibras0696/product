import {
  CrosshairIcon,
  HandTapIcon,
  MinusIcon,
  PlusIcon,
} from "@phosphor-icons/react";
import { useState } from "react";

import type { MapEntity, Relation } from "../model/historyData";
import { useInteractiveMapEngine, type Basemap } from "./interactiveMapEngine";
import { StylizedHistoryMap } from "./StylizedHistoryMap";

interface InteractiveHistoryMapProps {
  entities: MapEntity[];
  relations: Relation[];
  selectedId: string;
  focusEntityId: string | null;
  onSelect: (id: string) => void;
  onFocusRestored: () => void;
  showBasemapSwitch?: boolean;
}

function MapControls({
  basemap,
  showSwitch,
  onBasemapChange,
  onZoomIn,
  onZoomOut,
  onFit,
}: {
  basemap: Basemap;
  showSwitch: boolean;
  onBasemapChange: (value: Basemap) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFit: () => void;
}) {
  return (
    <>
      {showSwitch ? (
        <div className="hx-basemap-switch" aria-label="Вид карты">
          {(["street", "satellite"] as const).map((item) => (
            <button
              key={item}
              type="button"
              aria-pressed={basemap === item}
              onClick={() => {
                onBasemapChange(item);
              }}
            >
              {item === "street" ? "Карта" : "Спутник"}
            </button>
          ))}
        </div>
      ) : null}
      <div className="hx-map-controls" aria-label="Управление картой">
        <button type="button" aria-label="Приблизить карту" onClick={onZoomIn}>
          <PlusIcon size={20} aria-hidden="true" />
        </button>
        <button type="button" aria-label="Отдалить карту" onClick={onZoomOut}>
          <MinusIcon size={20} aria-hidden="true" />
        </button>
        <button type="button" aria-label="Показать все объекты" onClick={onFit}>
          <CrosshairIcon size={20} aria-hidden="true" />
        </button>
      </div>
    </>
  );
}

export function InteractiveHistoryMap(props: InteractiveHistoryMapProps) {
  const { showBasemapSwitch = true, ...engineProps } = props;
  const [basemap, setBasemap] = useState<Basemap>("satellite");
  const { containerRef, state, zoomIn, zoomOut, fit } = useInteractiveMapEngine(
    { ...engineProps, basemap },
  );
  if (state === "unsupported") {
    return (
      <StylizedHistoryMap
        entities={props.entities}
        relations={props.relations}
        selectedId={props.selectedId}
        focusEntityId={props.focusEntityId}
        onSelect={props.onSelect}
        onFocusRestored={props.onFocusRestored}
      />
    );
  }
  return (
    <>
      <div
        ref={containerRef}
        className={`hx-map-canvas hx-map-canvas-${basemap}`}
      />
      {props.entities.length > 0 ? (
        <div className="hx-map-hint">
          <HandTapIcon size={24} aria-hidden="true" />
          <span>Касайтесь точек на карте, чтобы узнать больше</span>
        </div>
      ) : null}
      <MapControls
        basemap={basemap}
        showSwitch={showBasemapSwitch}
        onBasemapChange={setBasemap}
        onZoomIn={zoomIn}
        onZoomOut={zoomOut}
        onFit={fit}
      />
    </>
  );
}
