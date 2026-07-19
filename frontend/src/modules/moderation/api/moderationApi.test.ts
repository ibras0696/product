import type { components } from "@/shared/api/schema";
import { afterEach, vi } from "vitest";

import { defaultModerationFilters } from "../domain/filters";
import type { PublishCommand, PublishNewEntityCommand } from "../domain/types";
import { moderationApi } from "./moderationApi";
import { toPublishCommand } from "./moderationApiMappers";

type SubmissionDto = components["schemas"]["SubmissionDetails"];

const id = "50000000-0000-4000-8000-000000000001";
const signal = new AbortController().signal;

const detail: SubmissionDto = {
  id,
  type: "new_entity",
  status: "pending",
  version: 4,
  title: "Семейная башня",
  settlement_id: null,
  submitted_at: "2026-07-15T09:30:00Z",
  created_at: "2026-07-14T09:30:00Z",
  claimed_by: null,
  related_entity_id: null,
  description: "История башни из семейного архива",
  source_description: "Семейный архив, альбом № 4",
  author_name: "Марьям А.",
  contact: "maryam@example.test",
  consent: true,
  updated_at: "2026-07-15T10:30:00Z",
  media: [
    {
      id: "51000000-0000-4000-8000-000000000001",
      original_name: "family-tower.webp",
      mime_type: "image/webp",
      size_bytes: 786432,
      width: 1600,
      height: 1067,
      preview_url: `/api/v1/admin/submissions/${id}/media/51000000-0000-4000-8000-000000000001/preview`,
      caption: "Семейная башня",
      author: "Марьям А.",
      approximate_date: "1960-е годы",
      source_description: "Семейный архив, альбом № 4",
      related_entity_id: null,
      status: "pending",
    },
  ],
};

function apiResponse(
  status: number,
  ok: boolean,
  data: unknown,
  code?: string,
): Response {
  return new Response(
    JSON.stringify({
      ok,
      data,
      error: code ? { code, message: "Safe backend message" } : null,
      meta: { request_id: "moderation-test" },
    }),
    { status, headers: { "Content-Type": "application/json" } },
  );
}

function jsonBody(call: Parameters<typeof fetch>): unknown {
  const body = call[1]?.body;
  if (typeof body !== "string") throw new Error("Expected a JSON request body");
  return JSON.parse(body) as unknown;
}

function publishInput(): PublishNewEntityCommand {
  return {
    expectedVersion: 5,
    idempotencyKey: "60000000-0000-4000-8000-000000000001",
    action: "create_entity",
    comment: "Материал проверен",
    payload: {
      entity: {
        type: "landmark",
        slug: "family-tower",
        title: { ru: "Семейная башня", ce: null },
        shortDescription: { ru: "История семейной башни", ce: null },
        fullDescription: {
          ru: "Проверенная история семейной башни из архивных материалов.",
          ce: null,
        },
        coordinates: null,
        periodFrom: null,
        periodTo: null,
        districtId: null,
      },
      relations: [],
      sources: [
        {
          title: "Семейный архив",
          type: "archive_document",
          author: "Марьям А.",
          publisher: null,
          publicationYear: null,
          url: null,
          archiveReference: null,
          description: "Альбом № 4",
        },
      ],
      approvedMediaIds: ["51000000-0000-4000-8000-000000000001"],
    },
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

it("maps the bounded backend queue and keeps its flat pagination metadata", async () => {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
    apiResponse(200, true, {
      items: [detail],
      limit: 10,
      offset: 20,
      total: 31,
    }),
  );
  vi.stubGlobal("fetch", fetchMock);

  const page = await moderationApi.getQueue(
    { ...defaultModerationFilters, offset: 20 },
    signal,
  );

  expect(page.meta).toEqual({ limit: 10, offset: 20, total: 31 });
  expect(page.items[0]).toMatchObject({ id, settlementId: null, version: 4 });
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining("/api/v1/admin/submissions?status=pending"),
    expect.objectContaining({ method: "GET", credentials: "same-origin" }),
  );
});

