import type { components, paths } from "@/shared/api/schema";

import { AuthApiError } from "./errors";

export type CurrentAccount = components["schemas"]["CurrentAccount"];
export type Credentials = components["schemas"]["CredentialsRequest"];
type LoginResponse =
  paths["/api/v1/auth/login"]["post"]["responses"]["200"]["content"]["application/json"];
type RegisterResponse =
  paths["/api/v1/auth/register"]["post"]["responses"]["201"]["content"]["application/json"];
type MeResponse =
  paths["/api/v1/auth/me"]["get"]["responses"]["200"]["content"]["application/json"];

export async function getCurrentAccount(): Promise<CurrentAccount | null> {
  const response = await fetch("/api/v1/auth/me", {
    credentials: "same-origin",
  });
  if (response.status === 401) return null;
  const payload = (await parseResponse(response)) as MeResponse;
  return requireData(payload, response.status);
}

export async function login(credentials: Credentials): Promise<CurrentAccount> {
  const response = await post("/api/v1/auth/login", credentials);
  const payload = (await parseResponse(response)) as LoginResponse;
  return requireData(payload, response.status);
}

export async function register(
  credentials: Credentials,
): Promise<CurrentAccount> {
  const response = await post("/api/v1/auth/register", credentials);
  const payload = (await parseResponse(response)) as RegisterResponse;
  return requireData(payload, response.status);
}

export async function logout(): Promise<void> {
  const response = await post("/api/v1/auth/logout");
  await parseResponse(response);
}

async function post(path: string, body?: Credentials): Promise<Response> {
  return fetch(path, {
    method: "POST",
    credentials: "same-origin",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
}

async function parseResponse(response: Response): Promise<{
  ok: boolean;
  data?: unknown;
  error?: { code?: string; message?: string } | null;
}> {
  const payload = (await response.json()) as {
    ok: boolean;
    data?: unknown;
    error?: { code?: string; message?: string } | null;
  };
  if (!response.ok || !payload.ok) {
    throw new AuthApiError(
      payload.error?.code ?? "unknown_error",
      payload.error?.message ?? "Не удалось выполнить запрос",
      response.status,
    );
  }
  return payload;
}

function requireData(
  payload: { data?: CurrentAccount | null },
  status: number,
): CurrentAccount {
  if (!payload.data) {
    throw new AuthApiError(
      "invalid_response",
      "Сервер вернул неполный ответ",
      status,
    );
  }
  return payload.data;
}
