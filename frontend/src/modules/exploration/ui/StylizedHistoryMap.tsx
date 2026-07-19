import {
  ArrowClockwiseIcon,
  ArrowsOutCardinalIcon,
  HandTapIcon,
  MagnifyingGlassPlusIcon,
} from "@phosphor-icons/react";
import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
  type WheelEvent as ReactWheelEvent,
} from "react";

import type { MapEntity, Relation } from "../model/historyData";
import { FALLBACK_MAP_MAX_SCALE } from "./mapCamera";
import { createMarkerLayout, type MarkerGroup } from "./markerLayout";
import {
  boundaryPathD,
  outsideMaskPathD,
  projectGeo,
  viewBox,
} from "./stylizedMap";

interface StylizedHistoryMapProps {
  entities: MapEntity[];
  relations: Relation[];
  selectedId: string;
  focusEntityId: string | null;
  onSelect: (id: string) => void;
  onFocusRestored: () => void;
}

type PaletteKey = "place" | "person" | "event" | "landmark" | "source";

const PALETTE: Record<PaletteKey, string> = {
  place: "#8ed08a",
  person: "#5fb6ef",
  event: "#e0a24f",
  landmark: "#a888dd",
  source: "#d8c06e",
};
function paletteKey(entity: MapEntity): PaletteKey {
  return entity.kind;
}

function MapDefs() {
  return (
    <defs>
      <clipPath id="hx-cheq-clip">
        <path d={boundaryPathD} />
      </clipPath>
      <radialGradient id="hx-terrain" cx="42%" cy="34%" r="80%">
        <stop offset="0%" stopColor="#1c3327" />
        <stop offset="55%" stopColor="#0f2019" />
        <stop offset="100%" stopColor="#060f0e" />
      </radialGradient>
      {(Object.keys(PALETTE) as PaletteKey[]).map((key) => (
        <radialGradient key={key} id={`hx-glow-${key}`}>
          <stop offset="0%" stopColor={PALETTE[key]} stopOpacity="0.55" />
          <stop offset="55%" stopColor={PALETTE[key]} stopOpacity="0.16" />
          <stop offset="100%" stopColor={PALETTE[key]} stopOpacity="0" />
        </radialGradient>
      ))}
    </defs>
  );
}

function RelationLines({
  entities,
  relations,
  selectedId,
}: {
  entities: MapEntity[];
  relations: Relation[];
  selectedId: string;
}) {
  const byId = new Map(entities.map((entity) => [entity.id, entity]));
  return (
    <g className="hx-artmap-lines">
      {relations
        .filter((relation) => byId.has(relation.from) && byId.has(relation.to))
        .map((rel) => {
          const source = byId.get(rel.from);
          const target = byId.get(rel.to);
          if (!source || !target) return null;
          const a = projectGeo(source.coordinates);
          const b = projectGeo(target.coordinates);
          const active = rel.from === selectedId || rel.to === selectedId;
          return (
            <line
              key={`${rel.from}-${rel.to}`}
              className={active ? "hx-artmap-line is-active" : "hx-artmap-line"}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
            />
          );
        })}
    </g>
  );
}

function MapNode({
  group,
  selectedId,
  onSelect,
}: {
  group: MarkerGroup;
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  const entity = group.entities[0];
  const point = projectGeo(group.coordinates);
  const key = paletteKey(entity);
  const highlight = entity.id === selectedId;
  const color = PALETTE[key];
  return (
    <g
      className={`hx-node ${highlight ? "is-highlight" : ""}`}
      transform={`translate(${String(point.x)} ${String(point.y)})`}
      role="button"
      tabIndex={0}
      aria-pressed={entity.id === selectedId}
      aria-label={entity.name}
      onClick={() => {
        onSelect(entity.id);
      }}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect(entity.id);
        }
      }}
    >
      <circle r={highlight ? 40 : 24} fill={`url(#hx-glow-${key})`} />
      {highlight ? (
        <>
          <circle className="hx-node-ring" r={20} stroke={color} />
          <circle
            className="hx-node-ring hx-node-ring-2"
            r={13}
            stroke={color}
          />
        </>
      ) : null}
      <circle className="hx-node-core" r={highlight ? 7 : 5} fill={color} />
      {group.showLabel || highlight ? (
        <text className="hx-node-label" x={13} y={4.5}>
          {entity.name}
        </text>
      ) : null}
    </g>
  );
}

function MapControls({
  onPan,
  onZoom,
  onReset,
}: {
  onPan: () => void;
  onZoom: () => void;
  onReset: () => void;
}) {
  return (
    <div className="hx-artmap-controls" aria-label="Управление картой">
      <button type="button" onClick={onPan}>
        <ArrowsOutCardinalIcon size={18} aria-hidden="true" />
        Перемещение
      </button>
      <button type="button" onClick={onZoom}>
        <MagnifyingGlassPlusIcon size={18} aria-hidden="true" />
        Масштаб
      </button>
      <button type="button" onClick={onReset}>
        <ArrowClockwiseIcon size={18} aria-hidden="true" />
        Сбросить вид
      </button>
    </div>
  );
}

