import type {
  UploadQueueController,
  UploadQueueItem,
  UploadQueueStatus,
} from "../../model/uploadQueue";

interface SubmissionMediaRowProps {
  item: UploadQueueItem;
  queue: UploadQueueController;
  disabled?: boolean;
}

const statusLabels: Record<UploadQueueStatus, string> = {
  queued: "Готов к загрузке",
  uploading: "Загружается",
  ambiguous: "Ответ потерян — повторите загрузку",
  failed: "Ошибка загрузки",
  cancelled: "Загрузка отменена",
  uploaded: "Загружен",
  saving: "Сохраняем описание",
  deleting: "Удаляем",
};

function MetadataFields({
  item,
  queue,
  disabled = false,
}: SubmissionMediaRowProps) {
  const locked = disabled || queue.isMetadataLocked(item);
  const fieldId = (name: string) => `${item.clientId}-${name}`;

  return (
    <div className="submission-media-row__fields">
      <label htmlFor={fieldId("caption")}>Подпись</label>
      <input
        id={fieldId("caption")}
        defaultValue={item.metadata.caption}
        disabled={locked}
        onBlur={(event) => {
          queue.updateMetadata(item.clientId, {
            caption: event.currentTarget.value,
          });
        }}
      />
      <label htmlFor={fieldId("author")}>Автор</label>
      <input
        id={fieldId("author")}
        defaultValue={item.metadata.author}
        disabled={locked}
        onBlur={(event) => {
          queue.updateMetadata(item.clientId, {
            author: event.currentTarget.value,
          });
        }}
      />
      <label htmlFor={fieldId("source")}>Источник</label>
      <input
        id={fieldId("source")}
        defaultValue={item.metadata.sourceDescription}
        disabled={locked}
        onBlur={(event) => {
          queue.updateMetadata(item.clientId, {
            sourceDescription: event.currentTarget.value,
          });
        }}
      />
      <label htmlFor={fieldId("date")}>Примерная дата</label>
      <input
        id={fieldId("date")}
        defaultValue={item.metadata.approximateDate ?? ""}
        disabled={locked}
        placeholder="Например, 1985 год"
        onBlur={(event) => {
          queue.updateMetadata(item.clientId, {
            approximateDate: event.currentTarget.value || null,
          });
        }}
      />
    </div>
  );
}

function RowActions({
  item,
  queue,
  disabled = false,
}: SubmissionMediaRowProps) {
  const retryable = ["failed", "ambiguous", "cancelled"].includes(item.status);
  return (
    <div className="submission-media-row__actions">
      {item.status === "uploading" ? (
        <button
          type="button"
          disabled={disabled}
          onClick={() => {
            queue.cancel(item.clientId);
          }}
        >
          Отменить
        </button>
      ) : null}
      {retryable ? (
        <button
          type="button"
          disabled={disabled}
          onClick={() => {
            queue.retry(item.clientId);
          }}
        >
          Повторить
        </button>
      ) : null}
      {!(
        ["uploading", "ambiguous", "saving", "deleting"] as UploadQueueStatus[]
      ).includes(item.status) ? (
        <button
          type="button"
          disabled={disabled}
          onClick={() => {
            queue.remove(item.clientId);
          }}
        >
          {item.media ? "Удалить" : "Убрать"}
        </button>
      ) : null}
    </div>
  );
}

export function SubmissionMediaRow(props: SubmissionMediaRowProps) {
  const { item } = props;
  const preview = item.media?.previewUrl ?? item.previewUrl;
  return (
    <li className="submission-media-row">
      {preview ? (
        <img src={preview} alt={`Предпросмотр ${item.file.name}`} />
      ) : null}
      <div className="submission-media-row__content">
        <div>
          <strong>{item.file.name}</strong>
          <span role="status" aria-live="polite">
            {statusLabels[item.status]}
          </span>
        </div>
        {item.status === "uploading" ? (
          <progress aria-label={`Загрузка ${item.file.name}`} />
        ) : null}
        {item.error ? <p role="alert">{item.error}</p> : null}
        <MetadataFields {...props} />
        <RowActions {...props} />
      </div>
    </li>
  );
}
