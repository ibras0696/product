import type { EntitySource, PublishedMedia } from "../domain/entity";
import { EntityImage } from "./EntityImage";

function displayPhotoTitle(title: string) {
  return title
    .replace(/^File:/i, "")
    .replace(/\.(?:jpe?g|png|webp|gif|tiff?)$/i, "")
    .replaceAll("_", " ");
}

export function visualPhotoSources(
  media: PublishedMedia[],
  sources: EntitySource[],
) {
  const mediaUrls = new Set(
    media.flatMap((item) => [item.publicUrl, item.previewUrl]),
  );
  return sources.filter(
    (source) =>
      source.type === "photo" &&
      Boolean(source.archiveReference) &&
      !mediaUrls.has(source.archiveReference ?? ""),
  );
}

export function visualArchiveCount(
  media: PublishedMedia[],
  sources: EntitySource[],
) {
  return media.length + visualPhotoSources(media, sources).length;
}

export function MediaGallery({
  media,
  photoSources = [],
}: {
  media: PublishedMedia[];
  photoSources?: EntitySource[];
}) {
  const photos = visualPhotoSources(media, photoSources);
  if (media.length === 0 && photos.length === 0) {
    return (
      <p className="entity-empty">
        Медиаматериалы ещё не опубликованы. Здесь появятся только изображения с
        описанным происхождением.
      </p>
    );
  }

  return (
    <ul className="entity-gallery">
      {media.map((item) => (
        <li key={item.id}>
          <figure>
            <a href={item.publicUrl} target="_blank" rel="noreferrer">
              <EntityImage
                src={item.previewUrl}
                alt={item.caption}
                width={item.width}
                height={item.height}
              />
              <span className="entity-visually-hidden">
                Открыть изображение в полном размере в новой вкладке
              </span>
            </a>
            <figcaption>
              <strong>{item.caption}</strong>
              <span>
                {item.width} × {item.height} · {item.mimeType}
              </span>
              <span>{item.sourceDescription}</span>
            </figcaption>
          </figure>
        </li>
      ))}
      {photos.map((source) => {
        const title = displayPhotoTitle(source.title);
        return (
          <li key={source.id}>
            <figure>
              <a
                href={source.url ?? source.archiveReference ?? "#"}
                target="_blank"
                rel="noreferrer"
              >
                <EntityImage src={source.archiveReference ?? ""} alt={title} />
                <span className="entity-visually-hidden">
                  Открыть оригинал изображения в новой вкладке
                </span>
              </a>
              <figcaption>
                <strong>{title}</strong>
                <span>{source.author ?? "Автор не указан"}</span>
                <span>{source.description}</span>
                <span>Происхождение: опубликованный фотоисточник</span>
              </figcaption>
            </figure>
          </li>
        );
      })}
    </ul>
  );
}
