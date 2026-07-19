import { useMemo, useState } from "react";

import { entityIds } from "../model/historyData";
import { getStarGraph } from "../model/relationshipGraph";
import { GraphNodeIcon } from "./GraphNodeIcon";
import { PersonOverview } from "./OverviewPanels";
import { PanelPlaceholder, PanelTabs } from "./PanelTabs";
import "./explorer-profile.css";
import "./explorer-sources.css";

const profileTabs = ["Обзор", "Связи", "События", "Источники"];
const personName = "Ахмат-Хаджи Кадыров";
const sourceIds = [
  "archive-01",
  "archive-02",
  "archive-03",
  "archive-04",
  "archive-05",
  "archive-06",
  "archive-07",
  "archive-08",
  "archive-09",
  "archive-10",
];
const sourceThumbnails = [
  "/images/history/grozny.jpg",
  "/images/history/mountains.jpg",
  "/images/history/chechnya-relief.jpg",
];

function ProfileGraph({
  onOpenEntity,
}: {
  onOpenEntity: (id: string) => void;
}) {
  const graph = useMemo(() => getStarGraph(entityIds.akhmadKadyrov), []);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  return (
    <div className="hx-profile-graph" aria-label="Связи выбранной персоны">
      <svg viewBox="0 0 100 100" aria-hidden="true" preserveAspectRatio="none">
        {graph.nodes.map((node) => (
          <line
            key={node.id}
            className={`hx-graph-line hx-kind-${node.kind} ${selectedNode && selectedNode !== node.id ? "hx-graph-line-muted" : "hx-graph-line-active"}`}
            x1="50"
            y1="50"
            x2={node.x}
            y2={node.y}
          />
        ))}
      </svg>
      <strong className="hx-profile-center">{personName}</strong>
      {graph.nodes.map((node) => (
        <button
          type="button"
          key={node.id}
          className={`hx-profile-node hx-kind-${node.kind} ${selectedNode && selectedNode !== node.id ? "hx-graph-node-muted" : ""}`}
          style={{
            left: `${String(node.x)}%`,
            top: `${String(node.y)}%`,
          }}
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
      <ul className="hx-graph-alternative" aria-label={`Связи: ${personName}`}>
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

function SourceStrip({ onOpenEntity }: { onOpenEntity: (id: string) => void }) {
  return (
    <div className="hx-sources">
      <div>
        <strong>Источники (12)</strong>
        <span>Документы и архивные карточки</span>
      </div>
      <ul aria-label="Примеры источников">
        {sourceIds.map((sourceId, index) => (
          <li key={sourceId} aria-label={`Источник ${String(index + 1)}`}>
            <button
              type="button"
              aria-label={`Открыть источник ${String(index + 1)}`}
              onClick={() => {
                onOpenEntity(entityIds.archiveCollection);
              }}
            >
              <img
                src={sourceThumbnails[index % sourceThumbnails.length]}
                alt=""
                width="80"
                height="100"
                loading="lazy"
              />
            </button>
          </li>
        ))}
      </ul>
      <button
        className="hx-secondary-button"
        type="button"
        onClick={() => {
          onOpenEntity(entityIds.archiveCollection);
        }}
      >
        Смотреть все
      </button>
    </div>
  );
}

function ProfileTabsBar({
  activeTab,
  onChange,
}: {
  activeTab: string;
  onChange: (tab: string) => void;
}) {
  return (
    <PanelTabs
      label="Разделы личности"
      tabs={profileTabs}
      activeTab={activeTab}
      onChange={onChange}
    />
  );
}

export function ProfilePanel({
  onOpenEntity,
}: {
  onOpenEntity: (id: string) => void;
}) {
  const [activeTab, setActiveTab] = useState("Связи");
  return (
    <section className="hx-profile-panel" aria-labelledby="profile-title">
      <header>
        <h2 id="profile-title">{personName}</h2>
      </header>
      {activeTab === "Связи" ? (
        <>
          <div className="hx-profile-content">
            <figure>
              <img
                src="/images/history/akhmad-kadyrov.jpg"
                alt={personName}
                width="817"
                height="1089"
                loading="lazy"
              />
              <figcaption>
                <strong>{personName}</strong>
                <span>
                  Первый Президент Чеченской Республики, Герой России.
                </span>
                <small>1951 – 2004</small>
              </figcaption>
            </figure>
            <div className="hx-profile-graph-column">
              <ProfileTabsBar activeTab={activeTab} onChange={setActiveTab} />
              <ProfileGraph onOpenEntity={onOpenEntity} />
            </div>
          </div>
          <SourceStrip onOpenEntity={onOpenEntity} />
        </>
      ) : activeTab === "Обзор" ? (
        <>
          <ProfileTabsBar activeTab={activeTab} onChange={setActiveTab} />
          <PersonOverview />
        </>
      ) : (
        <>
          <ProfileTabsBar activeTab={activeTab} onChange={setActiveTab} />
          <PanelPlaceholder tab={activeTab} />
        </>
      )}
    </section>
  );
}
