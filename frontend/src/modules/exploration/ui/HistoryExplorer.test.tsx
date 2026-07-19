import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, beforeEach, vi } from "vitest";

import { explorationApi } from "../api/explorationApi";
import { districtIds, mockMapEntities } from "../api/mockCatalogData";
import { mockExplorationApi } from "../api/mockExplorationApi";
import { entityIds } from "../model/entityIds";
import { HistoryExplorer } from "./HistoryExplorer";

const edgeIds = {
  groznyShali: "30000000-0000-4000-8000-000000000001",
  shaliArgun: "30000000-0000-4000-8000-000000000002",
};

beforeEach(() => {
  vi.spyOn(explorationApi, "getMapEntities").mockImplementation(
    (filters, signal) => mockExplorationApi.getMapEntities(filters, signal),
  );
  vi.spyOn(explorationApi, "getCatalogOptions").mockImplementation((signal) =>
    mockExplorationApi.getCatalogOptions(signal),
  );
  vi.spyOn(explorationApi, "search").mockImplementation((filters, signal) =>
    mockExplorationApi.search(filters, signal),
  );
  vi.spyOn(explorationApi, "getTimelineEvents").mockResolvedValue({
    items: [
      {
        id: entityIds.publicEducation,
        title: "Народное образование",
        shortDescription: "История развития образования",
        periodFrom: 1920,
        periodTo: 1930,
        coordinates: null,
      },
    ],
    meta: { limit: 100, offset: 0, total: 1 },
  });
  vi.spyOn(explorationApi, "getEntity").mockImplementation((id) =>
    Promise.resolve(entityDetails(id)),
  );
  vi.spyOn(explorationApi, "getGraph").mockImplementation((id) =>
    Promise.resolve(entityGraph(id)),
  );
  vi.spyOn(explorationApi, "getEntitySources").mockResolvedValue(emptyPage());
  vi.spyOn(explorationApi, "getRelationSources").mockResolvedValue({
    items: [
      {
        id: "40000000-0000-4000-8000-000000000001",
        title: "Архивный источник",
        type: "archive_document",
        author: null,
        publisher: null,
        publication_year: null,
        url: null,
        archive_reference: "Фонд 1, дело 2",
        description: "Подтверждение исторической связи",
        is_verified: true,
      },
    ],
    meta: { limit: 20, offset: 0, total: 1 },
  });
  vi.spyOn(explorationApi, "getEntityMedia").mockResolvedValue(emptyPage());
});

afterEach(() => {
  vi.restoreAllMocks();
});

function LocationProbe() {
  const location = useLocation();
  return (
    <output aria-label="Текущий адрес">
      {location.pathname}
      {location.search}
    </output>
  );
}

function renderExplorer(initialEntry = "/") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <HistoryExplorer />
        <LocationProbe />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

it("keeps timeline filters in the URL and forwards their catalog values", async () => {
  const getTimeline = vi.spyOn(explorationApi, "getTimelineEvents");
  renderExplorer(
    `/?view=timeline&q=образование&types=event&district=${districtIds.central}&period=1917-1990`,
  );

  await waitFor(() => {
    expect(screen.getByText("1920–1930")).toBeVisible();
    expect(getTimeline).toHaveBeenLastCalledWith(
      expect.objectContaining({
        query: "образование",
        districtId: districtIds.central,
        periodFrom: 1917,
        periodTo: 1990,
      }),
      expect.any(AbortSignal),
    );
  });
  const address = screen.getByLabelText("Текущий адрес");
  expect(address).toHaveTextContent("view=timeline");
  expect(address).toHaveTextContent("types=event");
  expect(address).toHaveTextContent(`district=${districtIds.central}`);
  expect(address).toHaveTextContent("period=1917-1990");
});

it("keeps the selected entity graph complete when map dates are filtered", async () => {
  const getGraph = vi.spyOn(explorationApi, "getGraph");
  renderExplorer("/?period_from=1900&period_to=1950");

  await screen.findByRole("heading", { level: 1, name: "Грозный" });
  await waitFor(() => {
    expect(getGraph).toHaveBeenCalledWith(
      entityIds.grozny,
      {},
      expect.any(AbortSignal),
    );
  });
});

it("renders the real relations returned with the filtered map payload", async () => {
  vi.spyOn(explorationApi, "getMapEntities").mockResolvedValue({
    items: mockMapEntities.slice(0, 2),
    relations: [{ from: mockMapEntities[0].id, to: mockMapEntities[1].id }],
    truncated: false,
    relationsTruncated: false,
  });
  const { container } = renderExplorer();

  await screen.findByRole("heading", { level: 1, name: "Грозный" });
  expect(container.querySelectorAll(".hx-artmap-line")).toHaveLength(1);
});

