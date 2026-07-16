import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AuthControls } from "./AuthControls";

const account = {
  id: "cbf0a5fb-196b-43ac-bb6f-d143d5e0d5d8",
  email: "person@example.com",
  status: "active",
} as const;

it("moves through anonymous, failed login, authenticated, and logout states", async () => {
  let loginAttempts = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const path =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.href
            : input.url;
      if (path.endsWith("/me"))
        return apiResponse(401, false, null, "unauthorized");
      if (path.endsWith("/login")) {
        loginAttempts += 1;
        return loginAttempts === 1
          ? apiResponse(401, false, null, "invalid_credentials")
          : apiResponse(200, true, account);
      }
      if (path.endsWith("/logout")) return apiResponse(200, true, null);
      throw new Error(`Unexpected request: ${path}`);
    }),
  );
  const user = userEvent.setup();
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <AuthControls />
    </QueryClientProvider>,
  );

  await user.click(await screen.findByRole("button", { name: "Войти" }));
  const dialog = within(screen.getByRole("dialog"));
  await user.type(dialog.getByLabelText("Email"), account.email);
  await user.type(dialog.getByLabelText("Пароль"), "long user password");
  await user.click(dialog.getByRole("button", { name: "Войти" }));
  expect(await screen.findByText("Неверный email или пароль")).toBeVisible();

  await user.click(dialog.getByRole("button", { name: "Войти" }));
  expect(await screen.findByText(account.email)).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Выйти" }));
  expect(await screen.findByRole("button", { name: "Войти" })).toBeVisible();
});

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
      error: code ? { code, message: "Authentication failed" } : null,
      meta: { request_id: "test-request" },
    }),
    { status, headers: { "Content-Type": "application/json" } },
  );
}