function MapLegend() {
  const rows: Array<[PaletteKey, string]> = [
    ["place", "Населённые пункты"],
    ["person", "Личности"],
    ["event", "События"],
    ["landmark", "Природные и культурные объекты"],
    ["source", "Источники и организации"],
  ];
  return (
    <div className="hx-artmap-legend" aria-hidden="true">
      <strong>Условные обозначения</strong>
      <ul>
        {rows.map(([key, label]) => (
          <li key={key}>
            <span
              className="hx-legend-dot"
              style={{ background: PALETTE[key] }}
            />
            {label}
          </li>
        ))}
        <li>
          <span className="hx-legend-line" />
          Связи между объектами
        </li>
      </ul>
    </div>
  );
}

function useMapViewport() {
  const [scale, setScale] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(
    null,
  );
  const style: CSSProperties = {
    transform: `translate(${String(pan.x)}px, ${String(pan.y)}px) scale(${String(scale)})`,
  };
  const handlers = {
    onPointerDown(event: ReactPointerEvent<HTMLDivElement>) {
      // Пан начинаем только с фона карты, чтобы не перехватывать клики по узлам.
      drag.current = {
        x: event.clientX,
        y: event.clientY,
        px: pan.x,
        py: pan.y,
      };
    },
    onPointerMove(event: ReactPointerEvent<HTMLDivElement>) {
      if (!drag.current || event.buttons === 0) {
        drag.current = null;
        return;
      }
      setPan({
        x: drag.current.px + (event.clientX - drag.current.x),
        y: drag.current.py + (event.clientY - drag.current.y),
      });
    },
    onPointerUp() {
      drag.current = null;
    },
    onPointerLeave() {
      drag.current = null;
    },
    onWheel(event: ReactWheelEvent<HTMLDivElement>) {
      const next = scale * (event.deltaY < 0 ? 1.15 : 0.87);
      setScale(Math.min(FALLBACK_MAP_MAX_SCALE, Math.max(1, next)));
    },
  };
  return {
    style,
    handlers,
    resetPan: () => {
      setPan({ x: 0, y: 0 });
    },
    zoom: () => {
      setScale((value) => (value >= 2.4 ? 1 : value + 0.5));
    },
    reset: () => {
      setScale(1);
      setPan({ x: 0, y: 0 });
    },
  };
}

function MapScene({
  entities,
  relations,
  selectedId,
  onSelect,
  style,
}: {
  entities: MapEntity[];
  relations: Relation[];
  selectedId: string;
  onSelect: (id: string) => void;
  style: CSSProperties;
}) {
  const markers = createMarkerLayout(entities, selectedId, 9, projectGeo);
  return (
    <svg
      className="hx-artmap-svg"
      viewBox={viewBox}
      preserveAspectRatio="xMidYMid meet"
      style={style}
      role="group"
      aria-label="Стилизованная карта Чечни с историческими объектами"
    >
      <MapDefs />
      <rect width="100%" height="100%" fill="url(#hx-terrain)" />
      <image
        className="hx-artmap-terrain-dim"
        href="/images/history/chechnya-relief.jpg"
        x="0"
        y="0"
        width="100%"
        height="100%"
        preserveAspectRatio="xMidYMid slice"
      />
      <g clipPath="url(#hx-cheq-clip)">
        <image
          className="hx-artmap-terrain-bright"
          href="/images/history/chechnya-relief.jpg"
          x="0"
          y="0"
          width="100%"
          height="100%"
          preserveAspectRatio="xMidYMid slice"
        />
      </g>
      <path
        className="hx-artmap-outside-mask"
        d={outsideMaskPathD}
        fillRule="evenodd"
      />
      <path className="hx-artmap-boundary-glow" d={boundaryPathD} />
      <path className="hx-artmap-boundary" d={boundaryPathD} />
      <RelationLines
        entities={entities}
        relations={relations}
        selectedId={selectedId}
      />
      {markers.map((group) => (
        <MapNode
          key={group.id}
          group={group}
          selectedId={selectedId}
          onSelect={onSelect}
        />
      ))}
    </svg>
  );
}

export function StylizedHistoryMap({
  entities,
  relations,
  selectedId,
  focusEntityId,
  onSelect,
  onFocusRestored,
}: StylizedHistoryMapProps) {
  const { style, handlers, resetPan, zoom, reset } = useMapViewport();

  useEffect(() => {
    if (focusEntityId) onFocusRestored();
  }, [focusEntityId, onFocusRestored]);

  return (
    <div className="hx-artmap" {...handlers}>
      <MapScene
        entities={entities}
        relations={relations}
        selectedId={selectedId}
        onSelect={onSelect}
        style={style}
      />
      {entities.length > 0 ? (
        <div className="hx-map-hint">
          <HandTapIcon size={22} aria-hidden="true" />
          <span>Касайтесь точек на карте, чтобы узнать больше</span>
        </div>
      ) : null}
      <MapLegend />
      <MapControls onPan={resetPan} onZoom={zoom} onReset={reset} />
    </div>
  );
}
