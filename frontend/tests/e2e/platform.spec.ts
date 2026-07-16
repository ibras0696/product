import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health/ready", async (route) => {
    await route.fulfill({
      json: {
        ok: true,
        data: { status: "ready", components: [] },
        error: null,
      },
    });
  });
});

test("landing showcase switches designs on the configured viewport", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: "Из идеи в работающий продукт за один спринт.",
    }),
  ).toBeVisible();
  await expect(page.getByRole("status")).toContainText(
    "Все базовые сервисы доступны",
  );
  await expect(page.getByRole("button")).toHaveCount(20);

  await page.getByRole("button", { name: /Terminal/ }).click();
  await expect(page.locator("main")).toHaveAttribute("data-theme", "terminal");
  await expect(page).toHaveURL(/style=terminal/);

  await page.getByRole("button", { name: /Chrome/ }).click();
  await expect(page.locator("main")).toHaveAttribute("data-theme", "chrome");
  await expect(page).toHaveURL(/style=chrome/);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("@a11y all new themes remain accessible and fit the viewport", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const styleOptions = page.getByRole("button");

  for (let index = 10; index < 20; index += 1) {
    const option = styleOptions.nth(index);
    const theme = (await option.textContent()) ?? `theme ${String(index + 1)}`;
    await option.click();

    const results = await new AxeBuilder({ page }).analyze();
    expect(
      results.violations.filter(
        (item) => item.impact === "critical" || item.impact === "serious",
      ),
      theme,
    ).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      theme,
    ).toBe(true);
  }
});
