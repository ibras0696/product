import type { ModerationPort } from "../api/moderationPort";
import { isModerationError } from "../domain/errors";
import type {
  ModerationFilters,
  ModerationPage,
  ModerationQueueItem,
  ModerationSubmission,
} from "../domain/types";
import {
  useModerationActions,
  useModerationDetail,
  useModerationQueue,
} from "../model/queries";
import { ModerationDetail } from "./ModerationDetail";
import { ModerationFiltersForm } from "./ModerationFiltersForm";
import { ModerationQueue } from "./ModerationQueue";
import "./moderation.css";
import "./moderation-detail.css";

const errorLabels = {
  bad_request: "Проверьте параметры запроса.",
  unauthorized: "Сессия завершилась. Войдите в рабочее пространство снова.",
  not_found: "Заявка не найдена или больше недоступна.",
  forbidden: "Недостаточно прав для этой операции.",
  conflict:
    "Заявка изменилась в другой вкладке. Обновите данные; введённый текст сохранён.",
  invalid_transition:
    "Действие больше не соответствует текущему статусу заявки.",
  idempotency_conflict: "Ключ решения уже использован с другим содержимым.",
  source_required: "Для публикации нужен проверенный источник.",
  validation_error: "Проверьте обязательные поля решения.",
  rate_limited: "Слишком много запросов. Повторите попытку позже.",
  internal_error: "Сервер вернул неожиданный ответ.",
  service_unavailable: "Сервис модерации временно недоступен.",
} as const;

function errorText(error: unknown): string | null {
  return isModerationError(error) ? errorLabels[error.code] : null;
}

function QueuePane({
  page,
  pending,
  error,
  filters,
  selectedId,
  onSelect,
  onFiltersChange,
}: {
  page: ModerationPage<ModerationQueueItem> | undefined;
  pending: boolean;
  error: unknown;
  filters: ModerationFilters;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onFiltersChange: (filters: ModerationFilters) => void;
}) {
  return (
    <div>
      {pending ? (
        <p className="mod-state" role="status">
          Загружаем очередь…
        </p>
      ) : null}
      {error ? (
        <p className="mod-state" role="alert">
          {errorText(error) ?? "Не удалось загрузить очередь."}
        </p>
      ) : null}
      {page ? (
        <ModerationQueue
          page={page}
          filters={filters}
          selectedId={selectedId}
          onSelect={onSelect}
          onFiltersChange={onFiltersChange}
        />
      ) : null}
    </div>
  );
}

function ReviewPane({
  submission,
  pending,
  error,
  selectedId,
  actions,
}: {
  submission: ModerationSubmission | undefined;
  pending: boolean;
  error: unknown;
  selectedId: string | null;
  actions: ReturnType<typeof useModerationActions>;
}) {
  return (
    <aside className="mod-review" aria-label="Проверка выбранной заявки">
      {!selectedId ? (
        <p className="mod-empty">Выберите заявку в очереди.</p>
      ) : null}
      {pending && selectedId ? (
        <p className="mod-state" role="status">
          Загружаем заявку…
        </p>
      ) : null}
      {error ? (
        <p className="mod-state" role="alert">
          {errorText(error) ?? "Не удалось загрузить заявку."}
        </p>
      ) : null}
      {submission ? (
        <ModerationDetail
          key={submission.id}
          submission={submission}
          pending={{
            claim: actions.claim.isPending,
            revision: actions.revision.isPending,
            reject: actions.reject.isPending,
            publish: actions.publish.isPending,
          }}
          errors={{
            claim: errorText(actions.claim.error),
            revision: errorText(actions.revision.error),
            reject: errorText(actions.reject.error),
            publish: errorText(actions.publish.error),
          }}
          onClaim={() =>
            actions.claim.mutateAsync({
              id: submission.id,
              input: { expectedVersion: submission.version },
            })
          }
          onRevision={(input) => actions.revision.mutateAsync(input)}
          onReject={(input) => actions.reject.mutateAsync(input)}
          onPublish={(input) => actions.publish.mutateAsync(input)}
        />
      ) : null}
    </aside>
  );
}

interface Props {
  port: ModerationPort;
  filters: ModerationFilters;
  selectedSubmissionId: string | null;
  onFiltersChange: (filters: ModerationFilters) => void;
  onSelectSubmission: (id: string) => void;
}

export function ModerationWorkspace({
  port,
  filters,
  selectedSubmissionId,
  onFiltersChange,
  onSelectSubmission,
}: Props) {
  const queue = useModerationQueue(port, filters);
  const detail = useModerationDetail(port, selectedSubmissionId);
  const actions = useModerationActions(port, selectedSubmissionId);
  return (
    <section className="mod-workspace" aria-labelledby="moderation-title">
      <header className="mod-header">
        <div>
          <p className="mod-eyebrow">Административный контур</p>
          <h1 id="moderation-title">Модерация исторических материалов</h1>
        </div>
        <p>
          Очередь ограничена 50 записями на страницу. Решения проверяют версию
          заявки.
        </p>
      </header>
      <ModerationFiltersForm filters={filters} onChange={onFiltersChange} />
      <div className="mod-layout">
        <QueuePane
          page={queue.data}
          pending={queue.isPending}
          error={queue.error}
          filters={filters}
          selectedId={selectedSubmissionId}
          onSelect={onSelectSubmission}
          onFiltersChange={onFiltersChange}
        />
        <ReviewPane
          submission={detail.data}
          pending={detail.isPending}
          error={detail.error}
          selectedId={selectedSubmissionId}
          actions={actions}
        />
      </div>
    </section>
  );
}
