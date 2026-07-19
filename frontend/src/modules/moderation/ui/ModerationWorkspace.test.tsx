import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { vi } from "vitest";

import {
  createMockModerationPort,
  MODERATION_MOCK_IDS,
} from "../api/mockModerationPort";
import type { ModerationPort } from "../api/moderationPort";
import { defaultModerationFilters } from "../domain/filters";
import type { ModerationFilters } from "../domain/types";
import { ModerationWorkspace } from "./ModerationWorkspace";

const signal = new AbortController().signal;

function TestWorkspace({
  port,
  initialSelected = null,
  initialFilters = defaultModerationFilters,
}: {
  port: ModerationPort;
  initialSelected?: string | null;
  initialFilters?: ModerationFilters;
}) {
  const [filters, setFilters] = useState(initialFilters);
  const [selected, setSelected] = useState(initialSelected);
  return (
    <ModerationWorkspace
      port={port}
      filters={filters}
      selectedSubmissionId={selected}
      onFiltersChange={setFilters}
      onSelectSubmission={setSelected}
    />
  );
}

function renderWorkspace(
  port: ModerationPort,
  initialSelected?: string,
  initialFilters?: ModerationFilters,
) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <TestWorkspace
        port={port}
        initialSelected={initialSelected}
        initialFilters={initialFilters}
      />
    </QueryClientProvider>,
  );
}

function SwitchingWorkspace({
  port,
  firstId,
  secondId,
}: {
  port: ModerationPort;
  firstId: string;
  secondId: string;
}) {
  const [selected, setSelected] = useState(firstId);
  return (
    <>
      <button
        type="button"
        onClick={() => {
          setSelected(secondId);
        }}
      >
        Показать вторую заявку
      </button>
      <ModerationWorkspace
        port={port}
        filters={{ ...defaultModerationFilters, status: "in_review" }}
        selectedSubmissionId={selected}
        onFiltersChange={vi.fn()}
        onSelectSubmission={setSelected}
      />
    </>
  );
}

function decisionForm(name: string): HTMLFormElement {
  const heading = screen.getByRole("heading", { level: 3, name });
  const form = heading.closest("form");
  if (!(form instanceof HTMLFormElement))
    throw new Error("Decision form missing");
  return form;
}

it("filters the bounded queue, opens safe detail and provides the report-resolution flow", async () => {
  const user = userEvent.setup();
  const port = createMockModerationPort("publish");
  const { container } = renderWorkspace(port);

  await user.selectOptions(screen.getByLabelText("Тип заявки"), "report_error");
  expect(
    await screen.findAllByText("Неточность в дате основания"),
  ).not.toHaveLength(0);
  const openButtons = screen.getAllByRole("button", { name: "Открыть" });
  await user.click(openButtons[0]);
  expect(
    await screen.findByRole("heading", {
      level: 2,
      name: "Неточность в дате основания",
    }),
  ).toBeVisible();
  expect(screen.getByText("researcher@example.test")).toBeVisible();
  expect(screen.getByText("Архивная опись районного фонда")).toBeVisible();
  expect(screen.getByText(/<img src=x onerror=alert\(1\)>/)).toBeVisible();
  expect(container.querySelector("img")).toBeNull();
  expect(
    screen.getByText("Автор не приложил фотографии к этой заявке."),
  ).toBeVisible();

  await user.click(screen.getByRole("button", { name: "Взять в работу" }));
  expect(
    await screen.findByRole("heading", {
      name: "Разрешить сообщение об ошибке",
    }),
  ).toBeVisible();
});

