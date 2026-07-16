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
  await expect(page.locator(".status-card")).toContainText(
    "Все базовые сервисы доступны",
  );
  await expect(page.locator(".style-option")).toHaveCount(20);

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
  const styleOptions = page.locator(".style-option");

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

test("registration restores the server session and logout clears it", async ({
  page,
}, testInfo) => {
  const email = `e2e-${testInfo.project.name}-${String(Date.now())}@example.com`;
  await page.goto("/");
  await page.getByRole("button", { name: "Войти" }).click();
  const dialog = page.getByRole("dialog");
  const accessibility = await new AxeBuilder({ page })
    .include(".auth-dialog")
    .analyze();
  expect(
    accessibility.violations.filter(
      (item) => item.impact === "critical" || item.impact === "serious",
    ),
  ).toEqual([]);
  await dialog.getByRole("tab", { name: "Регистрация" }).click();
  await dialog.getByLabel("Email").fill(email);
  await dialog.getByLabel("Пароль").fill("long e2e user password");
  await dialog.getByRole("button", { name: "Зарегистрироваться" }).click();

  await expect(page.getByText(email)).toBeVisible();
  await page.reload();
  await expect(page.getByText(email)).toBeVisible();
  const sessionCookie = (await page.context().cookies()).find(
    (cookie) => cookie.name === "__Host-product_session",
  );
  expect(sessionCookie).toBeDefined();
  const rejected = await page.request.post("/api/auth/logout", {
    headers: {
      Cookie: `${sessionCookie?.name ?? ""}=${sessionCookie?.value ?? ""}`,
      Origin: "https://evil.example",
    },
  });
  expect(rejected.status()).toBe(403);
  await page.reload();
  await expect(page.getByText(email)).toBeVisible();
  await page.getByRole("button", { name: "Выйти" }).click();
  await expect(page.getByRole("button", { name: "Войти" })).toBeVisible();
});

test("login abuse is bounded and publishes retry timing", async ({
  request,
}, testInfo) => {
  test.skip(
    testInfo.project.name !== "desktop-chromium",
    "One shared Redis scenario is enough",
  );
  const credentials = {
    email: `limited-${String(Date.now())}@example.com`,
    password: "long invalid password",
  };
  for (let attempt = 0; attempt < 5; attempt += 1) {
    const response = await request.post("/api/auth/login", {
      data: credentials,
    });
    expect(response.status()).toBe(401);
  }

  const limited = await request.post("/api/auth/login", { data: credentials });
  expect(limited.status()).toBe(429);
  expect(Number(limited.headers()["retry-after"])).toBeGreaterThan(0);
});
