import { useMemo, useState } from "react";

import type { MapEntity } from "../model/historyData";
import { getStarGraph } from "../model/relationshipGraph";
import { GraphNodeIcon } from "./GraphNodeIcon";
import { PlaceOverview } from "./OverviewPanels";
import { PanelPlaceholder, PanelTabs } from "./PanelTabs";
import "./explorer-details.css";

interface NetworkPanelProps {
  entity: MapEntity;
  onOpenEntity: (id: string) => void;
}

const panelTabs = [
  "Обзор",
  "Связи",
  "Герои",
  "События",
  "Достопримечательности",
  "Источники",
];

function ConnectionCanvas({ entity, onOpenEntity }: NetworkPanelProps) {
  const graph = useMemo(() => getStarGraph(entity.id), [entity.id]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  return (
    <div className="hx-network-canvas">
      <svg viewBox="0 0 100 100" aria-hidden="true" preserveAspectRatio="none">
        {graph.nodes.map((node) => (
          <line
            key={node.id}
            className={`hx-graph-line hx-kind-${node.kind} ${selectedNode && selectedNode !== node.id ? "hx-graph-line-muted" : "hx-graph-line-active"}`}
            x1="50"
            y1="52"
            x2={node.x}
            y2={node.y}
          />
        ))}
      </svg>
      <div className={`hx-network-center hx-kind-${graph.centerKind}`}>
        <strong>{graph.centerName}</strong>
        <span>{graph.centerCaption}</span>
      </div>
      {graph.nodes.map((node) => (
        <button
          type="button"
          key={node.id}
          className={`hx-orbit-node hx-kind-${node.kind} ${selectedNode && selectedNode !== node.id ? "hx-graph-node-muted" : ""}`}
          style={{ left: `${String(node.x)}%`, top: `${String(node.y)}%` }}
          aria-pressed={selectedNode === node.id}
          onClick={() => {
            setSelectedNode((current) =>
              current === node.id ? null : node.id,
            );
            onOpenEntity(node.id);
          }}
        >
          <span>
            <GraphNodeIcon kind={node.kind} />
          </span>
          <small>{node.label}</small>
        </button>
      ))}
      <ul className="hx-graph-alternative" aria-label={`Связи: ${entity.name}`}>
        {graph.nodes.map((node) => (
          <li key={node.id}>
            {node.label} · {node.caption}
          </li>
        ))}
      </ul>
      <span className="hx-visually-hidden" role="status">
        {selectedNode ? "Выбрана связь" : "Показаны все связи"}
      </span>
    </div>
  );
}

function PlaceProfile({ entity }: { entity: MapEntity }) {
  const [shareStatus, setShareStatus] = useState("");
  const stats: Array<[string, number]> = [
    ["Героев", entity.stats.heroes],
    ["Событий", entity.stats.events],
    ["Достопримечательностей", entity.stats.landmarks],
    ["Источников", entity.stats.sources],
  ];

  return (
    <figure className="hx-place-figure">
      <img
        src={entity.image}
        alt={`Изображение: ${entity.name}`}
        width="1280"
        height="720"
        loading="lazy"
      />
      <figcaption>
        <strong>{entity.name}</strong>
        <span>{entity.subtitle}</span>
        <span>{entity.summary}</span>
      </figcaption>
      <dl className="hx-place-stats">
        {stats.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <button
        className="hx-secondary-button"
        type="button"
        onClick={() => {
          const clipboard = navigator.clipboard;
          void clipboard
            .writeText(window.location.href)
            .then(() => {
              setShareStatus("Ссылка скопирована");
            })
            .catch(() => {
              setShareStatus("Не удалось скопировать ссылку");
            });
        }}
      >
        Поделиться
      </button>
      <span className="hx-visually-hidden" role="status">
        {shareStatus}
      </span>
    </figure>
  );
}

export function NetworkPanel({ entity, onOpenEntity }: NetworkPanelProps) {
  const [activeTab, setActiveTab] = useState("Связи");
  return (
    <section className="hx-detail-panel" id="details" tabIndex={-1}>
      <header>
        <h2>{entity.name}</h2>
      </header>
      <PanelTabs
        label="Разделы населённого пункта"
        tabs={panelTabs}
        activeTab={activeTab}
        onChange={setActiveTab}
      />
      {activeTab === "Связи" ? (
        <div className="hx-detail-content">
          <PlaceProfile entity={entity} />
          <div className="hx-network-column">
            <ConnectionCanvas entity={entity} onOpenEntity={onOpenEntity} />
          </div>
        </div>
      ) : activeTab === "Обзор" ? (
        <PlaceOverview entity={entity} />
      ) : (
        <PanelPlaceholder tab={activeTab} />
      )}
    </section>
  );
}
