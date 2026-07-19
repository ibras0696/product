import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, vi } from "vitest";

import { AdminLoginPage } from "./AdminLoginPage";
import { ProtectedAdminShell } from "./ProtectedAdminShell";

const currentAccount = {
  id: "cbf0a5fb-196b-43ac-bb6f-d143d5e0d5d8",
  email: "admin@museum.test",
  status: "active",
} as const;

const adminAccount = {
  ...currentAccount,
  display_name: "Главный редактор",
  roles: ["admin"],
} as const;

afterEach(() => {
  vi.unstubAllGlobals();
});

it("logs in through the real cookie-session endpoints and restores the requested admin route", async () => {
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValueOnce(apiResponse(200, true, currentAccount))
    .mockResolvedValueOnce(apiResponse(200, true, adminAccount));
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();

  renderLogin("/admin/login?returnTo=/admin/catalog/entities");
  expect(screen.getByText("Вход в редакцию", { selector: "h1" })).toBeVisible();
  expect(screen.getByLabelText("Электронная почта")).toHaveAttribute(
    "autocomplete",
    "username",
  );
  expect(screen.getByLabelText("Электронная почта")).toHaveValue("");
  expect(screen.getByLabelText("Пароль")).toHaveAttribute(
    "autocomplete",
    "current-password",
  );
  await user.type(
    screen.getByLabelText("Электронная почта"),
    currentAccount.email,
  );
  await user.type(screen.getByLabelText("Пароль"), "long museum password");
  await user.click(screen.getByRole("button", { name: "Войти" }));

  expect(
    await screen.findByRole("heading", { name: "Каталог истории" }),
  ).toBeVisible();
  expect(fetchMock).toHaveBeenNthCalledWith(
    1,
    "/api/v1/auth/login",
    expect.objectContaining({
      method: "POST",
      credentials: "same-origin",
      body: JSON.stringify({
        email: currentAccount.email,
        password: "long museum password",
      }),
    }),
  );
  expect(fetchMock).toHaveBeenNthCalledWith(
    2,
    "/api/v1/admin/me",
    expect.objectContaining({
      credentials: "same-origin",
    }),
  );
});

it("shows stable backend authentication and authorization failures", async () => {
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValueOnce(apiResponse(401, false, null, "invalid_credentials"))
    .mockResolvedValueOnce(apiResponse(200, true, currentAccount))
    .mockResolvedValueOnce(apiResponse(403, false, null, "forbidden"));
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();

  renderLogin("/admin/login");
  await user.type(
    screen.getByLabelText("Электронная почта"),
    currentAccount.email,
  );
  await user.type(screen.getByLabelText("Пароль"), "long museum password");
  await user.click(screen.getByRole("button", { name: "Войти" }));
  expect(await screen.findByText("Неверный email или пароль")).toBeVisible();
  expect(screen.getByLabelText("Пароль")).toHaveValue("");

  await user.type(screen.getByLabelText("Пароль"), "long museum password");
  await user.click(screen.getByRole("button", { name: "Войти" }));
  expect(
    await screen.findByText("У аккаунта нет доступа к рабочему пространству"),
  ).toBeVisible();
});

it("restores an admin session and logs out through the backend before redirecting", async () => {
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValueOnce(apiResponse(200, true, adminAccount))
    .mockResolvedValueOnce(apiResponse(200, true, null));
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();

  renderProtectedRoute();
  expect(await screen.findByText("Главный редактор")).toBeVisible();
  expect(screen.getByText("Администратор")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Выйти" }));

  expect(
    await screen.findByRole("heading", { name: "Требуется вход" }),
  ).toBeVisible();
  expect(fetchMock).toHaveBeenNthCalledWith(
    2,
    "/api/v1/auth/logout",
    expect.objectContaining({ method: "POST", credentials: "same-origin" }),
  );
});

it("distinguishes an authenticated account without an admin role from an anonymous session", async () => {
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValueOnce(apiResponse(403, false, null, "forbidden"))
    .mockResolvedValueOnce(apiResponse(200, true, null));
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();

  renderProtectedRoute();
  expect(
    await screen.findByRole("heading", { name: "Нет доступа" }),
  ).toBeVisible();
  expect(
    screen.getByText("У текущего аккаунта нет административной роли."),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Выйти" }));
  expect(
    await screen.findByRole("heading", { name: "Требуется вход" }),
  ).toBeVisible();
});

function renderLogin(initialEntry: string) {
  renderWithProviders(
    initialEntry,
    <Routes>
      <Route path="/admin/login" element={<AdminLoginPage />} />
      <Route
        path="/admin/catalog/entities"
        element={<h1>Каталог истории</h1>}
      />
      <Route path="/admin" element={<h1>Рабочее пространство</h1>} />
    </Routes>,
  );
}

function renderProtectedRoute() {
  renderWithProviders(
    "/admin",
    <Routes>
      <Route path="/admin/login" element={<h1>Требуется вход</h1>} />
      <Route path="/admin" element={<ProtectedAdminShell />}>
        <Route index element={<p>Рабочее пространство</p>} />
      </Route>
    </Routes>,
  );
}

function renderWithProviders(initialEntry: string, routes: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>{routes}</MemoryRouter>
    </QueryClientProvider>,
  );
}

function apiResponse(
  status: number,
  ok: boolean,
  data: unknown,
  code?: string,
): Response {
  return new Response(
    JSON.stringify({
      ok,
      data,
      error: code ? { code, message: "Safe backend message" } : null,
      meta: { request_id: "admin-session-test" },
    }),
    { status, headers: { "Content-Type": "application/json" } },
  );
}
