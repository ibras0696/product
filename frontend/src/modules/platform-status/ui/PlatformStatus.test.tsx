import { render, screen } from "@testing-library/react";

import { PlatformStatus } from "./PlatformStatus";

it("loads platform readiness and reports a usable success state", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          ok: true,
          data: {
            status: "ready",
            components: [{ name: "postgres", healthy: true }],
          },
          error: null,
          meta: { request_id: "test-request" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    ),
  );

  render(<PlatformStatus />);

  expect(screen.getByRole("status")).toHaveTextContent("Проверяем сервисы");
  expect(await screen.findByText("Все базовые сервисы доступны")).toBeVisible();
});
