import { afterEach, vi } from "vitest";

import { entitiesApi } from "./entitiesApi";
import { EntityNotFoundError } from "./entitiesPort";

const publishedEntityId = "2bc0b62a-579a-4daf-9480-ef9ec785110b";
const signal = new AbortController().signal;

afterEach(() => {
  vi.unstubAllGlobals();
});

it("loads a published map entity bundle from the public entity endpoints", async () => {
  const requestedUrls: string[] = [];
  const fetchMock = vi.fn<typeof fetch>((input, init) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.href
          : input.url;
    requestedUrls.push(url);
    expect(init).toMatchObject({
      method: "GET",
      credentials: "same-origin",
      signal,
    });
    if (url.endsWith("/sources?limit=12&offset=0")) {
      return Promise.resolve(apiResponse(sourcePage));
    }
    if (url.endsWith("/media?limit=12&offset=0")) {
      return Promise.resolve(apiResponse(mediaPage));
    }
    if (url.endsWith("/graph?depth=2&limit=40")) {
      return Promise.resolve(apiResponse(graph));
    }
    return Promise.resolve(apiResponse(entityDetails));
  });
  vi.stubGlobal("fetch", fetchMock);

  const [entity, entityGraph, sources, media] = await Promise.all([
    entitiesApi.getEntity(publishedEntityId, signal),
    entitiesApi.getGraph(publishedEntityId, signal),
    entitiesApi.getSources(publishedEntityId, 12, 0, signal),
    entitiesApi.getMedia(publishedEntityId, 12, 0, signal),
  ]);

  expect(entity).toMatchObject({
    id: publishedEntityId,
    title: { ru: "Опубликованный объект" },
    shortDescription: { ru: "Краткое описание" },
    counts: { relations: 3, sources: 1, media: 1 },
  });
  expect(sources.items[0]).toMatchObject({
    title: "Устное свидетельство",
    type: "oral_testimony",
    verificationStatus: "oral_account",
  });
  expect(media.items[0]).toMatchObject({
    previewUrl: "/api/v1/media/asset-id/preview",
    sourceDescription: "Семейный архив",
  });
  expect(entityGraph).toMatchObject({
    center: { id: publishedEntityId },
    nodes: [{ relationsCount: 2 }],
    edges: [{ sourcesCount: 3 }],
  });
  expect(requestedUrls).toEqual([
    `/api/v1/entities/${publishedEntityId}`,
    `/api/v1/entities/${publishedEntityId}/graph?depth=2&limit=40`,
    `/api/v1/entities/${publishedEntityId}/sources?limit=12&offset=0`,
    `/api/v1/entities/${publishedEntityId}/media?limit=12&offset=0`,
  ]);
});

it("maps the documented not_found code to the page-level missing state", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          ok: false,
          data: null,
          error: { code: "not_found", message: "Safe backend message" },
          meta: { request_id: "entity-test" },
        }),
        { status: 404, headers: { "Content-Type": "application/json" } },
      ),
    ),
  );

  await expect(
    entitiesApi.getEntity(publishedEntityId, signal),
  ).rejects.toBeInstanceOf(EntityNotFoundError);
});

function apiResponse(data: unknown): Response {
  return new Response(
    JSON.stringify({
      ok: true,
      data,
      error: null,
      meta: { request_id: "entity-test" },
    }),
    { status: 200, headers: { "Content-Type": "application/json" } },
  );
}

const entityDetails = {
  id: publishedEntityId,
  type: "settlement",
  slug: "published-entity",
  title: { ru: "Опубликованный объект", ce: null },
  short_description: { ru: "Краткое описание", ce: null },
  full_description: { ru: "Полное описание", ce: null },
  coordinates: { latitude: 43.31, longitude: 45.69 },
  period_from: 1900,
  period_to: null,
  cover_url: null,
  relations_count: 3,
  sources_count: 1,
  media_count: 1,
  status: "published",
  research_status: "verified",
};

const sourcePage = {
  items: [
    {
      id: "source-id",
      title: "Устное свидетельство",
      type: "oral_testimony",
      author: "Очевидец",
      publisher: null,
      publication_year: null,
      url: null,
      archive_reference: null,
      description: "Записанное свидетельство",
      is_verified: true,
    },
  ],
  meta: { limit: 12, offset: 0, total: 1 },
};

const graph = {
  center: {
    id: publishedEntityId,
    type: "settlement",
    title: { ru: "Опубликованный объект", ce: null },
  },
  nodes: [
    {
      id: "10000000-0000-4000-8000-000000000002",
      type: "person",
      title: { ru: "Связанная персона", ce: null },
      relations_count: 2,
    },
  ],
  edges: [
    {
      id: "30000000-0000-4000-8000-000000000001",
      source_id: publishedEntityId,
      target_id: "10000000-0000-4000-8000-000000000002",
      type: "connected_with",
      title: { ru: "Подтверждённая связь", ce: null },
      description: { ru: "Описание", ce: null },
      sources_count: 3,
    },
  ],
  hidden_nodes_count: 0,
};

const mediaPage = {
  items: [
    {
      id: "asset-id",
      public_url: "/api/v1/media/asset-id/original",
      preview_url: "/api/v1/media/asset-id/preview",
      mime_type: "image/webp",
      width: 640,
      height: 480,
      caption: "Архивное фото",
      author: "Автор",
      approximate_date: null,
      source_description: "Семейный архив",
    },
  ],
  meta: { limit: 12, offset: 0, total: 1 },
};
