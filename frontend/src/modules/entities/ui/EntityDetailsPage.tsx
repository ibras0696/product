import { EntityNotFoundError, type EntitiesPort } from "../api/entitiesPort";
import { entitiesApi } from "../api/entitiesApi";
import { useEntityBundle } from "../model/useEntityBundle";
import { EntityHero } from "./EntityHero";
import { EntityPageState } from "./EntityPageState";
import { EntityRelationsGraph } from "./EntityRelationsGraph";
import { MediaGallery, visualArchiveCount } from "./MediaGallery";
import { SourceEvidence } from "./SourceEvidence";
import "./entity-details.css";
import "./entity-content.css";

export interface EntityDetailsPageProps {
  entityId: string;
  onBack: () => void;
  entitiesPort?: EntitiesPort;
}

export function EntityDetailsPage({
  entityId,
  onBack,
  entitiesPort = entitiesApi,
}: EntityDetailsPageProps) {
  const query = useEntityBundle(entitiesPort, entityId);

  if (query.isPending) {
    return (
      <EntityPageState
        title="Загружаем историю"
        description="Собираем карточку, опубликованные источники и медиаматериалы."
        onBack={onBack}
      />
    );
  }

  if (query.error instanceof EntityNotFoundError) {
    return (
      <EntityPageState
        title="История не найдена"
        description="Возможно, материал ещё не опубликован или ссылка устарела."
        onBack={onBack}
      />
    );
  }

  if (query.isError) {
    return (
      <EntityPageState
        title="Не удалось открыть историю"
        description="Данные временно недоступны. Вернитесь к карте и попробуйте позднее."
        onBack={onBack}
        danger
      />
    );
  }

  const { entity, graph, sources, media } = query.data;
  const photoSources = sources.items.filter(
    (source) =>
      source.type === "photo" &&
      Boolean(source.archiveReference?.startsWith("http")),
  );
  const mediaCount = visualArchiveCount(media.items, photoSources);
  const hasDistinctFullDescription =
    entity.fullDescription.ru
      .trim()
      .localeCompare(entity.shortDescription.ru.trim(), "ru", {
        sensitivity: "base",
      }) !== 0;
  return (
    <main className="entity-page">
      <EntityHero
        entity={{
          ...entity,
          counts: { ...entity.counts, media: mediaCount },
        }}
        onBack={onBack}
      />
      <div className="entity-content">
        {hasDistinctFullDescription ? (
          <article className="entity-story">
            <p className="entity-section-index">01 / История</p>
            <h2>О месте</h2>
            <p>{entity.fullDescription.ru}</p>
          </article>
        ) : null}
        <section
          className="entity-section"
          aria-labelledby="entity-relations-heading"
        >
          <div className="entity-section-heading">
            <p className="entity-section-index">02 / Паутина связей</p>
            <h2 id="entity-relations-heading">Связи</h2>
            <span>
              {graph.nodes.length} объектов · {graph.edges.length} отношений
            </span>
          </div>
          <EntityRelationsGraph graph={graph} />
        </section>
        <section
          className="entity-section"
          aria-labelledby="entity-sources-heading"
        >
          <div className="entity-section-heading">
            <p className="entity-section-index">03 / Доказательства</p>
            <h2 id="entity-sources-heading">Источники</h2>
            <span>{sources.meta.total} опубликовано</span>
          </div>
          <SourceEvidence entityId={entity.id} sources={sources.items} />
        </section>
        <section
          className="entity-section"
          aria-labelledby="entity-media-heading"
        >
          <div className="entity-section-heading">
            <p className="entity-section-index">04 / Визуальный архив</p>
            <h2 id="entity-media-heading">Медиатека</h2>
            <span>{mediaCount} опубликовано</span>
          </div>
          <MediaGallery media={media.items} photoSources={photoSources} />
        </section>
      </div>
    </main>
  );
}
