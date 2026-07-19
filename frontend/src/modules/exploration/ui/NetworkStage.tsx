import { useId, useState } from "react";

import type { GraphViewModel } from "../api/viewModels";
import { NetworkCanvas, NetworkLegend } from "./NetworkCanvas";
import { RelationEvidence } from "./RelationEvidence";
import {
  buildNetworkBranches,
  relationTypeLabels,
  type NetworkBranch as NetworkBranchModel,
  type NetworkEdge,
} from "./networkGraph";

interface NetworkStageProps {
  graph?: GraphViewModel;
  selectedId: string | null;
  status: "loading" | "error" | "ready";
  onOpenEntity: (id: string) => void;
  onRetry: () => void;
  onReset: () => void;
}

function NetworkState({
  kind,
  onAction,
}: {
  kind: "loading" | "error" | "empty";
  onAction: () => void;
}) {
  const content = {
    loading: [
      "Загружаем паутину связей…",
      "Получаем связи глубиной до двух уровней.",
    ],
    error: [
      "Связи временно недоступны",
      "Повторите запрос подтверждённых отношений.",
    ],
    empty: ["Связей пока нет", "Выберите другой объект или сбросьте фильтры."],
  } as const;
  return (
    <div
      className="hx-network-state"
      role={kind === "error" ? "alert" : "status"}
    >
      <strong>{content[kind][0]}</strong>
      <span>{content[kind][1]}</span>
      {kind !== "loading" ? (
        <button type="button" onClick={onAction}>
          {kind === "error" ? "Повторить" : "Сбросить фильтры"}
        </button>
      ) : null}
    </div>
  );
}

function RelationRow({
  edge,
  expanded,
  onToggle,
}: {
  edge: NetworkEdge;
  expanded: boolean;
  onToggle: (id: string) => void;
}) {
  return (
    <li className="hx-network-relation">
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => {
          onToggle(edge.id);
        }}
      >
        <span>{edge.title.ru}</span>
        <small>
          {relationTypeLabels[edge.type]} · источников: {edge.sources_count}
        </small>
      </button>
      {expanded ? <RelationEvidence relationId={edge.id} /> : null}
    </li>
  );
}

function RelationList({
  edges,
  activeRelationId,
  onToggleRelation,
}: {
  edges: NetworkEdge[];
  activeRelationId: string | null;
  onToggleRelation: (id: string) => void;
}) {
  return (
    <ul className="hx-network-relations">
      {edges.map((edge) => (
        <RelationRow
          key={edge.id}
          edge={edge}
          expanded={activeRelationId === edge.id}
          onToggle={onToggleRelation}
        />
      ))}
    </ul>
  );
}

function LevelTwoNode({
  item,
  activeRelationId,
  onOpenEntity,
  onToggleRelation,
}: {
  item: NetworkBranchModel["levelTwoNodes"][number];
  activeRelationId: string | null;
  onOpenEntity: (id: string) => void;
  onToggleRelation: (id: string) => void;
}) {
  return (
    <li className="hx-network-node hx-network-node-level-two">
      <button
        type="button"
        onClick={() => {
          onOpenEntity(item.node.id);
        }}
      >
        <strong>{item.node.title.ru}</strong>
        <small>Уровень 2 · связей: {item.node.relations_count}</small>
      </button>
      <RelationList
        edges={item.edges}
        activeRelationId={activeRelationId}
        onToggleRelation={onToggleRelation}
      />
    </li>
  );
}

function NetworkBranch({
  branch,
  activeRelationId,
  onOpenEntity,
  onToggleRelation,
}: {
  branch: NetworkBranchModel;
  activeRelationId: string | null;
  onOpenEntity: (id: string) => void;
  onToggleRelation: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const branchId = useId();
  const childCount = branch.levelTwoNodes.length;
  return (
    <li className="hx-network-branch">
      <div className="hx-network-branch-head">
        <button
          type="button"
          onClick={() => {
            onOpenEntity(branch.node.id);
          }}
        >
          <strong>{branch.node.title.ru}</strong>
          <small>Уровень 1 · связей: {branch.node.relations_count}</small>
        </button>
        {childCount > 0 ? (
          <button
            type="button"
            aria-expanded={expanded}
            aria-controls={branchId}
            onClick={() => {
              setExpanded((current) => !current);
            }}
          >
            {expanded
              ? "Свернуть ветвь"
              : `Развернуть ветвь (${String(childCount)})`}
          </button>
        ) : null}
      </div>
      <RelationList
        edges={[...branch.centerEdges, ...branch.peerEdges]}
        activeRelationId={activeRelationId}
        onToggleRelation={onToggleRelation}
      />
      {expanded && childCount > 0 ? (
        <ul id={branchId} className="hx-network-level-two">
          {branch.levelTwoNodes.map((item) => (
            <LevelTwoNode
              key={item.node.id}
              item={item}
              activeRelationId={activeRelationId}
              onOpenEntity={onOpenEntity}
              onToggleRelation={onToggleRelation}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

export function NetworkStage(props: NetworkStageProps) {
  const [activeRelationId, setActiveRelationId] = useState<string | null>(null);
  const graph =
    props.graph?.center.id === props.selectedId ? props.graph : undefined;
  if (props.status !== "ready") {
    return <NetworkState kind={props.status} onAction={props.onRetry} />;
  }
  if (!graph || (graph.nodes.length === 0 && graph.edges.length === 0)) {
    return <NetworkState kind="empty" onAction={props.onReset} />;
  }
  const branches = buildNetworkBranches(graph);
  return (
    <section className="hx-network-stage" aria-labelledby="network-stage-title">
      <header>
        <div>
          <span>Глубина связей: 2</span>
          <h2 id="network-stage-title">Паутина: {graph.center.title.ru}</h2>
        </div>
        <p>
          {graph.hidden_nodes_count > 0
            ? `За пределами лимита скрыто объектов: ${String(graph.hidden_nodes_count)}`
            : "Показаны все доступные связи в пределах двух уровней."}
        </p>
      </header>
      <NetworkLegend graph={graph} />
      <NetworkCanvas graph={graph} onOpenEntity={props.onOpenEntity} />
      <ul
        className="hx-network-branches"
        aria-label={`Связи объекта ${graph.center.title.ru}`}
      >
        {branches.map((branch) => (
          <NetworkBranch
            key={branch.node.id}
            branch={branch}
            activeRelationId={activeRelationId}
            onOpenEntity={props.onOpenEntity}
            onToggleRelation={(id) => {
              setActiveRelationId((current) => (current === id ? null : id));
            }}
          />
        ))}
      </ul>
    </section>
  );
}
