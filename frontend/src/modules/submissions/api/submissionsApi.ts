import type { components } from "@/shared/api/schema";

import {
  SubmissionApplicationError,
  type SubmissionErrorCode,
} from "../domain/errors";
import type { SubmissionsPort } from "./submissionsPort";
import {
  toCreateDto,
  toDraft,
  toMedia,
  toMediaPatch,
  toPatchDto,
  toStatus,
  uploadForm,
} from "./submissionsApiMappers";

type ApiError = components["schemas"]["ApiError"];
type SubmissionSubmit = components["schemas"]["SubmissionSubmit"];
type StatusRequest = components["schemas"]["SubmissionStatusRequest"];
type DraftDto = components["schemas"]["SubmissionDraft"];
type StatusDto = components["schemas"]["SubmissionStatusView"];
type MediaDto = components["schemas"]["SubmissionMedia"];

interface Envelope<T> {
  ok?: boolean;
  data?: T | null;
  error?: ApiError | null;
}

const REQUEST_TIMEOUT_MS = 60_000;

function boundedSignal(signal: AbortSignal | null | undefined) {
  const timeout = AbortSignal.timeout(REQUEST_TIMEOUT_MS);
  return signal ? AbortSignal.any([signal, timeout]) : timeout;
}

const errorCodes = new Set<SubmissionErrorCode>([
  "bad_request",
  "unauthorized",
  "forbidden",
  "not_found",
  "conflict",
  "payload_too_large",
  "unsupported_media_type",
  "validation_error",
  "rate_limited",
  "internal_error",
  "service_unavailable",
  "source_required",
  "draft_not_editable",
  "invalid_transition",
  "media_rejected",
  "idempotency_conflict",
]);

const errorMessages: Record<SubmissionErrorCode, string> = {
  bad_request: "Проверьте данные заявки.",
  unauthorized: "Сессия недоступна. Обновите страницу и повторите попытку.",
  forbidden: "Операция недоступна для этого черновика.",
  not_found: "Заявка не найдена или недоступна.",
  conflict: "Черновик изменился. Обновите страницу перед повторной отправкой.",
  payload_too_large: "Файл превышает допустимый размер.",
  unsupported_media_type: "Формат файла не поддерживается.",
  validation_error: "Проверьте заполненные поля.",
  rate_limited: "Слишком много попыток. Попробуйте позже.",
  internal_error: "Сервер вернул неожиданный ответ.",
  service_unavailable: "Сервис временно недоступен. Повторите попытку.",
  source_required: "Укажите источник материала.",
  draft_not_editable: "Заявка уже недоступна для изменений.",
  invalid_transition: "Текущий статус заявки не допускает эту операцию.",
  media_rejected: "Файл или его описание отклонены.",
  idempotency_conflict: "Повторная загрузка не совпадает с исходным файлом.",
};

function statusErrorCode(status: number): SubmissionErrorCode {
  const codes: Partial<Record<number, SubmissionErrorCode>> = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "rate_limited",
    503: "service_unavailable",
  };
  return codes[status] ?? "internal_error";
}

function applicationError(code: unknown, status: number) {
  const resolved =
    typeof code === "string" && errorCodes.has(code as SubmissionErrorCode)
      ? (code as SubmissionErrorCode)
      : statusErrorCode(status);
  return new SubmissionApplicationError(resolved, errorMessages[resolved]);
}

async function fetchSameOrigin(path: string, init: RequestInit) {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  try {
    return await fetch(path, {
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
}

async function readEnvelope<T>(response: Response): Promise<Envelope<T>> {
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw applicationError(null, response.status);
  }
  if (payload == null || typeof payload !== "object") {
    throw applicationError("internal_error", 500);
  }
  return payload;
}

async function request<T>(
  path: string,
  init: RequestInit,
  allowNull = false,
): Promise<T> {
  const response = await fetchSameOrigin(path, init);
  const envelope = await readEnvelope<T>(response);
  if (!response.ok || envelope.ok !== true) {
    throw applicationError(envelope.error?.code, response.status);
  }
  if (!("data" in envelope) || (envelope.data === null && !allowNull)) {
    throw applicationError("internal_error", 500);
  }
  return envelope.data as T;
}

function jsonRequest(
  body: object,
  method: "POST" | "PATCH",
  signal: AbortSignal,
) {
  return {
    method,
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  } satisfies RequestInit;
}

function submissionPath(submissionId: string, suffix = "") {
  return `/api/v1/submissions/${encodeURIComponent(submissionId)}${suffix}`;
}

export const submissionsApi: SubmissionsPort = {
  async createSubmission(input, signal) {
    const dto = await request<DraftDto>(
      "/api/v1/submissions",
      jsonRequest(toCreateDto(input), "POST", signal),
    );
    return toDraft(dto);
  },
  async patchSubmission(id, expectedVersion, patch, signal) {
    const dto = await request<DraftDto>(
      submissionPath(id),
      jsonRequest(toPatchDto(expectedVersion, patch), "PATCH", signal),
    );
    return toDraft(dto);
  },
  async submitSubmission(id, expectedVersion, signal) {
    const body: SubmissionSubmit = { expected_version: expectedVersion };
    const dto = await request<StatusDto>(
      submissionPath(id, "/submit"),
      jsonRequest(body, "POST", signal),
    );
    return toStatus(dto);
  },
  async getSubmissionStatus(trackingCode, signal) {
    const body: StatusRequest = { tracking_code: trackingCode };
    const dto = await request<StatusDto>(
      "/api/v1/submissions/status",
      jsonRequest(body, "POST", signal),
    );
    return toStatus(dto);
  },
  async uploadSubmissionMedia(id, input, idempotencyKey, signal) {
    const dto = await request<MediaDto>(submissionPath(id, "/media"), {
      method: "POST",
      signal,
      headers: { "Idempotency-Key": idempotencyKey },
      body: uploadForm(input),
    });
    return toMedia(dto);
  },
  async getSubmissionMedia(id, signal) {
    const items = await request<MediaDto[]>(submissionPath(id, "/media"), {
      method: "GET",
      signal,
    });
    return items.map(toMedia);
  },
  async patchSubmissionMedia(id, mediaId, patch, signal) {
    const dto = await request<MediaDto>(
      submissionPath(id, `/media/${encodeURIComponent(mediaId)}`),
      jsonRequest(toMediaPatch(patch), "PATCH", signal),
    );
    return toMedia(dto);
  },
  async deleteSubmissionMedia(id, mediaId, signal) {
    await request<null>(
      submissionPath(id, `/media/${encodeURIComponent(mediaId)}`),
      { method: "DELETE", signal },
      true,
    );
    return null;
  },
};
