import type { ChangeEvent } from "react";

import type { UploadQueueController } from "../../model/uploadQueue";
import { SubmissionMediaRow } from "./SubmissionMediaRow";
import "../submission-media.css";

interface SubmissionMediaStepProps {
  queue: UploadQueueController;
  disabled?: boolean;
  required?: boolean;
}

export function SubmissionMediaStep({
  queue,
  disabled = false,
  required = false,
}: SubmissionMediaStepProps) {
  function selectFiles(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.currentTarget.files ?? []);
    const clientIds = queue.queueFiles(files);
    queue.upload(clientIds);
    event.currentTarget.value = "";
  }

  return (
    <section
      className="submission-media"
      aria-labelledby="submission-media-title"
    >
      <div className="submission-media__heading">
        <h3 id="submission-media-title">Фотографии и документы</h3>
        <span>{queue.items.length}/10</span>
      </div>
      <p>
        JPEG, PNG или WebP до 10 МиБ. Разрешение до 40 мегапикселей окончательно
        проверит сервер.
      </p>
      <p className="submission-media__requirement">
        {required
          ? "Для этого типа заявки загрузите хотя бы один файл."
          : "Файлы необязательны — этот шаг можно пропустить."}
      </p>
      <label className="submission-media__picker">
        Выбрать файлы
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          disabled={disabled || queue.items.length >= 10}
          onChange={selectFiles}
        />
      </label>
      {queue.notice ? <p role="alert">{queue.notice}</p> : null}
      <div
        className="submission-media__updates"
        aria-live="polite"
        aria-atomic="true"
      >
        {queue.items.length === 0
          ? "Файлы пока не выбраны."
          : `В очереди файлов: ${String(queue.items.length)}.`}
      </div>
      <ul className="submission-media__list" aria-label="Выбранные медиафайлы">
        {queue.items.map((item) => (
          <SubmissionMediaRow
            key={item.clientId}
            item={item}
            queue={queue}
            disabled={disabled}
          />
        ))}
      </ul>
    </section>
  );
}
