import type { components } from "@/shared/api/schema";

import {
  ModerationApplicationError,
  type ModerationErrorCode,
} from "../domain/errors";
import type { ModerationPort } from "./moderationPort";
import {
  moderationQueueParams,
  type PublishDto,
  type QueuePageDto,
  type SubmissionDto,
  toPublishCommand,
  toPublishResult,
  toQueuePage,
  toSubmission,
} from "./moderationApiMappers";

type ApiError = components["schemas"]["ApiError"];

interface Envelope<T> {
  ok?: boolean;
  data?: T | null;
  error?: ApiError | null;
}

const REQUEST_TIMEOUT_MS = 15_000;

function boundedSignal(signal: AbortSignal | null | undefined) {
  const timeout = AbortSignal.timeout(REQUEST_TIMEOUT_MS);
  return signal ? AbortSignal.any([signal, timeout]) : timeout;
}

const knownCodes = new Set<ModerationErrorCode>([
  "bad_request",
  "unauthorized",
  "forbidden",
  "not_found",
  "conflict",
  "invalid_transition",
  "idempotency_conflict",
  "source_required",
  "validation_error",
  "rate_limited",
  "internal_error",
  "service_unavailable",
]);

const messages: Record<ModerationErrorCode, string> = {
  bad_request: "Проверьте параметры запроса.",
  unauthorized: "Сессия завершилась. Войдите в рабочее пространство снова.",
  forbidden: "Недостаточно прав для операции модерации.",
  not_found: "Заявка не найдена или больше недоступна.",
  conflict: "Заявка была изменена. Обновите данные перед решением.",
  invalid_transition: "Текущий статус заявки не допускает это действие.",
  idempotency_conflict: "Ключ публикации уже использован с другим решением.",
  source_required: "Для публикации нужен проверенный источник.",
  validation_error: "Проверьте обязательные поля решения.",
  rate_limited: "Слишком много запросов. Повторите попытку позже.",
  internal_error: "Сервер вернул неожиданный ответ.",
  service_unavailable: "Сервис модерации временно недоступен.",
};

function statusCode(status: number): ModerationErrorCode {
  const codes: Partial<Record<number, ModerationErrorCode>> = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    503: "service_unavailable",
  };
  return codes[status] ?? "internal_error";
}

function applicationError(code: unknown, status: number) {
  const resolved =
    typeof code === "string" && knownCodes.has(code as ModerationErrorCode)
      ? (code as ModerationErrorCode)
      : statusCode(status);
  return new ModerationApplicationError(resolved, messages[resolved]);
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  let response: Response;
  try {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    response = await fetch(path, {
      ...init,
      credentials: "same-origin",
      headers,
      signal: boundedSignal(init.signal),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;
    throw applicationError("service_unavailable", 503);
  }
  let envelope: Envelope<T>;
  try {
    envelope = (await response.json()) as Envelope<T>;
  } catch {
    throw applicationError(null, response.status);
  }
  if (!response.ok || envelope.ok !== true) {
    throw applicationError(envelope.error?.code, response.status);
  }
  if (envelope.data == null) throw applicationError("internal_error", 500);
  return envelope.data;
}

function jsonRequest(body: object, signal: AbortSignal): RequestInit {
  return {
    method: "POST",
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

function submissionPath(id: string, suffix = "") {
  return `/api/v1/admin/submissions/${encodeURIComponent(id)}${suffix}`;
}

export const moderationApi: ModerationPort = {
  async getQueue(filters, signal) {
    const dto = await request<QueuePageDto>(
      `/api/v1/admin/submissions?${moderationQueueParams(filters)}`,
      { method: "GET", signal },
    );
    return toQueuePage(dto);
  },
  async getSubmission(id, signal) {
    const dto = await request<SubmissionDto>(submissionPath(id), {
      method: "GET",
      signal,
    });
    return toSubmission(dto);
  },
  async claimSubmission(id, input, signal) {
    const dto = await request<SubmissionDto>(
      submissionPath(id, "/claim"),
      jsonRequest({ expected_version: input.expectedVersion }, signal),
    );
    return toSubmission(dto);
  },
  async requestRevision(id, input, signal) {
    const dto = await request<SubmissionDto>(
      submissionPath(id, "/request-revision"),
      jsonRequest(
        { expected_version: input.expectedVersion, comment: input.comment },
        signal,
      ),
    );
    return toSubmission(dto);
  },
  async rejectSubmission(id, input, signal) {
    const dto = await request<SubmissionDto>(
      submissionPath(id, "/reject"),
      jsonRequest(
        { expected_version: input.expectedVersion, comment: input.comment },
        signal,
      ),
    );
    return toSubmission(dto);
  },
  async publishSubmission(id, input, signal) {
    const dto = await request<PublishDto>(
      submissionPath(id, "/publish"),
      jsonRequest(toPublishCommand(input), signal),
    );
    try {
      return toPublishResult(dto, input.action);
    } catch {
      throw applicationError("internal_error", 500);
    }
  },
};
