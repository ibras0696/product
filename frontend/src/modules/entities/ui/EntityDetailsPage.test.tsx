import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { type ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, vi } from "vitest";

import type { EntitiesPort } from "../api/entitiesPort";
import { MOCK_ENTITY_IDS, mockEntitiesPort } from "../api/mockEntitiesAdapter";
import { EntityDetailsPage } from "./EntityDetailsPage";

afterEach(() => {
  vi.unstubAllGlobals();
});

function TestQueryProvider({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

function renderPage(
  entityId: string,
  onBack = vi.fn(),
  entitiesPort: EntitiesPort = mockEntitiesPort,
) {
  render(
    <TestQueryProvider>
      <EntityDetailsPage
        entityId={entityId}
        onBack={onBack}
        entitiesPort={entitiesPort}
      />
    </TestQueryProvider>,
  );
  return { onBack };
}

it("loads the entity, evidence and bounded media as one public workflow", async () => {
  const user = userEvent.setup();
  const { onBack } = renderPage(MOCK_ENTITY_IDS.grozny);

  expect(
    screen.getByRole("heading", { name: "Загружаем историю" }),
  ).toBeVisible();
  expect(
    await screen.findByRole("heading", { level: 1, name: "Грозный" }),
  ).toBeVisible();
  expect(
    screen.getByRole("heading", { level: 2, name: "Источники" }),
  ).toBeVisible();
  expect(screen.getAllByText("Проверено").length).toBeGreaterThanOrEqual(2);
  expect(
    screen.getByRole("heading", { level: 2, name: "Связи" }),
  ).toBeVisible();
  expect(screen.getByLabelText(/Визуальный граф связей/)).toBeInTheDocument();
  expect(screen.getByText(/источников: 1/)).toBeVisible();
  expect(
    screen.getAllByRole("link", { name: /уровень [12]/ }).length,
  ).toBeGreaterThan(0);
  const galleryImage = screen.getByRole("img", {
    name: "Современная панорама центральной части Грозного",
  });
  expect(galleryImage).toHaveAttribute("width", "960");
  const galleryItem = galleryImage.closest("li");
  expect(galleryItem).not.toBeNull();
  expect(
    within(galleryItem as HTMLElement).getByText("960 × 640 · image/jpeg"),
  ).toBeVisible();

  await user.click(screen.getByRole("button", { name: "Назад к карте" }));
  expect(onBack).toHaveBeenCalledOnce();
});

it("keeps a published entity useful when sources and media are empty", async () => {
  renderPage(MOCK_ENTITY_IDS.nozhayYurt);

  expect(
    await screen.findByRole("heading", { level: 1, name: "Ножай-Юрт" }),
  ).toBeVisible();
  expect(
    screen.getByText(/Проверенные источники пока не опубликованы/),
  ).toBeVisible();
  expect(screen.getByText(/Медиаматериалы ещё не опубликованы/)).toBeVisible();
});

it("adds sourced photos to the visual archive without duplicating media URLs", async () => {
  const duplicateUrl = "https://upload.wikimedia.org/duplicate.jpg";
  const uniqueUrl = "https://upload.wikimedia.org/unique.jpg";
  const photoSource = (
    id: string,
    title: string,
    archiveReference: string,
  ) => ({
    id,
    title,
    type: "photo" as const,
    author: "Wikimedia contributor",
    publisher: null,
    publicationYear: null,
    url: `https://commons.wikimedia.org/wiki/${id}`,
    archiveReference,
    description: "Оригинал и происхождение описаны в источнике.",
    verificationStatus: "verified" as const,
  });
  const port: EntitiesPort = {
    ...mockEntitiesPort,
    getSources: async () => ({
      items: [
        photoSource("duplicate", "Дублирующее фото", duplicateUrl),
        photoSource("unique", "Уникальное фото", uniqueUrl),
      ],
      meta: { limit: 12, offset: 0, total: 2 },
    }),
    getMedia: async () => ({
      items: [
        {
          id: "media-duplicate",
          publicUrl: duplicateUrl,
          previewUrl: duplicateUrl,
          mimeType: "image/jpeg",
          width: 1200,
          height: 800,
          caption: "Медиа-копия",
          author: null,
          approximateDate: null,
          sourceDescription: "Опубликованный media asset",
        },
      ],
      meta: { limit: 12, offset: 0, total: 1 },
    }),
  };

  renderPage(MOCK_ENTITY_IDS.grozny, vi.fn(), port);

  const mediaSection = (
    await screen.findByRole("heading", {
      name: "Медиатека",
    })
  ).closest("section");
  expect(mediaSection).not.toBeNull();
  expect(
    within(mediaSection as HTMLElement).getByText("2 опубликовано"),
  ).toBeVisible();
  expect(screen.getByRole("img", { name: "Уникальное фото" })).toBeVisible();
  expect(
    screen.queryByRole("img", { name: "Дублирующее фото" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByText("Происхождение: опубликованный фотоисточник"),
  ).toBeVisible();
});

it("uses the public API by default for a UUID received from the published map", async () => {
  const publishedId = "2bc0b62a-579a-4daf-9480-ef9ec785110b";
  const fetchMock = vi.fn<typeof fetch>((input) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.href
          : input.url;
    if (url.endsWith("/sources?limit=100&offset=0")) {
      return Promise.resolve(apiResponse(emptyPage));
    }
    if (url.endsWith("/media?limit=100&offset=0")) {
      return Promise.resolve(apiResponse(emptyPage));
    }
    if (url.includes("/graph?depth=2&limit=40")) {
      return Promise.resolve(
        apiResponse({
          center: {
            id: publishedId,
            type: "settlement",
            title: { ru: "Объект из карты", ce: null },
          },
          nodes: [],
          edges: [],
          hidden_nodes_count: 0,
        }),
      );
    }
    return Promise.resolve(
      apiResponse({
        id: publishedId,
        type: "settlement",
        slug: "real-published-entity",
        title: { ru: "Объект из карты", ce: null },
        short_description: { ru: "Краткое описание", ce: null },
        full_description: { ru: "Полная история объекта", ce: null },
        coordinates: null,
        period_from: null,
        period_to: null,
        cover_url: null,
        relations_count: 2,
        sources_count: 0,
        media_count: 0,
        status: "published",
        research_status: "verified",
      }),
    );
  });
  vi.stubGlobal("fetch", fetchMock);

  render(
    <TestQueryProvider>
      <EntityDetailsPage entityId={publishedId} onBack={vi.fn()} />
    </TestQueryProvider>,
  );

  await vi.waitFor(() => {
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });
  expect(
    fetchMock.mock.calls.map(([input]) =>
      typeof input === "string" ? input : String(input),
    ),
  ).toEqual([
    `/api/v1/entities/${publishedId}`,
    `/api/v1/entities/${publishedId}/graph?depth=2&limit=40`,
    `/api/v1/entities/${publishedId}/sources?limit=100&offset=0`,
    `/api/v1/entities/${publishedId}/media?limit=100&offset=0`,
  ]);

  expect(
    await screen.findByRole("heading", { level: 1, name: "Объект из карты" }),
  ).toBeVisible();
  expect(screen.getByText("Полная история объекта")).toBeVisible();
  expect(fetchMock).toHaveBeenCalledTimes(4);
});

it("distinguishes an unpublished entity from a temporary data failure", async () => {
  renderPage("10000000-0000-4000-8000-000000000099");
  expect(
    await screen.findByRole("heading", { name: "История не найдена" }),
  ).toBeVisible();
  cleanup();

  const unavailablePort: EntitiesPort = {
    getEntity: async () => Promise.reject(new Error("offline")),
    getGraph: async () => Promise.reject(new Error("offline")),
    getSources: async () => Promise.reject(new Error("offline")),
    getMedia: async () => Promise.reject(new Error("offline")),
  };
  renderPage(MOCK_ENTITY_IDS.grozny, vi.fn(), unavailablePort);
  expect(
    await screen.findByRole("heading", {
      name: "Не удалось открыть историю",
    }),
  ).toBeVisible();
});

const emptyPage = {
  items: [],
  meta: { limit: 12, offset: 0, total: 0 },
};

function apiResponse(data: unknown): Response {
  return new Response(
    JSON.stringify({
      ok: true,
      data,
      error: null,
      meta: { request_id: "entity-page-test" },
    }),
    { status: 200, headers: { "Content-Type": "application/json" } },
  );
}