it("shows media and publishes only the UUIDs selected with accessible checkboxes", async () => {
  const user = userEvent.setup();
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
  const port = createMockModerationPort("publish");
  const publish = vi.spyOn(port, "publishSubmission");
  renderWorkspace(port, MODERATION_MOCK_IDS.newEntityInReview, {
    ...defaultModerationFilters,
    status: "in_review",
  });

  expect(
    await screen.findByRole("img", { name: "Первый выпуск школы" }),
  ).toBeVisible();
  expect(screen.getByText("school-class.jpg")).toBeVisible();
  expect(screen.getByText("image/jpeg · 1.5 МБ")).toBeVisible();
  expect(screen.getByText("2048 × 1365")).toBeVisible();

  const firstPhoto = screen.getByRole("checkbox", {
    name: "Первый выпуск школы",
  });
  const secondPhoto = screen.getByRole("checkbox", {
    name: "Здание сельской школы",
  });
  expect(firstPhoto).not.toBeChecked();
  await user.click(firstPhoto);
  expect(firstPhoto).toBeChecked();
  await user.click(secondPhoto);
  expect(secondPhoto).toBeChecked();
  await user.click(secondPhoto);
  expect(secondPhoto).not.toBeChecked();

  await user.click(
    screen.getByRole("button", { name: "Опубликовать атомарно" }),
  );
  await waitFor(() => {
    expect(publish).toHaveBeenCalledOnce();
  });
  const command = publish.mock.calls[0][1];
  expect(command.action).toBe("create_entity");
  if (command.action !== "create_entity") throw new Error("Unexpected action");
  expect(command.payload.approvedMediaIds).toEqual([
    "51000000-0000-4000-8000-000000000002",
  ]);
  expect(confirm).toHaveBeenCalledOnce();
  confirm.mockRestore();
});

it("claims a pending item and requests a commented revision", async () => {
  const user = userEvent.setup();
  const port = createMockModerationPort("publish");
  renderWorkspace(port, MODERATION_MOCK_IDS.newEntityPending);

  await user.click(
    await screen.findByRole("button", { name: "Взять в работу" }),
  );
  await screen.findByRole("heading", { name: "Запросить исправления" });
  const form = decisionForm("Запросить исправления");
  await user.type(
    within(form).getByLabelText("Комментарий для автора"),
    "Добавьте архивный шифр",
  );
  await user.click(
    within(form).getByRole("button", { name: "Запросить исправления" }),
  );
  expect(await screen.findByText(/needs_revision · v3/)).toBeVisible();
});

it("keeps unsaved decision text when expected version is stale", async () => {
  const user = userEvent.setup();
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
  const port = createMockModerationPort("publish");
  renderWorkspace(port, MODERATION_MOCK_IDS.newEntityInReview, {
    ...defaultModerationFilters,
    status: "in_review",
  });
  await screen.findByRole("heading", { name: "Отклонить заявку" });
  const form = decisionForm("Отклонить заявку");
  const comment = within(form).getByLabelText("Комментарий для автора");
  await user.type(comment, "Источник невозможно подтвердить");

  await act(async () => {
    await port.requestRevision(
      MODERATION_MOCK_IDS.newEntityInReview,
      { expectedVersion: 3, comment: "Параллельное решение" },
      signal,
    );
  });
  await user.click(
    within(form).getByRole("button", { name: "Отклонить заявку" }),
  );
  expect(
    await screen.findByText(/Заявка изменилась в другой вкладке/),
  ).toBeVisible();
  expect(comment).toHaveValue("Источник невозможно подтвердить");
  expect(confirm).toHaveBeenCalledOnce();
  confirm.mockRestore();
});

it("does not carry form values or idempotency state into another submission", async () => {
  const user = userEvent.setup();
  const basePort = createMockModerationPort("publish");
  const first = await basePort.getSubmission(
    MODERATION_MOCK_IDS.newEntityInReview,
    signal,
  );
  const second = {
    ...first,
    id: "50000000-0000-4000-8000-000000000005",
    title: "История второй школы",
    media: [],
  };
  const port: ModerationPort = {
    ...basePort,
    getSubmission: (id, requestSignal) =>
      id === second.id
        ? Promise.resolve(second)
        : basePort.getSubmission(id, requestSignal),
  };
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <SwitchingWorkspace port={port} firstId={first.id} secondId={second.id} />
    </QueryClientProvider>,
  );

  const title = await screen.findByLabelText("Название");
  await user.clear(title);
  await user.type(title, "Несохранённый текст первой заявки");
  await user.click(
    screen.getByRole("button", { name: "Показать вторую заявку" }),
  );

  expect(
    await screen.findByRole("heading", {
      level: 2,
      name: "История второй школы",
    }),
  ).toBeVisible();
  expect(screen.getByLabelText("Название")).toHaveValue("История второй школы");
});
