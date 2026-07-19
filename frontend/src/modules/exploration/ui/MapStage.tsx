import type { ExplorerView, MapEntity, Relation } from "../model/historyData";
import { InteractiveHistoryMap } from "./InteractiveHistoryMap";

interface MapStageProps {
  entities: MapEntity[];
  relations: Relation[];
  selectedId: string;
  focusEntityId: string | null;
  view: ExplorerView;
  status: "loading" | "error" | "ready";
  truncated: boolean;
  relationsTruncated: boolean;
  onSelect: (id: string) => void;
  onRetry: () => void;
  onReset: () => void;
  onFocusRestored: () => void;
}

function MapMessage({
  kind,
  onAction,
}: {
  kind: "loading" | "error" | "empty";
  onAction: () => void;
}) {
  const content = {
    loading: ["Загружаем объекты…", "Подготавливаем опубликованные материалы."],
    error: ["Данные временно недоступны", "Повторите загрузку объектов."],
    empty: ["Ничего не найдено", "Измените поиск или сбросьте фильтры."],
  } as const;
  return (
    <div className="hx-map-empty" role={kind === "error" ? "alert" : "status"}>
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

export function MapStage({
  entities,
  relations,
  selectedId,
  focusEntityId,
  view,
  status,
  truncated,
  relationsTruncated,
  onSelect,
  onRetry,
  onReset,
  onFocusRestored,
}: MapStageProps) {
  return (
    <section
      id="atlas-map"
      className={`hx-map-stage hx-map-stage-${view}`}
      aria-label="Интерактивная карта исторических связей"
    >
      {truncated || relationsTruncated ? (
        <div className="hx-map-warning" role="status">
          {truncated
            ? "Показана часть объектов — уточните фильтры."
            : "Показана часть связей — уточните фильтры."}
        </div>
      ) : null}
      <InteractiveHistoryMap
        entities={entities}
        relations={relations}
        selectedId={selectedId}
        focusEntityId={focusEntityId}
        onSelect={onSelect}
        onFocusRestored={onFocusRestored}
        showBasemapSwitch={false}
      />
      {status === "loading" ? (
        <MapMessage kind="loading" onAction={onRetry} />
      ) : null}
      {status === "error" ? (
        <MapMessage kind="error" onAction={onRetry} />
      ) : null}
      {status === "ready" && entities.length === 0 && relations.length === 0 ? (
        <MapMessage kind="empty" onAction={onReset} />
      ) : null}
    </section>
  );
}
