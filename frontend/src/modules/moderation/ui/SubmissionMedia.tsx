import type { FieldValues, Path, UseFormRegister } from "react-hook-form";

import type { ModerationMedia } from "../domain/types";

interface SelectableValues {
  approvedMediaIds: string[];
}

function formatBytes(sizeBytes: number): string {
  if (sizeBytes < 1024) return `${String(sizeBytes)} Б`;
  const kibibytes = sizeBytes / 1024;
  if (kibibytes < 1024) return `${kibibytes.toFixed(1)} КБ`;
  return `${(kibibytes / 1024).toFixed(1)} МБ`;
}

function Preview({ media }: { media: ModerationMedia }) {
  if (!media.previewUrl) {
    return (
      <div className="mod-media-preview mod-media-preview--unavailable">
        Предпросмотр недоступен
      </div>
    );
  }
  return (
    <img
      className="mod-media-preview"
      src={media.previewUrl}
      alt={media.caption || `Предпросмотр файла ${media.originalName}`}
      width={media.width}
      height={media.height}
      loading="lazy"
      decoding="async"
    />
  );
}

function MediaMetadata({ media }: { media: ModerationMedia }) {
  return (
    <dl className="mod-media-metadata">
      <div>
        <dt>Файл</dt>
        <dd>{media.originalName}</dd>
      </div>
      <div>
        <dt>Формат и размер</dt>
        <dd>
          {media.mimeType} · {formatBytes(media.sizeBytes)}
        </dd>
      </div>
      <div>
        <dt>Разрешение</dt>
        <dd>
          {media.width} × {media.height}
        </dd>
      </div>
      <div>
        <dt>Автор</dt>
        <dd>{media.author}</dd>
      </div>
      <div>
        <dt>Примерная дата</dt>
        <dd>{media.approximateDate ?? "Не указана"}</dd>
      </div>
      <div>
        <dt>Источник</dt>
        <dd>{media.sourceDescription}</dd>
      </div>
    </dl>
  );
}

export function SubmissionMediaGallery({
  media,
}: {
  media: ModerationMedia[];
}) {
  if (media.length === 0) {
    return (
      <p className="mod-empty">Автор не приложил фотографии к этой заявке.</p>
    );
  }
  return (
    <ul className="mod-media-grid">
      {media.map((item) => (
        <li key={item.id} className="mod-media-card">
          <Preview media={item} />
          <div className="mod-media-card__body">
            <h4>{item.caption || item.originalName}</h4>
            <MediaMetadata media={item} />
          </div>
        </li>
      ))}
    </ul>
  );
}

export function MediaSelection<T extends FieldValues & SelectableValues>({
  media,
  register,
}: {
  media: ModerationMedia[];
  register: UseFormRegister<T>;
}) {
  if (media.length === 0) return null;
  return (
    <fieldset className="mod-media-selection">
      <legend>Фотографии для публикации</legend>
      <p>Отметьте только проверенные фотографии. Остальные не публикуются.</p>
      <div>
        {media.map((item) => (
          <label key={item.id}>
            <input
              type="checkbox"
              value={item.id}
              {...register("approvedMediaIds" as Path<T>)}
            />
            <span>{item.caption || item.originalName}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
