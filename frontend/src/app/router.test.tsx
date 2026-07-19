import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, vi } from "vitest";

import { AppRouter } from "./router";

function renderRoute(path: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <AppRouter />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

it("routes an anonymous admin through backend login into the protected shell", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(apiResponse(401, false, null, "unauthorized"))
      .mockResolvedValueOnce(apiResponse(200, true, currentAccount))
      .mockResolvedValueOnce(apiResponse(200, true, adminAccount)),
  );
  const user = userEvent.setup();
  renderRoute("/admin/catalog/entities");

  expect(
    await screen.findByRole("heading", { name: "Вход в рабочее пространство" }),
  ).toBeVisible();
  await user.type(screen.getByLabelText("Пароль"), "long museum password");
  await user.click(screen.getByRole("button", { name: "Войти" }));

  expect(
    await screen.findByRole("heading", {
      name: "Каталог истории",
    }),
  ).toBeVisible();
  expect(
    screen.getByRole("navigation", { name: "Разделы администратора" }),
  ).toBeVisible();
});

it("shows a useful not-found route", () => {
  renderRoute("/missing-route");
  expect(
    screen.getByRole("heading", { name: "Страница не найдена" }),
  ).toBeVisible();
  expect(screen.getByRole("link", { name: "Открыть карту" })).toHaveAttribute(
    "href",
    "/",
  );
});

it("keeps an editor out of moderation while allowing the admin shell", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(apiResponse(401, false, null, "unauthorized"))
      .mockResolvedValueOnce(
        apiResponse(200, true, {
          ...currentAccount,
          email: "editor@museum.test",
        }),
      )
      .mockResolvedValueOnce(
        apiResponse(200, true, {
          ...adminAccount,
          email: "editor@museum.test",
          display_name: "Редактор",
          roles: ["editor"],
        }),
      ),
  );
  const user = userEvent.setup();
  renderRoute("/admin/submissions");

  const email = await screen.findByLabelText("Email");
  await user.clear(email);
  await user.type(email, "editor@museum.test");
  await user.type(screen.getByLabelText("Пароль"), "long museum password");
  await user.click(screen.getByRole("button", { name: "Войти" }));

  expect(
    await screen.findByRole("heading", { name: "Модерация недоступна" }),
  ).toBeVisible();
  expect(screen.getByText(/роль moderator или admin/)).toBeVisible();
});

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
      meta: { request_id: "router-test" },
    }),
    { status, headers: { "Content-Type": "application/json" } },
  );
}
