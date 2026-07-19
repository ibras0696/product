import { Link } from "react-router-dom";

import type { EntitySource } from "../domain/entity";
import { sourceLabels } from "./sourcePresentation";

const verificationLabels: Record<EntitySource["verificationStatus"], string> = {
  verified: "Проверено",
  contextual: "Контекстный источник",
  oral_account: "Устное свидетельство",
};

export function SourceEvidence({
  entityId,
  sources,
}: {
  entityId: string;
  sources: EntitySource[];
}) {
  if (sources.length === 0) {
    return (
      <p className="entity-empty">
        Проверенные источники пока не опубликованы. Карточка остаётся открытой
        для дальнейшего документирования.
      </p>
    );
  }

  return (
    <ol className="entity-source-list">
      {sources.map((source) => (
        <li key={source.id}>
          <article className="entity-source-card">
            <div className="entity-source-topline">
              <span>{sourceLabels[source.type]}</span>
              <strong>{verificationLabels[source.verificationStatus]}</strong>
            </div>
            <h3>{source.title}</h3>
            <p>{source.description}</p>
            <dl>
              <div>
                <dt>Автор / издатель</dt>
                <dd>
                  {[source.author, source.publisher]
                    .filter(Boolean)
                    .join(" · ") || "Не указаны"}
                </dd>
              </div>
              <div>
                <dt>Год / архивный шифр</dt>
                <dd>
                  {[source.publicationYear, source.archiveReference]
                    .filter(Boolean)
                    .join(" · ") || "Не указаны"}
                </dd>
              </div>
            </dl>
            <Link
              to={`/entities/${entityId}/sources/${source.id}`}
              state={{ fromEntity: true }}
            >
              Подробнее об источнике
            </Link>
            {source.url ? (
              <a href={source.url} target="_blank" rel="noreferrer">
                Открыть источник
                <span className="entity-visually-hidden">
                  {` «${source.title}» в новой вкладке`}
                </span>
              </a>
            ) : null}
          </article>
        </li>
      ))}
    </ol>
  );
}
