import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, vi } from "vitest";

import { explorationApi } from "../api/explorationApi";
import type { TimelineEventsViewModel } from "../api/timelineViewModels";
import { ExplorerTimeline } from "./ExplorerTimeline";

afterEach(() => {
  vi.restoreAllMocks();
});

it("renders real event periods and opens the selected published event", async () => {
  const onOpenEvent = vi.fn();
  const getTimeline = vi
    .spyOn(explorationApi, "getTimelineEvents")
    .mockResolvedValue(timelinePage());
  const user = userEvent.setup();
  renderTimeline({ onOpenEvent });

  const timeline = await screen.findByRole("list", {
    name: "Хронология событий",
  });
  expect(within(timeline).getAllByRole("listitem")).toHaveLength(5);
  ["1944", "1817–1864", "с 1785", "до 1799", "Дата не указана"].forEach(
    (period) => {
      expect(within(timeline).getByText(period)).toBeVisible();
    },
  );
  await user.click(
    within(timeline).getByRole("button", { name: "Депортация населения" }),
  );
  expect(onOpenEvent).toHaveBeenCalledWith(
    "51151ac6-98cc-57e4-9fb0-d1d1a959ec90",
  );
  expect(getTimeline).toHaveBeenCalledWith(
    expect.objectContaining({
      query: "депортация",
      periodFrom: 1900,
      periodTo: 2000,
    }),
    expect.any(AbortSignal),
  );
});

it("shows loading, empty and error outcomes with an accessible retry", async () => {
  const pending = new Promise<TimelineEventsViewModel>(() => undefined);
  const getTimeline = vi
    .spyOn(explorationApi, "getTimelineEvents")
    .mockReturnValueOnce(pending);
  const loading = renderTimeline();
  expect(screen.getByRole("status")).toHaveTextContent("Загружаем хронологию");
  loading.unmount();

  getTimeline.mockReset().mockResolvedValueOnce({
    items: [],
    meta: { limit: 100, offset: 0, total: 0 },
  });
  const empty = renderTimeline();
  expect(
    await screen.findByText("По выбранным фильтрам событий нет."),
  ).toBeVisible();
  empty.unmount();

  getTimeline
    .mockReset()
    .mockRejectedValueOnce(new Error("service unavailable"));
  renderTimeline();
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("Не удалось загрузить хронологию");
  expect(
    within(alert).getByText("Не удалось загрузить хронологию."),
  ).toBeVisible();
  expect(screen.getByRole("button", { name: "Повторить" })).toBeVisible();
});

it("does not request events when the active type filter excludes them", () => {
  const getTimeline = vi.spyOn(explorationApi, "getTimelineEvents");
  renderTimeline({ eventsEnabled: false });

  expect(screen.getByRole("status")).toHaveTextContent(
    "События скрыты выбранными типами объектов",
  );
  expect(getTimeline).not.toHaveBeenCalled();
});

function renderTimeline({
  eventsEnabled = true,
  onOpenEvent = vi.fn(),
}: {
  eventsEnabled?: boolean;
  onOpenEvent?: (id: string) => void;
} = {}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
  }
  return render(
    <ExplorerTimeline
      filters={{ query: "депортация", periodFrom: 1900, periodTo: 2000 }}
      eventsEnabled={eventsEnabled}
      onOpenEvent={onOpenEvent}
    />,
    { wrapper: Wrapper },
  );
}

function timelinePage(): TimelineEventsViewModel {
  const values = [
    [
      "51151ac6-98cc-57e4-9fb0-d1d1a959ec90",
      "Депортация населения",
      1944,
      1944,
    ],
    ["2503b706-f407-5d94-817f-2a068379b72d", "Кавказская война", 1817, 1864],
    ["9aa14194-0b24-5a01-ae36-07767e8b4717", "Сражение при Алдах", 1785, null],
    ["00000000-0000-4000-8000-000000000001", "Раннее событие", null, 1799],
    ["00000000-0000-4000-8000-000000000002", "Событие без даты", null, null],
  ] as const;
  return {
    items: values.map(([id, title, periodFrom, periodTo]) => ({
      id,
      title,
      shortDescription: `${title}: краткое описание`,
      periodFrom,
      periodTo,
      coordinates: null,
    })),
    meta: { limit: 100, offset: 0, total: values.length },
  };
}
