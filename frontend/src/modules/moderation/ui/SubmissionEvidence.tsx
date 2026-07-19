import type { ModerationSubmission } from "../domain/types";
import { SubmissionMediaGallery } from "./SubmissionMedia";

export function SubmissionEvidence({
  submission,
}: {
  submission: ModerationSubmission;
}) {
  return (
    <>
      <section className="mod-evidence" aria-labelledby="mod-material-title">
        <h3 id="mod-material-title">Материал автора</h3>
        <p>{submission.description}</p>
        <dl>
          <div>
            <dt>Автор</dt>
            <dd>{submission.authorName}</dd>
          </div>
          <div>
            <dt>Контакт</dt>
            <dd>{submission.contact}</dd>
          </div>
          <div>
            <dt>Источник</dt>
            <dd>{submission.sourceDescription}</dd>
          </div>
          <div>
            <dt>Согласие</dt>
            <dd>{submission.consent ? "Получено" : "Не получено"}</dd>
          </div>
        </dl>
      </section>
      <section className="mod-media" aria-labelledby="mod-media-title">
        <h3 id="mod-media-title">Медиа заявки</h3>
        <SubmissionMediaGallery media={submission.media} />
      </section>
    </>
  );
}
