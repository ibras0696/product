import type {
  CatalogEntityType,
  EntityDetailsViewModel,
  GraphViewModel,
  MapEntityViewModel,
} from "../api/viewModels";
import "./explorer-footer.css";
import "./explorer-supporting.css";

interface ExplorerSupportingContentProps {
  entity: MapEntityViewModel;
  details?: EntityDetailsViewModel;
  graph?: GraphViewModel;
  graphPending: boolean;
  graphError: boolean;
  onOpenEntity: (id: string) => void;
}

const entityTypeLabels: ReadonlyMap<string, string> = new Map<
  CatalogEntityType,
  string
>([
  ["settlement", "Населённый пункт"],
  ["person", "Личность"],
  ["event", "Событие"],
  ["landmark", "Достопримечательность"],
  ["natural_object", "Природный объект"],
  ["cultural_object", "Культурный объект"],
  ["organization", "Организация"],
  ["university_object", "Объект университета"],
  ["artifact", "Артефакт"],
]);

function entityTypeLabel(type: string): string {
  return entityTypeLabels.get(type) ?? "Другой объект";
}

function entitySummary(
  entity: MapEntityViewModel,
  details?: EntityDetailsViewModel,
) {
  if (details?.id === entity.id) {
    const shortDescription = details.short_description.ru.trim();
    const fullDescription = details.full_description.ru.trim();
    const description =
      fullDescription.localeCompare(shortDescription, "ru", {
        sensitivity: "base",
      }) === 0
        ? null
        : fullDescription;
    return {
      details,
      type: details.type,
      title: details.title.ru,
      shortDescription,
      description,
    };
  }
  return {
    details: undefined,
    type: entity.entityType,
    title: entity.title.ru,
    shortDescription: null,
    description: "Описание объекта пока недоступно.",
  };
}

function EntitySummary({
  entity,
  details,
}: Pick<ExplorerSupportingContentProps, "entity" | "details">) {
  const summary = entitySummary(entity, details);
  return (
    <header className="hx-supporting-summary">
      <div>
        <span>{entityTypeLabel(summary.type)}</span>
        <h2 id="supporting-title">{summary.title}</h2>
        {summary.shortDescription ? (
          <strong>{summary.shortDescription}</strong>
        ) : null}
        {summary.description ? <p>{summary.description}</p> : null}
      </div>
      <EntityCounts entity={entity} details={summary.details} />
    </header>
  );
}

function EntityCounts({
  entity,
  details,
}: Pick<ExplorerSupportingContentProps, "entity" | "details">) {
  const counts = details
    ? [
        ["Связей", details.relations_count],
        ["Источников", details.sources_count],
        ["Медиа", details.media_count],
      ]
    : [["Связей", entity.stats.relations]];
  return (
    <dl className="hx-supporting-counts" aria-label="Данные объекта">
      {counts.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function GraphState({ pending, error }: { pending: boolean; error: boolean }) {
  if (error) {
    return (
      <p className="hx-supporting-state" role="alert">
        Не удалось загрузить связи объекта.
      </p>
    );
  }
  if (pending) {
    return (
      <div className="hx-supporting-state" role="status" aria-live="polite">
        <span className="hx-supporting-skeleton" aria-hidden="true" />
        Загружаем подтверждённые связи…
      </div>
    );
  }
  return (
    <p className="hx-supporting-state" role="status">
      У объекта пока нет опубликованных связей.
    </p>
  );
}

function GraphNodes({
  graph,
  onOpenEntity,
}: Pick<ExplorerSupportingContentProps, "graph" | "onOpenEntity"> & {
  graph: GraphViewModel;
}) {
  if (graph.nodes.length === 0) return null;
  return (
    <section className="hx-supporting-list" aria-labelledby="graph-nodes-title">
      <h3 id="graph-nodes-title">Связанные объекты</h3>
      <ul>
        {graph.nodes.map((node) => (
          <li key={node.id}>
            <button
              type="button"
              onClick={() => {
                onOpenEntity(node.id);
              }}
            >
              <span>
                <strong>{node.title.ru}</strong>
                <small>{entityTypeLabel(node.type)}</small>
              </span>
              <span aria-label={`Связей: ${String(node.relations_count)}`}>
                {node.relations_count}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function GraphEdges({ graph }: { graph: GraphViewModel }) {
  if (graph.edges.length === 0) return null;
  const titlesById = new Map([
    [graph.center.id, graph.center.title.ru],
    ...graph.nodes.map((node) => [node.id, node.title.ru] as const),
  ]);
  return (
    <section className="hx-supporting-list" aria-labelledby="graph-edges-title">
      <h3 id="graph-edges-title">Подтверждённые отношения</h3>
      <ul>
        {graph.edges.map((edge) => (
          <li className="hx-supporting-edge" key={edge.id}>
            <strong>{edge.title.ru}</strong>
            <span>
              {titlesById.get(edge.source_id) ?? "Объект недоступен"}
              <span aria-hidden="true"> → </span>
              <span className="hx-visually-hidden"> связано с </span>
              {titlesById.get(edge.target_id) ?? "Объект недоступен"}
            </span>
            {edge.description.ru ? <p>{edge.description.ru}</p> : null}
            <small>Источников: {edge.sources_count}</small>
          </li>
        ))}
      </ul>
    </section>
  );
}

function GraphContent({
  graph,
  graphPending,
  graphError,
  onOpenEntity,
}: Omit<ExplorerSupportingContentProps, "entity" | "details">) {
  if (graphError || graphPending || !graph) {
    return <GraphState pending={graphPending} error={graphError} />;
  }
  if (graph.nodes.length === 0 && graph.edges.length === 0) {
    return <GraphState pending={false} error={false} />;
  }
  return (
    <div className="hx-supporting-graph">
      <div className="hx-supporting-graph-meta" aria-label="Состав графа">
        <span>Объектов: {graph.nodes.length}</span>
        <span>Отношений: {graph.edges.length}</span>
        {graph.hidden_nodes_count > 0 ? (
          <span>Скрыто объектов: {graph.hidden_nodes_count}</span>
        ) : null}
      </div>
      <div className="hx-supporting-columns">
        <GraphNodes graph={graph} onOpenEntity={onOpenEntity} />
        <GraphEdges graph={graph} />
      </div>
    </div>
  );
}

export function ExplorerSupportingContent({
  entity,
  details,
  graph,
  graphPending,
  graphError,
  onOpenEntity,
}: ExplorerSupportingContentProps) {
  const currentGraph = graph?.center.id === entity.id ? graph : undefined;
  return (
    <>
      <div className="hx-supporting-wrap">
        <section
          className="hx-supporting-panel"
          aria-labelledby="supporting-title"
        >
          <EntitySummary entity={entity} details={details} />
          <GraphContent
            graph={currentGraph}
            graphPending={graphPending}
            graphError={graphError}
            onOpenEntity={onOpenEntity}
          />
        </section>
      </div>
      <footer className="hx-footer" id="about">
        <span>Паутина истории Чечни</span>
        <p>
          Публичный атлас опубликованных исторических объектов и подтверждённых
          связей.
        </p>
        <a href="#atlas">Вернуться к карте</a>
      </footer>
    </>
  );
}
