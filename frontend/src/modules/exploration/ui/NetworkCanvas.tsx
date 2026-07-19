import { MinusIcon, PlusIcon } from "@phosphor-icons/react";
import { useState } from "react";

import type { GraphViewModel } from "../api/viewModels";
import {
  buildNetworkLegend,
  createNetworkLayout,
  relationTypeLabels,
} from "./networkGraph";

export function NetworkLegend({ graph }: { graph: GraphViewModel }) {
  return (
    <aside className="hx-network-legend" aria-label="Типы отношений в паутине">
      <strong>Легенда отношений</strong>
      <ul>
        {buildNetworkLegend(graph).map((item) => (
          <li key={item.type}>
            <span
              className={`hx-network-line-${item.type}`}
              aria-hidden="true"
            />
            <div>
              <strong>{relationTypeLabels[item.type]}</strong>
              <small>{item.titles.join(" · ")}</small>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}

export function NetworkCanvas({
  graph,
  onOpenEntity,
}: {
  graph: GraphViewModel;
  onOpenEntity: (id: string) => void;
}) {
  const layout = createNetworkLayout(graph);
  const [zoom, setZoom] = useState(1);
  const canvasWidth = Math.round(layout.width * zoom);
  const canvasHeight = Math.round(layout.height * zoom);
  return (
    <section className="hx-network-visual">
      <div className="hx-network-zoom" aria-label="Масштаб паутины">
        <button
          type="button"
          aria-label="Уменьшить паутину"
          disabled={zoom <= 0.75}
          onClick={() => {
            setZoom((current) => Math.max(current - 0.25, 0.75));
          }}
        >
          <MinusIcon size={18} aria-hidden="true" />
        </button>
        <output aria-live="polite">{Math.round(zoom * 100)}%</output>
        <button
          type="button"
          aria-label="Увеличить паутину"
          disabled={zoom >= 1.5}
          onClick={() => {
            setZoom((current) => Math.min(current + 0.25, 1.5));
          }}
        >
          <PlusIcon size={18} aria-hidden="true" />
        </button>
      </div>
      <div className="hx-network-viewport" tabIndex={0}>
        <div
          className="hx-network-canvas"
          role="group"
          aria-label={`Визуальная паутина связей объекта ${graph.center.title.ru}`}
          style={{ width: canvasWidth, height: canvasHeight }}
        >
          <svg
            viewBox={`0 0 ${String(layout.width)} ${String(layout.height)}`}
            aria-hidden="true"
          >
            {layout.edges.map(({ edge, source, target }) => (
              <line
                key={edge.id}
                className={`hx-network-edge hx-network-line-${edge.type}`}
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
              />
            ))}
          </svg>
          {layout.nodes.map((node) => (
            <button
              key={node.id}
              type="button"
              className={`hx-network-visual-node hx-network-visual-node-level-${String(node.level)}`}
              style={{
                left: `${String((node.x / layout.width) * 100)}%`,
                top: `${String((node.y / layout.height) * 100)}%`,
              }}
              aria-label={`${node.title}, уровень ${String(node.level)}`}
              aria-current={node.level === 0 ? "true" : undefined}
              onClick={() => {
                onOpenEntity(node.id);
              }}
            >
              {node.title}
            </button>
          ))}
          {layout.omittedNodesCount > 0 ? (
            <p>
              Не показано несвязанных узлов: {layout.omittedNodesCount}. Все
              объекты доступны в списке ниже.
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
