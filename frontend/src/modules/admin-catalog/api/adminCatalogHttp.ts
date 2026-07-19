import type { components } from "@/shared/api/schema";

import { AdminCatalogError } from "../domain/catalog";

type ErrorDto = components["schemas"]["ApiError"];
interface Envelope<T> {
  ok?: boolean;
  data?: T | null;
  error?: ErrorDto | null;
}

const knownCodes = new Set<AdminCatalogError["code"]>([
  "bad_request",
  "unauthorized",
  "forbidden",
  "conflict",
  "not_found",
  "export_too_large",
  "source_required",
  "validation_error",
  "internal_error",
  "service_unavailable",
]);

function fallbackCode(status: number): AdminCatalogError["code"] {
  const codes: Partial<Record<number, AdminCatalogError["code"]>> = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    413: "export_too_large",
    422: "validation_error",
    503: "service_unavailable",
  };
  return codes[status] ?? "internal_error";
}

function apiError(code: unknown, status: number) {
  const resolved =
    typeof code === "string" &&
    knownCodes.has(code as AdminCatalogError["code"])
      ? (code as AdminCatalogError["code"])
      : fallbackCode(status);
  const messages: Record<AdminCatalogError["code"], string> = {
    bad_request: "Проверьте параметры каталога.",
    unauthorized: "Сессия завершилась. Войдите снова.",
    forbidden: "Недостаточно прав для этой операции.",
    conflict: "Запись уже изменена. Обновите каталог.",
    not_found: "Запись не найдена или недоступна.",
    export_too_large: "Экспорт превышает допустимый размер.",
    source_required: "Для публикации нужен проверенный источник.",
    validation_error: "Проверьте обязательные поля.",
    internal_error: "Сервер вернул неожиданный ответ.",
    service_unavailable: "Каталог временно недоступен.",
  };
  return new AdminCatalogError(resolved, messages[resolved]);
}

function boundedSignal(signal: AbortSignal | null | undefined) {
  const timeout = AbortSignal.timeout(60_000);
  return signal ? AbortSignal.any([signal, timeout]) : timeout;
}

export async function requestEnvelope<T>(
  path: string,
  init: RequestInit,
): Promise<T | null> {
  let response: Response;
  try {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    response = await fetch(path, {
      ...init,
      headers,
      credentials: "same-origin",
      signal: boundedSignal(init.signal),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;
    throw apiError("service_unavailable", 503);
  }
  let envelope: Envelope<T>;
  try {
    envelope = (await response.json()) as Envelope<T>;
  } catch {
    throw apiError(null, response.status);
  }
  if (!response.ok || envelope.ok !== true)
    throw apiError(envelope.error?.code, response.status);
  return envelope.data ?? null;
}

export async function request<T>(path: string, init: RequestInit): Promise<T> {
  const data = await requestEnvelope<T>(path, init);
  if (data == null) throw apiError("internal_error", 500);
  return data;
}

export function jsonInit(
  method: "POST" | "PATCH" | "DELETE",
  body: object,
  signal: AbortSignal,
) {
  return {
    method,
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  } satisfies RequestInit;
}

export async function requestExport(
  path: string,
  fallback: string,
  signal: AbortSignal,
) {
  const response = await fetchExport(path, signal);
  if (!response.ok) throw await exportError(response);
  return exportFile(response, fallback);
}

async function fetchExport(path: string, signal: AbortSignal) {
  try {
    return await fetch(path, {
      credentials: "same-origin",
      signal: boundedSignal(signal),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;
    throw apiError("service_unavailable", 503);
  }
}

async function exportError(response: Response) {
  if (!response.ok) {
    const envelope = (await response
      .json()
      .catch(() => null)) as Envelope<null> | null;
    return apiError(envelope?.error?.code, response.status);
  }
  return apiError("internal_error", response.status);
}

async function exportFile(response: Response, fallback: string) {
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition");
  const filename =
    disposition?.match(/filename="?([^";]+)"?/i)?.[1] ?? fallback;
  return {
    blob,
    filename,
    contentType: response.headers.get("Content-Type") ?? blob.type,
  };
}
