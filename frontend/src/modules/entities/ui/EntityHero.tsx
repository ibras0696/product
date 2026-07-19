import { useEffect, useRef } from "react";

import type { EntityDetails } from "../domain/entity";
import { EntityImage } from "./EntityImage";

interface EntityHeroProps {
  entity: EntityDetails;
  onBack: () => void;
}

const typeLabels: Record<EntityDetails["type"], string> = {
  settlement: "Населённый пункт",
  person: "Персона",
  event: "Событие",
  landmark: "Достопримечательность",
  natural_object: "Природный объект",
  cultural_object: "Культурный объект",
  organization: "Организация",
  university_object: "Университетский объект",
  artifact: "Артефакт",
};

const researchStatusLabels: Record<EntityDetails["researchStatus"], string> = {
  verified: "Проверено",
  needs_review: "Требует проверки",
};

function formatPeriod(entity: EntityDetails): string {
  if (entity.periodFrom === null && entity.periodTo === null)
    return "Не указан";
  const start = entity.periodFrom === null ? "—" : String(entity.periodFrom);
  if (entity.periodTo === null) return `с ${start} года`;
  return `${start}–${String(entity.periodTo)}`;
}

export function EntityHero({ entity, onBack }: EntityHeroProps) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  const metrics = [
    ["Связей", entity.counts.relations],
    ["Источников", entity.counts.sources],
    ["Медиа", entity.counts.media],
  ] as const;

  useEffect(() => {
    headingRef.current?.focus();
  }, [entity.id]);

  return (
    <header className="entity-hero">
      <div className="entity-hero-media">
        {entity.coverUrl ? (
          <EntityImage
            src={entity.coverUrl}
            alt={`Панорама: ${entity.title.ru}`}
            width={960}
            height={640}
            eager
          />
        ) : (
          <div className="entity-cover-empty">Обложка не опубликована</div>
        )}
      </div>
      <div className="entity-hero-copy">
        <button type="button" className="entity-back" onClick={onBack}>
          Назад к карте
        </button>
        <div className="entity-hero-labels">
          <p className="entity-eyebrow">{typeLabels[entity.type]}</p>
          <span data-status={entity.researchStatus}>
            {researchStatusLabels[entity.researchStatus]}
          </span>
        </div>
        <h1 ref={headingRef} tabIndex={-1}>
          {entity.title.ru}
        </h1>
        {entity.title.ce ? (
          <p className="entity-native-title" lang="ce">
            {entity.title.ce}
          </p>
        ) : null}
        <p className="entity-lead">{entity.shortDescription.ru}</p>
        <dl className="entity-facts">
          <div>
            <dt>Период</dt>
            <dd>{formatPeriod(entity)}</dd>
          </div>
          <div>
            <dt>Координаты</dt>
            <dd>
              {entity.coordinates
                ? `${entity.coordinates.latitude.toFixed(3)}° N, ${entity.coordinates.longitude.toFixed(3)}° E`
                : "Не указаны"}
            </dd>
          </div>
        </dl>
        <dl className="entity-metrics" aria-label="Статистика сущности">
          {metrics.map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      </div>
    </header>
  );
}
