import { Link } from "react-router-dom";

import type { EntityGraph, RelationType } from "../domain/entity";
import {
  createEntityGraphLayout,
  graphDepths,
} from "../model/entityGraphLayout";

const relationLabels: Record<RelationType, string> = {
  born_in: "Родился в",
  lived_in: "Жил в",
  worked_in: "Работал в",
  studied_in: "Учился в",
  taught_at: "Преподавал в",
  participated_in: "Участвовал в",
  located_in: "Расположен в",
  part_of: "Часть объекта",
  created_by: "Создан автором",
  described_in: "Описан в",
  connected_with: "Связан с",
  connected_with_chgu: "Связан с ЧГУ",
};

function GraphLegend({ graph }: { graph: EntityGraph }) {
  const types = [...new Set(graph.edges.map((edge) => edge.type))];
  return (
    <ul className="entity-graph-legend" aria-label="Типы отношений">
      {types.map((type) => (
        <li key={type}>
          <span className={`entity-graph-key entity-graph-key-${type}`} />
          {relationLabels[type]}
        </li>
      ))}
    </ul>
  );
}

function VisualGraph({ graph }: { graph: EntityGraph }) {
  const layout = createEntityGraphLayout(graph);
  return (
    <div
      className="entity-graph-canvas"
      role="group"
      aria-label={`Визуальный граф связей: ${graph.center.title.ru}`}
    >
      <svg viewBox="0 0 1000 620" aria-hidden="true">
        {layout.edges.map(({ edge, source, target }) => (
          <line
            key={edge.id}
            className={`entity-graph-edge entity-graph-key-${edge.type}`}
            x1={source.x}
            y1={source.y}
            x2={target.x}
            y2={target.y}
          />
        ))}
      </svg>
      {layout.nodes.map((node) =>
        node.level === 0 ? (
          <strong
            key={node.id}
            className="entity-graph-node entity-graph-node-0"
            style={{
              left: `${String(node.x / 10)}%`,
              top: `${String(node.y / 6.2)}%`,
            }}
          >
            {node.title}
          </strong>
        ) : (
          <Link
            key={node.id}
            className={`entity-graph-node entity-graph-node-${String(node.level)}`}
            style={{
              left: `${String(node.x / 10)}%`,
              top: `${String(node.y / 6.2)}%`,
            }}
            to={`/entities/${encodeURIComponent(node.id)}`}
            aria-label={`${node.title}, уровень ${String(node.level)}`}
          >
            {node.title}
          </Link>
        ),
      )}
      {layout.omittedCount > 0 ? (
        <p>
          На схеме скрыто узлов: {layout.omittedCount}. Полный список доступен
          ниже.
        </p>
      ) : null}
    </div>
  );
}

function RelationList({ graph }: { graph: EntityGraph }) {
  const names = new Map([
    [graph.center.id, graph.center.title.ru],
    ...graph.nodes.map((node) => [node.id, node.title.ru] as const),
  ]);
  const depths = graphDepths(graph);
  return (
    <ul className="entity-relation-list" aria-label="Подтверждённые связи">
      {graph.edges.map((edge) => (
        <li key={edge.id}>
          <div>
            <strong>{edge.title.ru}</strong>
            <span>
              {relationLabels[edge.type]} · источников: {edge.sourcesCount}
            </span>
          </div>
          <p>
            {names.get(edge.sourceId)} → {names.get(edge.targetId)}
          </p>
          <small>
            Уровень{" "}
            {Math.max(
              depths.get(edge.sourceId) ?? 0,
              depths.get(edge.targetId) ?? 0,
            )}
          </small>
        </li>
      ))}
    </ul>
  );
}

export function EntityRelationsGraph({ graph }: { graph: EntityGraph }) {
  if (graph.nodes.length === 0 || graph.edges.length === 0) {
    return (
      <p className="entity-empty">Подтверждённые связи пока не опубликованы.</p>
    );
  }
  return (
    <div className="entity-graph">
      <GraphLegend graph={graph} />
      <VisualGraph graph={graph} />
      <RelationList graph={graph} />
    </div>
  );
}