it("maps media metadata and only exposes the contracted same-origin preview", async () => {
  const unsafeDetail: SubmissionDto = {
    ...detail,
    media: [
      detail.media[0],
      {
        ...detail.media[0],
        id: "51000000-0000-4000-8000-000000000002",
        original_name: "external.png",
        mime_type: "image/png",
        preview_url: "https://untrusted.example/preview.png",
      },
    ],
  };
  vi.stubGlobal(
    "fetch",
    vi
      .fn<typeof fetch>()
      .mockResolvedValue(apiResponse(200, true, unsafeDetail)),
  );

  const submission = await moderationApi.getSubmission(id, signal);

  expect(submission.media[0]).toMatchObject({
    originalName: "family-tower.webp",
    sizeBytes: 786432,
    previewUrl: `/api/v1/admin/submissions/${id}/media/51000000-0000-4000-8000-000000000001/preview`,
  });
  expect(submission.media[1].previewUrl).toBeNull();
});

it("sends the selected version for claim, revision, and rejection", async () => {
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockImplementation(() => Promise.resolve(apiResponse(200, true, detail)));
  vi.stubGlobal("fetch", fetchMock);

  await moderationApi.claimSubmission(id, { expectedVersion: 4 }, signal);
  await moderationApi.requestRevision(
    id,
    { expectedVersion: 5, comment: "Добавьте архивный шифр" },
    signal,
  );
  await moderationApi.rejectSubmission(
    id,
    { expectedVersion: 5, comment: "Источник не подтверждён" },
    signal,
  );

  expect(jsonBody(fetchMock.mock.calls[0])).toEqual({
    expected_version: 4,
  });
  expect(jsonBody(fetchMock.mock.calls[1])).toEqual({
    expected_version: 5,
    comment: "Добавьте архивный шифр",
  });
  expect(fetchMock.mock.calls[2][0]).toBe(
    `/api/v1/admin/submissions/${id}/reject`,
  );
});

it("publishes create_entity with the generated OpenAPI wire shape", async () => {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
    apiResponse(200, true, {
      submission_id: id,
      status: "published",
      action: "create_entity",
      published_entity_ids: ["70000000-0000-4000-8000-000000000001"],
      published_relation_ids: [],
      published_source_ids: ["80000000-0000-4000-8000-000000000001"],
      published_media_ids: [],
      audit_id: "90000000-0000-4000-8000-000000000001",
    }),
  );
  vi.stubGlobal("fetch", fetchMock);

  const result = await moderationApi.publishSubmission(
    id,
    publishInput(),
    signal,
  );
  const body = jsonBody(fetchMock.mock.calls[0]);

  expect(body).toMatchObject({
    action: "create_entity",
    expected_version: 5,
    idempotency_key: "60000000-0000-4000-8000-000000000001",
    payload: {
      entity: {
        short_description: { ru: "История семейной башни", ce: null },
        period_from: null,
        district_id: null,
      },
      approved_media_ids: ["51000000-0000-4000-8000-000000000001"],
    },
  });
  expect(result).toMatchObject({
    submissionId: id,
    action: "create_entity",
    publishedMediaIds: [],
  });
});

const commandBase = {
  expectedVersion: 5,
  idempotencyKey: "60000000-0000-4000-8000-000000000001",
  comment: "Решение проверено",
} as const;

const source = {
  title: "Архив",
  type: "archive_document" as const,
  author: null,
  publisher: null,
  publicationYear: null,
  url: null,
  archiveReference: "Фонд 1",
  description: "Проверенный источник",
};

