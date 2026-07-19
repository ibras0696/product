import { useForm } from "react-hook-form";

import { SubmissionApplicationError } from "../../domain/errors";
import type { SubmissionStatusView } from "../../domain/submission";

interface StatusLookupValues {
  trackingCode: string;
}

interface SubmissionStatusLookupProps {
  pending: boolean;
  error: Error | null;
  result?: SubmissionStatusView;
  onLookup: (trackingCode: string) => void;
}

const statusLabels: Record<SubmissionStatusView["status"], string> = {
  draft: "Черновик",
  pending: "Ожидает проверки",
  in_review: "На рассмотрении",
  needs_revision: "Нужны уточнения",
  rejected: "Отклонена",
  published: "Опубликована",
};

function publicLookupError(error: Error) {
  if (!(error instanceof SubmissionApplicationError)) {
    return "Не удалось проверить статус. Повторите попытку.";
  }
  if (error.code === "not_found") {
    return "Заявка с таким кодом не найдена. Проверьте код целиком.";
  }
  if (error.code === "rate_limited") {
    return "Слишком много попыток. Попробуйте позже.";
  }
  return "Статус временно недоступен. Повторите попытку.";
}

export function SubmissionStatusLookup(props: SubmissionStatusLookupProps) {
  const { register, handleSubmit } = useForm<StatusLookupValues>();
  return (
    <section
      className="submission-status-lookup"
      aria-labelledby="status-title"
    >
      <div>
        <span>Уже отправляли материал?</span>
        <h2 id="status-title">Проверить статус</h2>
        <p>
          Код передаётся только в теле запроса и не попадает в адрес страницы.
        </p>
      </div>
      <form
        onSubmit={(event) => {
          void handleSubmit(({ trackingCode }) => {
            props.onLookup(trackingCode.trim());
          })(event);
        }}
      >
        <label htmlFor="submission-tracking-code">Код отслеживания</label>
        <div>
          <input
            id="submission-tracking-code"
            autoComplete="off"
            required
            minLength={40}
            {...register("trackingCode")}
          />
          <button type="submit" disabled={props.pending}>
            {props.pending ? "Проверяем…" : "Проверить"}
          </button>
        </div>
      </form>
      {props.error ? (
        <p className="submission-form-error" role="alert">
          {publicLookupError(props.error)}
        </p>
      ) : null}
      {props.result ? (
        <div className="submission-status-result" role="status">
          <strong>{statusLabels[props.result.status]}</strong>
          <span>{props.result.title}</span>
          {props.result.publicComment ? (
            <p>{props.result.publicComment}</p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
