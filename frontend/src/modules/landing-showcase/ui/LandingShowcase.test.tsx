import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { LandingShowcase } from "./LandingShowcase";

beforeEach(() => {
  window.history.replaceState({}, "", "/");
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          ok: true,
          data: { status: "ready", components: [] },
          error: null,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    ),
  );
});

it("switches the complete landing design while preserving usable content", async () => {
  const user = userEvent.setup();
  render(<LandingShowcase />);

  expect(screen.getAllByRole("button")).toHaveLength(10);
  expect(screen.getByRole("button", { name: /Signal/ })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(
    screen.getByRole("heading", {
      name: "Из идеи в работающий продукт за один спринт.",
    }),
  ).toBeVisible();

  await user.click(screen.getByRole("button", { name: /Glass/ }));

  expect(screen.getByRole("button", { name: /Glass/ })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(document.querySelector("main")).toHaveAttribute("data-theme", "glass");
  expect(window.location.search).toBe("?style=glass");
  expect(await screen.findByText("Все базовые сервисы доступны")).toBeVisible();
});