it.each<[string, PublishCommand, object]>([
  [
    "update_entity",
    {
      ...commandBase,
      action: "update_entity",
      payload: {
        entityId: id,
        entityPatch: {
          fullDescription: { ru: "Уточнённое описание", ce: null },
        },
        sources: [source],
        approvedMediaIds: ["51000000-0000-4000-8000-000000000001"],
      },
    },
    {
      entity_id: id,
      entity_patch: {
        full_description: { ru: "Уточнённое описание", ce: null },
      },
      sources: [
        {
          title: "Архив",
          type: "archive_document",
          author: null,
          publisher: null,
          publication_year: null,
          url: null,
          archive_reference: "Фонд 1",
          description: "Проверенный источник",
        },
      ],
      approved_media_ids: ["51000000-0000-4000-8000-000000000001"],
    },
  ],
  [
    "create_relation",
    {
      ...commandBase,
      action: "create_relation",
      payload: {
        relation: {
          sourceEntityId: id,
          targetEntityId: "50000000-0000-4000-8000-000000000002",
          type: "connected_with",
          title: { ru: "Связь", ce: null },
          description: { ru: "Описание связи", ce: null },
          periodFrom: null,
          periodTo: null,
        },
        sources: [source],
      },
    },
    {
      relation: {
        source_entity_id: id,
        target_entity_id: "50000000-0000-4000-8000-000000000002",
        type: "connected_with",
        title: { ru: "Связь", ce: null },
        description: { ru: "Описание связи", ce: null },
        period_from: null,
        period_to: null,
      },
      sources: [
        {
          title: "Архив",
          type: "archive_document",
          author: null,
          publisher: null,
          publication_year: null,
          url: null,
          archive_reference: "Фонд 1",
          description: "Проверенный источник",
        },
      ],
    },
  ],
  [
    "add_source",
    {
      ...commandBase,
      action: "add_source",
      payload: { targetType: "relation", targetId: id, source },
    },
    {
      target_type: "relation",
      target_id: id,
      source: {
        title: "Архив",
        type: "archive_document",
        author: null,
        publisher: null,
        publication_year: null,
        url: null,
        archive_reference: "Фонд 1",
        description: "Проверенный источник",
      },
    },
  ],
  [
    "publish_media",
    {
      ...commandBase,
      action: "publish_media",
      payload: {
        targetEntityId: id,
        approvedMediaIds: ["51000000-0000-4000-8000-000000000001"],
      },
    },
    {
      target_entity_id: id,
      approved_media_ids: ["51000000-0000-4000-8000-000000000001"],
    },
  ],
  [
    "resolve_report",
    {
      ...commandBase,
      action: "resolve_report",
      payload: {
        resolution: "Ошибка подтверждена",
        entityPatch: { title: { ru: "Исправленное название", ce: null } },
      },
    },
    {
      resolution: "Ошибка подтверждена",
      entity_patch: { title: { ru: "Исправленное название", ce: null } },
    },
  ],
])(
  "maps %s to its exact generated discriminator payload",
  (_name, command, payload) => {
    expect(toPublishCommand(command)).toEqual({
      action: command.action,
      expected_version: 5,
      idempotency_key: commandBase.idempotencyKey,
      comment: commandBase.comment,
      payload,
    });
  },
);

it.each([
  [403, "forbidden"],
  [409, "conflict"],
] as const)(
  "surfaces HTTP %s as typed %s without trusting message text",
  async (status, code) => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn<typeof fetch>()
        .mockResolvedValue(apiResponse(status, false, null, code)),
    );

    await expect(
      moderationApi.rejectSubmission(
        id,
        { expectedVersion: 4, comment: "Решение" },
        signal,
      ),
    ).rejects.toMatchObject({ code });
  },
);

it("rejects a publish result whose discriminator mismatches the command", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn<typeof fetch>().mockResolvedValue(
      apiResponse(200, true, {
        submission_id: id,
        status: "published",
        action: "update_entity",
        published_entity_ids: [],
        published_relation_ids: [],
        published_source_ids: [],
        published_media_ids: [],
        audit_id: "90000000-0000-4000-8000-000000000001",
      }),
    ),
  );

  await expect(
    moderationApi.publishSubmission(id, publishInput(), signal),
  ).rejects.toMatchObject({ code: "internal_error" });
});
