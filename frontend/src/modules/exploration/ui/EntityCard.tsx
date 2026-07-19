import { CaretLeftIcon, CaretRightIcon } from "@phosphor-icons/react";
import { useState } from "react";

import type {
  EntityDetailsViewModel,
  MapEntityViewModel,
} from "../api/viewModels";
import { researchStatusLabels } from "./researchStatusLabels";

interface EntityCardProps {
  entity: MapEntityViewModel;
  details?: EntityDetailsViewModel;
  onOpenDetails: () => void;
}

const statLabels = [
  ["relations", "Связей"],
  ["heroes", "Героев"],
  ["events", "Событий"],
  ["sources", "Источников"],
] as const;

export function EntityCard({
  entity,
  details,
  onOpenDetails,
}: EntityCardProps) {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <article
      className={`hx-entity-card ${collapsed ? "hx-entity-card-collapsed" : ""}`}
      aria-labelledby="entity-panel-title"
    >
      <button
        className="hx-card-collapse"
        type="button"
        aria-label={collapsed ? "Развернуть карточку" : "Свернуть карточку"}
        aria-expanded={!collapsed}
        onClick={() => {
          setCollapsed((current) => !current);
        }}
      >
        {collapsed ? (
          <CaretLeftIcon size={18} aria-hidden="true" />
        ) : (
          <CaretRightIcon size={18} aria-hidden="true" />
        )}
      </button>
      <div className="hx-card-content" inert={collapsed}>
        <header>
          <h1 id="entity-panel-title">{entity.name}</h1>
          <span className="hx-research-status">
            {researchStatusLabels[entity.researchStatus]}
          </span>
          {details ? <strong>{details.short_description.ru}</strong> : null}
          {details ? <p>{details.full_description.ru}</p> : null}
        </header>
        {entity.image ? (
          <img
            src={entity.image}
            alt={`Панорама: ${entity.name}`}
            width="640"
            height="320"
            fetchPriority="high"
          />
        ) : null}
        <dl>
          {statLabels
            .filter(([key]) => key === "relations")
            .map(([key, label]) => (
              <div key={key}>
                <dt>{label}</dt>
                <dd>{details?.relations_count ?? entity.stats[key]}</dd>
              </div>
            ))}
        </dl>
        <button type="button" onClick={onOpenDetails}>
          Подробнее
        </button>
      </div>
    </article>
  );
}
