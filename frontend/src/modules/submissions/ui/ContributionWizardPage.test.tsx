import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { createMockSubmissionsPort } from "../api/createMockSubmissionsPort";
import { ContributionWizardPage } from "./ContributionWizardPage";

const settlements = [
  { id: "10000000-0000-4000-8000-000000000001", title: "Грозный" },
];
const entities = [
  {
    id: "20000000-0000-4000-8000-000000000002",
    title: "Старинная башня",
  },
];

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  const port = createMockSubmissionsPort();
  const createSubmission = vi.spyOn(port, "createSubmission");
  render(
    <QueryClientProvider client={queryClient}>
      <ContributionWizardPage
        port={port}
        entities={entities}
        settlements={settlements}
      />
    </QueryClientProvider>,
  );
  return { createSubmission };
}

it("keeps one relation draft consistent from type selection through submit", async () => {
  const user = userEvent.setup();
  const { createSubmission } = renderPage();

  await user.click(screen.getByRole("radio", { name: /Новая связь/i }));
  await user.click(screen.getByRole("button", { name: "Продолжить" }));
  await user.selectOptions(
    screen.getByLabelText("Связанный объект"),
    entities[0].id,
  );
  await user.selectOptions(
    screen.getByLabelText("Населённый пункт"),
    settlements[0].id,
  );
  await user.click(screen.getByRole("button", { name: "Продолжить" }));
  await user.click(screen.getByRole("button", { name: "Продолжить" }));
  expect(screen.getAllByText("Укажите заголовок")).toHaveLength(2);

  await user.type(
    screen.getByRole("textbox", { name: /Название связи/ }),
    "Семейная хроника",
  );
  await user.type(
    screen.getByRole("textbox", { name: /^Описание/ }),
    "История семьи и аула",
  );
  await user.type(
    screen.getByRole("textbox", { name: /Откуда взялись сведения/ }),
    "Домашний архив",
  );
  await user.click(screen.getByRole("button", { name: "Продолжить" }));
  await user.type(screen.getByLabelText("Как к вам обращаться"), "Муса");
  await user.type(
    screen.getByLabelText("Телефон, почта или другой способ связи"),
    "musa@example.test",
  );
  await user.click(screen.getByRole("checkbox"));
  await user.click(screen.getByRole("button", { name: "Продолжить" }));

  expect(
    await screen.findByRole("heading", { name: "Фотографии" }),
  ).toBeVisible();

  for (let index = 0; index < 4; index += 1) {
    await user.click(screen.getByRole("button", { name: "Назад" }));
  }
  expect(
    screen.getByRole("heading", { name: "Тип заявки сохранён" }),
  ).toBeVisible();
  expect(screen.queryByRole("radio")).not.toBeInTheDocument();

  for (let index = 0; index < 4; index += 1) {
    await user.click(screen.getByRole("button", { name: "Продолжить" }));
  }
  await user.click(screen.getByRole("button", { name: "Продолжить" }));
  expect(screen.getByText("Семейная хроника")).toBeVisible();
  expect(screen.getByText("Можно отправлять")).toBeVisible();
  await user.click(
    screen.getByRole("button", { name: "Отправить в редакцию" }),
  );

  expect(
    await screen.findByRole("heading", { name: "Спасибо за вклад в историю" }),
  ).toBeVisible();
  expect(screen.getByText(/^tracking_/)).toBeVisible();
  expect(createSubmission).toHaveBeenCalledTimes(1);
  expect(createSubmission.mock.calls[0][0]).toMatchObject({
    type: "new_relation",
    relatedEntityId: entities[0].id,
    settlementId: settlements[0].id,
  });
});
