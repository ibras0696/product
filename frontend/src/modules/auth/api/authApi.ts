import type { components, paths } from "@/shared/api/schema";

import { AuthApiError } from "./errors";

export type CurrentAccount = components["schemas"]["CurrentAccount"];
export type Credentials = components["schemas"]["CredentialsRequest"];
export type AdminRole = components["schemas"]["RoleName"];
export interface AdminAccount {
  id: string;
  email: string;
  status: "active";
  displayName: string;
  roles: AdminRole[];
}
type LoginResponse =
  paths["/api/v1/auth/login"]["post"]["responses"]["200"]["content"]["application/json"];
type RegisterResponse =
  paths["/api/v1/auth/register"]["post"]["responses"]["201"]["content"]["application/json"];
type MeResponse =
  paths["/api/v1/auth/me"]["get"]["responses"]["200"]["content"]["application/json"];
type AdminMeResponse =
  paths["/api/v1/admin/me"]["get"]["responses"]["200"]["content"]["application/json"];

const REQUEST_TIMEOUT_MS = 15_000;

export async function getCurrentAccount(): Promise<CurrentAccount | null> {
  const response = await fetch("/api/v1/auth/me", {
    credentials: "same-origin",
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });
  if (response.status === 401) return null;
  const payload = await parseResponse<MeResponse>(response);
  return requireData(payload, response.status);
}

export async function getAdminAccount(): Promise<AdminAccount | null> {
  const response = await fetch("/api/v1/admin/me", {
    credentials: "same-origin",
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });
  if (response.status === 401) return null;
  const payload = await parseResponse<AdminMeResponse>(response);
  const account = requireData(payload, response.status);
  return {
    id: account.id,
    email: account.email,
    status: account.status,
    displayName: account.display_name.trim() || account.email,
    roles: account.roles,
  };
}

export async function login(credentials: Credentials): Promise<CurrentAccount> {
  const response = await post("/api/v1/auth/login", credentials);
  const payload = await parseResponse<LoginResponse>(response);
  return requireData(payload, response.status);
}

export async function loginAdmin(
  credentials: Credentials,
): Promise<AdminAccount> {
  await login(credentials);
  const account = await getAdminAccount();
  if (!account) {
    throw new AuthApiError(
      "invalid_response",
      "Сервер не подтвердил административную сессию",
      401,
    );
  }
  return account;
}

export async function register(
  credentials: Credentials,
): Promise<CurrentAccount> {
  const response = await post("/api/v1/auth/register", credentials);
  const payload = await parseResponse<RegisterResponse>(response);
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
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });
}

async function parseResponse<T extends ApiEnvelope>(
  response: Response,
): Promise<T> {
  const payload = (await response.json()) as T;
  if (!response.ok || !payload.ok) {
    throw new AuthApiError(
      payload.error?.code ?? "unknown_error",
      payload.error?.message ?? "Не удалось выполнить запрос",
      response.status,
    );
  }
  return payload;
}

type ApiEnvelope = {
  ok: boolean;
  data?: unknown;
  error?: { code?: string; message?: string } | null;
};

function requireData<T>(payload: { data?: T | null }, status: number): T {
  if (!payload.data) {
    throw new AuthApiError(
      "invalid_response",
      "Сервер вернул неполный ответ",
      status,
    );
  }
  return payload.data;
}
