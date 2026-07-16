import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

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
  await expect(page.getByRole("button")).toHaveCount(10);

  await page.getByRole("button", { name: /Terminal/ }).click();
  await expect(page.locator("main")).toHaveAttribute("data-theme", "terminal");
  await expect(page).toHaveURL(/style=terminal/);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("@a11y platform shell has no serious accessibility violations", async ({
  page,
}) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations.filter(
      (item) => item.impact === "critical" || item.impact === "serious",
    ),
  ).toEqual([]);
});