it("opens a search result that has no map coordinates in the map modal", async () => {
  const user = userEvent.setup();
  vi.spyOn(explorationApi, "search").mockResolvedValue({
    items: [
      {
        id: entityIds.publicEducation,
        type: "event",
        title: { ru: "Событие без координат", ce: null },
        subtitle: "Опубликованное событие",
        coverUrl: "",
        relationsCount: 1,
      },
    ],
    meta: { limit: 8, offset: 0, total: 1 },
  });
  renderExplorer("/?q=событие");

  await user.click(
    await screen.findByRole("button", { name: /Событие без координат/ }),
  );

  expect(await screen.findByRole("dialog")).toBeVisible();
  expect(screen.getByLabelText("Текущий адрес")).toHaveTextContent(
    `modal=${entityIds.publicEducation}`,
  );
  expect(screen.getByLabelText("Текущий адрес")).toHaveTextContent("/");
});

it("uses the first type and status click as an inclusive filter", async () => {
  const user = userEvent.setup();
  const getMapEntities = vi.spyOn(explorationApi, "getMapEntities");
  renderExplorer();

  await screen.findByRole("heading", { level: 1, name: "Грозный" });
  await user.click(screen.getByRole("button", { name: "Личности" }));
  await waitFor(() => {
    expect(screen.getByLabelText("Текущий адрес")).toHaveTextContent(
      "types=person",
    );
    expect(getMapEntities).toHaveBeenLastCalledWith(
      expect.objectContaining({ types: ["person"] }),
      expect.any(AbortSignal),
    );
  });

  await user.click(screen.getByRole("button", { name: "Требует проверки" }));
  await waitFor(() => {
    expect(screen.getByLabelText("Текущий адрес")).toHaveTextContent(
      "research_statuses=needs_review",
    );
    expect(getMapEntities).toHaveBeenLastCalledWith(
      expect.objectContaining({ researchStatuses: ["needs_review"] }),
      expect.any(AbortSignal),
    );
  });
});

it("opens the selected published entity in a modal over the map", async () => {
  const user = userEvent.setup();
  renderExplorer();

  expect(
    await screen.findByRole("heading", { level: 1, name: "Грозный" }),
  ).toBeVisible();
  expect(
    await screen.findByRole("heading", { level: 2, name: "Грозный" }),
  ).toBeVisible();
  expect(screen.getByText("Подтверждённые отношения")).toBeVisible();

  await user.click(screen.getByRole("button", { name: "Свернуть карточку" }));
  expect(
    screen.getByRole("button", { name: "Развернуть карточку" }),
  ).toHaveAttribute("aria-expanded", "false");
  expect(
    screen
      .getByRole("button", { name: "Подробнее" })
      .closest(".hx-card-content"),
  ).toHaveAttribute("inert");
  await user.click(screen.getByRole("button", { name: "Развернуть карточку" }));

  await user.click(screen.getByRole("button", { name: /Хронология/ }));
  const timeline = await screen.findByRole("list", {
    name: "Хронология событий",
  });
  expect(within(timeline).getAllByRole("listitem")).toHaveLength(1);
  expect(within(timeline).getByText("1920–1930")).toBeVisible();

  const detailsTrigger = screen.getByRole("button", { name: "Подробнее" });
  await user.click(detailsTrigger);
  expect(await screen.findByRole("dialog")).toBeVisible();
  expect(screen.getByLabelText("Текущий адрес")).toHaveTextContent(
    `modal=${entityIds.grozny}`,
  );
  expect(screen.getByLabelText("Текущий адрес")).not.toHaveTextContent(
    "/entities/",
  );
});

it("shows photo sources and the central node when the modal graph has no edges", async () => {
  const user = userEvent.setup();
  vi.spyOn(explorationApi, "getGraph").mockImplementation((id) => {
    const center = fixtureEntity(id);
    return Promise.resolve({
      center: { id: center.id, type: center.entityType, title: center.title },
      nodes: [],
      edges: [],
      hidden_nodes_count: 0,
    });
  });
  vi.spyOn(explorationApi, "getEntitySources").mockResolvedValue({
    items: [
      {
        id: "40000000-0000-4000-8000-000000000002",
        title: "Архивная фотография Грозного",
        type: "photo",
        author: null,
        publisher: null,
        publication_year: null,
        url: "/archive-grozny.jpg",
        archive_reference: null,
        description: "",
        is_verified: true,
      },
    ],
    meta: { limit: 20, offset: 0, total: 1 },
  });
  renderExplorer();

  await user.click(await screen.findByRole("button", { name: "Подробнее" }));

  const dialog = await screen.findByRole("dialog");
  expect(
    within(dialog).getByRole("group", {
      name: "Визуальная паутина связей объекта Грозный",
    }),
  ).toBeVisible();
  expect(
    within(dialog).getByText(/Центральный объект остаётся на схеме/),
  ).toBeVisible();
  expect(
    within(dialog).getByRole("img", {
      name: "Архивная фотография Грозного",
    }),
  ).toHaveAttribute("src", "/archive-grozny.jpg");
  expect(within(dialog).getByText("Фотография")).toBeVisible();
  expect(within(dialog).getByText("Населённый пункт")).toBeVisible();
});

