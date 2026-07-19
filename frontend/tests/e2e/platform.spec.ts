import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("history atlas supports the primary exploration workflow", async ({
  page,
}, testInfo) => {
  const blankTile = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
    "base64",
  );
  for (const tileHost of [
    "https://tile.openstreetmap.org/**",
    "https://server.arcgisonline.com/**",
  ]) {
    await page.route(tileHost, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "image/png",
        body: blankTile,
      });
    });
  }
  const apiRequests: string[] = [];
  const consoleErrors: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.startsWith("/api/")) {
      apiRequests.push(request.url());
    }
  });
  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });
  await page.goto("/");
  await expect(page.locator(".maplibregl-canvas")).toBeVisible();
  await page.getByLabel("Поиск по атласу").fill("Грозный");
  const searchResults = page.getByRole("list", { name: "Результаты поиска" });
  await expect(
    searchResults.getByRole("button", { name: /Грозный/ }).first(),
  ).toBeVisible({ timeout: 15_000 });
  await searchResults
    .getByRole("button", { name: /Грозный/ })
    .first()
    .click();
  await expect(page).toHaveURL(/modal=[0-9a-f-]{36}/);
  const entityDialog = page.getByRole("dialog");
  await expect(entityDialog).toBeVisible();
  await expect(
    entityDialog.getByRole("heading", { level: 2, name: "Грозный" }),
  ).toBeVisible();
  const selectedId = new URL(page.url()).searchParams.get("modal");
  expect(selectedId).toMatch(/^[0-9a-f-]{36}$/);
  const modalEdges = entityDialog.locator(".hx-network-edge");
  await expect(modalEdges.first()).toBeAttached({ timeout: 15_000 });
  expect(await modalEdges.count()).toBeGreaterThan(0);
  await expect(modalEdges.first()).not.toHaveCSS("stroke", "none");
  await page.keyboard.press("Escape");
  await page.goto(`/?view=network&entity=${selectedId ?? ""}`);
  await expect(
    page.getByRole("heading", { level: 2, name: /Паутина: Грозный/ }),
  ).toBeVisible({ timeout: 15_000 });
  if ((testInfo.project.use.viewport?.width ?? 0) >= 720) {
    await expect(page.locator(".hx-network-canvas")).toBeVisible();
  } else {
    await expect(
      page.getByRole("list", { name: "Связи объекта Грозный" }),
    ).toBeVisible();
  }
  await expect(page.getByText("Глубина связей: 2")).toBeVisible();
  await page.goto("/?view=timeline");
  const timeline = page.getByRole("list", { name: "Хронология событий" });
  await expect(timeline.getByRole("listitem").first()).toBeVisible();
  await timeline.getByRole("listitem").first().getByRole("button").click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(page).toHaveURL(/modal=[0-9a-f-]{36}/);
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(page).not.toHaveURL(/\/entities\//);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(apiRequests.some((url) => url.includes("/api/v1/map/entities"))).toBe(
    true,
  );
  expect(apiRequests.some((url) => url.includes("/api/v1/search"))).toBe(true);
  expect(
    apiRequests.some((url) => url.includes("/api/v1/timeline/events")),
  ).toBe(true);
  expect(apiRequests.some((url) => url.includes("/graph?depth=2"))).toBe(true);
  expect(apiRequests.some((url) => url.includes("10000000-"))).toBe(false);
  expect(consoleErrors).toEqual([]);
});

test("@a11y atlas remains accessible and fits the viewport", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations.filter(
      (item) => item.impact === "critical" || item.impact === "serious",
    ),
  ).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Подробнее" }).click();
  const entityResults = await new AxeBuilder({ page }).analyze();
  expect(
    entityResults.violations.filter(
      (item) => item.impact === "critical" || item.impact === "serious",
    ),
  ).toEqual([]);
});

test("exploration exposes recoverable API states", async ({ page }) => {
  await page.route("**/api/v1/map/entities?**", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        ok: false,
        data: null,
        error: {
          code: "service_unavailable",
          message: "Unavailable",
          details: null,
        },
        meta: { request_id: "e2e-map-error" },
      }),
    });
  });
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText(
    "Данные временно недоступны",
  );
});

test("admin route guards anonymous access without browser tokens", async ({
  page,
}) => {
  await page.goto("/admin/catalog/entities");
  await expect(
    page.getByRole("heading", { name: "Вход в редакцию" }),
  ).toBeVisible();
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(
    accessibility.violations.filter(
      (item) => item.impact === "critical" || item.impact === "serious",
    ),
  ).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(
    await page.evaluate(() => localStorage.length + sessionStorage.length),
  ).toBe(0);
});

test("@a11y contribution wizard protects private browser state", async ({
  page,
}) => {
  await page.goto("/contribute");
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Добавить материал",
    }),
  ).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations.filter(
      (item) => item.impact === "critical" || item.impact === "serious",
    ),
  ).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(
    await page.evaluate(() => localStorage.length + sessionStorage.length),
  ).toBe(0);
});

test("unknown route has a recovery action", async ({ page }) => {
  await page.goto("/unknown");
  await expect(
    page.getByRole("heading", { name: "Страница не найдена" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Открыть карту" }),
  ).toHaveAttribute("href", "/");
});
