import type { EntitiesPort } from "../api/entitiesPort";
import { EntityNotFoundError } from "../api/entitiesPort";
import { entitiesApi } from "../api/entitiesApi";
import type { EntitySource } from "../domain/entity";
import { useEntityBundle } from "../model/useEntityBundle";
import { EntityPageState } from "./EntityPageState";
import { sourceLabels } from "./sourcePresentation";
import "./source-details.css";

export interface SourceDetailsPageProps {
  entityId: string;
  sourceId: string;
  onBack: () => void;
  entitiesPort?: EntitiesPort;
}

function SourceDocument({
  source,
  onBack,
}: {
  source: EntitySource;
  onBack: () => void;
}) {
  return (
    <main className="source-page">
      <button className="entity-back" type="button" onClick={onBack}>
        Назад к сущности
      </button>
      <article className="source-document">
        <p className="entity-section-index">Опубликованный источник</p>
        <p className="source-type">{sourceLabels[source.type]}</p>
        <h1>{source.title}</h1>
        <p className="source-description">{source.description}</p>
        <dl>
          <div>
            <dt>Автор</dt>
            <dd>{source.author ?? "Не указан"}</dd>
          </div>
          <div>
            <dt>Издатель</dt>
            <dd>{source.publisher ?? "Не указан"}</dd>
          </div>
          <div>
            <dt>Год</dt>
            <dd>{source.publicationYear ?? "Не указан"}</dd>
          </div>
          <div>
            <dt>Архивный шифр</dt>
            <dd>{source.archiveReference ?? "Не указан"}</dd>
          </div>
        </dl>
        {source.url ? (
          <a href={source.url} target="_blank" rel="noreferrer">
            Открыть оригинал
          </a>
        ) : null}
      </article>
    </main>
  );
}

export function SourceDetailsPage({
  entityId,
  sourceId,
  onBack,
  entitiesPort = entitiesApi,
}: SourceDetailsPageProps) {
  const query = useEntityBundle(entitiesPort, entityId);

  if (query.isPending) {
    return (
      <EntityPageState
        title="Загружаем источник"
        description="Получаем опубликованное описание и архивные реквизиты."
        onBack={onBack}
      />
    );
  }

  if (query.error instanceof EntityNotFoundError) {
    return (
      <EntityPageState
        title="Источник не найден"
        description="Ссылка устарела или материал ещё не опубликован."
        onBack={onBack}
      />
    );
  }

  if (query.isError) {
    return (
      <EntityPageState
        title="Не удалось открыть источник"
        description="Вернитесь к сущности и повторите позднее."
        onBack={onBack}
        danger
      />
    );
  }

  const source = query.data.sources.items.find((item) => item.id === sourceId);
  if (!source) {
    return (
      <EntityPageState
        title="Источник не найден"
        description="Ссылка устарела или материал ещё не опубликован."
        onBack={onBack}
      />
    );
  }

  return <SourceDocument source={source} onBack={onBack} />;
}