it("switches from the basemap to the selected real depth-two network", async () => {
  const user = userEvent.setup();
  renderExplorer();

  await screen.findByRole("heading", { level: 1, name: "Грозный" });
  await user.click(screen.getByRole("button", { name: /Паутина связей/ }));

  expect(
    await screen.findByRole("heading", { level: 2, name: "Паутина: Грозный" }),
  ).toBeVisible();
  expect(screen.getAllByText(/Уровень 1 · связей:/).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/Уровень 2 · связей:/).length).toBeGreaterThan(0);
  expect(screen.getByLabelText("Текущий адрес")).toHaveTextContent(
    "view=network",
  );
  expect(
    screen.getByRole("group", {
      name: /Визуальная паутина связей объекта Грозный/,
    }),
  ).toBeInTheDocument();
});

it("keeps the selected depth-two network when its center leaves the map payload", async () => {
  vi.spyOn(explorationApi, "getMapEntities").mockResolvedValue({
    items: mockMapEntities.filter((entity) => entity.id !== entityIds.grozny),
    relations: [],
    truncated: false,
    relationsTruncated: false,
  });
  renderExplorer(`/?view=network&entity=${entityIds.grozny}`);

  expect(
    await screen.findByRole("heading", { level: 2, name: "Паутина: Грозный" }),
  ).toBeVisible();
  expect(screen.getAllByText(/Уровень 1 · связей:/).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/Уровень 2 · связей:/).length).toBeGreaterThan(0);
  expect(screen.getByLabelText("Текущий адрес")).toHaveTextContent(
    `entity=${entityIds.grozny}`,
  );
});

function entityDetails(id: string) {
  const entity = mockMapEntities.find((item) => item.id === id);
  if (!entity) throw new Error(`Missing fixture entity: ${id}`);
  return {
    id: entity.id,
    type: entity.entityType,
    slug: entity.name.toLocaleLowerCase("ru-RU").replaceAll(" ", "-"),
    title: entity.title,
    short_description: { ru: entity.summary, ce: null },
    full_description: { ru: entity.description, ce: null },
    coordinates: {
      longitude: entity.coordinates[0],
      latitude: entity.coordinates[1],
    },
    period_from: entity.periodFrom,
    period_to: entity.periodTo,
    cover_url: entity.image || null,
    relations_count: entity.stats.relations,
    sources_count: 1,
    media_count: 0,
    status: "published" as const,
    research_status: "verified" as const,
  };
}

function entityGraph(id: string) {
  const linkedIds = [entityIds.grozny, entityIds.shali, entityIds.argun];
  const nodes = linkedIds
    .filter((entityId) => entityId !== id)
    .map((entityId) => {
      const entity = fixtureEntity(entityId);
      return {
        id: entity.id,
        type: entity.entityType,
        title: entity.title,
        relations_count: entity.stats.relations,
      };
    });
  const center = fixtureEntity(id);
  return {
    center: { id: center.id, type: center.entityType, title: center.title },
    nodes,
    edges: [
      graphEdge(edgeIds.groznyShali, entityIds.grozny, entityIds.shali),
      graphEdge(edgeIds.shaliArgun, entityIds.shali, entityIds.argun),
    ],
    hidden_nodes_count: 0,
  };
}

function graphEdge(id: string, sourceId: string, targetId: string) {
  return {
    id,
    source_id: sourceId,
    target_id: targetId,
    type: "connected_with" as const,
    title: { ru: "Историко-географическая связь", ce: null },
    description: { ru: "Связь подтверждена архивным источником", ce: null },
    sources_count: 1,
  };
}

function fixtureEntity(id: string) {
  const entity = mockMapEntities.find((item) => item.id === id);
  if (!entity) throw new Error(`Missing fixture entity: ${id}`);
  return entity;
}

function emptyPage() {
  return { items: [], meta: { limit: 20, offset: 0, total: 0 } };
}
