import { afterEach, vi } from "vitest";

import type {
  AdminCatalogPermissions,
  EntityInput,
  RelationInput,
  SourceInput,
} from "../domain/catalog";
import { adminCatalogApi } from "./adminCatalogApi";

const permissions: AdminCatalogPermissions = {
  read: true,
  write: true,
  export: true,
  auditRead: true,
};
const signal = new AbortController().signal;
const input: EntityInput = {
  type: "artifact",
  slug: "museum-artifact",
  title: { ru: "Артефакт", ce: null },
  shortDescription: { ru: "Краткое описание", ce: null },
  fullDescription: { ru: "Полное описание", ce: null },
  coordinates: null,
  periodFrom: 1900,
  periodTo: 1950,
  districtId: null,
  status: "draft",
};
const entityDto = {
  id: "60000000-0000-4000-8000-000000000001",
  type: "artifact",
  slug: "museum-artifact",
  title: { ru: "Артефакт", ce: null },
  short_description: { ru: "Краткое описание", ce: null },
  full_description: { ru: "Полное описание", ce: null },
  coordinates: null,
  period_from: 1900,
  period_to: 1950,
  district_id: null,
  status: "draft",
  version: 4,
  relations_count: 1,
  sources_count: 2,
  media_count: 3,
} as const;
const relationInput: RelationInput = {
  sourceEntityId: "60000000-0000-4000-8000-000000000001",
  targetEntityId: "60000000-0000-4000-8000-000000000002",
  type: "born_in",
  title: { ru: "Родился в", ce: null },
  description: { ru: "Подтверждено источником", ce: null },
  periodFrom: 1900,
  periodTo: 1950,
  status: "draft",
};
const relationDto = {
  id: "61000000-0000-4000-8000-000000000001",
  source_entity_id: relationInput.sourceEntityId,
  target_entity_id: relationInput.targetEntityId,
  type: relationInput.type,
  title: relationInput.title,
  description: relationInput.description,
  period_from: relationInput.periodFrom,
  period_to: relationInput.periodTo,
  status: relationInput.status,
  version: 4,
} as const;
const sourceInput: SourceInput = {
  title: "Архивная справка",
  type: "archive_document",
  author: "Составитель",
  publisher: null,
  publicationYear: 1950,
  url: null,
  archiveReference: "Ф. 1",
  description: "Описание источника",
  isVerified: true,
  status: "draft",
};
const sourceDto = {
  id: "62000000-0000-4000-8000-000000000001",
  title: sourceInput.title,
  type: sourceInput.type,
  author: sourceInput.author,
  publisher: sourceInput.publisher,
  publication_year: sourceInput.publicationYear,
  url: sourceInput.url,
  archive_reference: sourceInput.archiveReference,
  description: sourceInput.description,
  is_verified: sourceInput.isVerified,
  status: sourceInput.status,
  version: 4,
} as const;

afterEach(() => vi.unstubAllGlobals());

it("maps the generated entity contract and sends create/update versions", async () => {
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValueOnce(
      ok({ items: [entityDto], meta: { limit: 10, offset: 0, total: 1 } }),
    )
    .mockResolvedValueOnce(ok(entityDto))
    .mockResolvedValueOnce(ok({ ...entityDto, version: 5 }));
  vi.stubGlobal("fetch", fetchMock);

  const page = await adminCatalogApi.listEntities(
    { type: "artifact", limit: 10, offset: 0 },
    permissions,
    signal,
  );
  expect(page.items[0]).toMatchObject({
    title: { ru: "Артефакт", ce: null },
    shortDescription: { ru: "Краткое описание", ce: null },
    version: 4,
  });
  await adminCatalogApi.createEntity(input, permissions, signal);
  await adminCatalogApi.updateEntity(
    entityDto.id,
    input,
    4,
    permissions,
    signal,
  );

  expect(fetchMock.mock.calls[0]?.[0]).toBe(
    "/api/v1/admin/catalog/entities?type=artifact&limit=10&offset=0",
  );
  expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({
    credentials: "same-origin",
  });
  expect(bodyAt(fetchMock, 1)).toMatchObject({
    expected_version: 0,
    type: "artifact",
  });
  expect(bodyAt(fetchMock, 2)).toMatchObject({
    expected_version: 4,
    status: "draft",
  });
  expect(bodyAt(fetchMock, 2)).not.toHaveProperty("type");
});

it("maps relation and source CRUD through generated contract endpoints", async () => {
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValueOnce(
      ok({ items: [relationDto], meta: { limit: 10, offset: 0, total: 1 } }),
    )
    .mockResolvedValueOnce(ok(relationDto))
    .mockResolvedValueOnce(ok({ ...relationDto, version: 5 }))
    .mockResolvedValueOnce(ok(null))
    .mockResolvedValueOnce(
      ok({ items: [sourceDto], meta: { limit: 10, offset: 0, total: 1 } }),
    )
    .mockResolvedValueOnce(ok(sourceDto))
    .mockResolvedValueOnce(ok({ ...sourceDto, version: 5 }))
    .mockResolvedValueOnce(ok(null));
  vi.stubGlobal("fetch", fetchMock);

  const relations = await adminCatalogApi.listRelations(
    { entityId: relationInput.sourceEntityId, type: "born_in", limit: 10 },
    permissions,
    signal,
  );
  const createdRelation = await adminCatalogApi.createRelation(
    relationInput,
    permissions,
    signal,
  );
  await adminCatalogApi.updateRelation(
    relationDto.id,
    relationInput,
    4,
    permissions,
    signal,
  );
  await adminCatalogApi.archiveRelation(relationDto.id, 5, permissions, signal);
  const sources = await adminCatalogApi.listSources(
    { query: "архив", type: "archive_document", limit: 10 },
    permissions,
    signal,
  );
  const createdSource = await adminCatalogApi.createSource(
    sourceInput,
    permissions,
    signal,
  );
  await adminCatalogApi.updateSource(
    sourceDto.id,
    sourceInput,
    4,
    permissions,
    signal,
  );
  await adminCatalogApi.archiveSource(sourceDto.id, 5, permissions, signal);

  expect(relations.items[0]).toMatchObject({
    sourceEntityId: relationInput.sourceEntityId,
    targetEntityId: relationInput.targetEntityId,
  });
  expect(createdRelation.version).toBe(4);
  expect(sources.items[0]).toMatchObject({ isVerified: true, version: 4 });
  expect(createdSource.publicationYear).toBe(1950);
  expect(fetchMock.mock.calls.map(([path]) => path)).toEqual([
    "/api/v1/admin/catalog/relations?entity_id=60000000-0000-4000-8000-000000000001&type=born_in&limit=10",
    "/api/v1/admin/catalog/relations",
    `/api/v1/admin/catalog/relations/${relationDto.id}`,
    `/api/v1/admin/catalog/relations/${relationDto.id}`,
    "/api/v1/admin/catalog/sources?query=%D0%B0%D1%80%D1%85%D0%B8%D0%B2&type=archive_document&limit=10",
    "/api/v1/admin/catalog/sources",
    `/api/v1/admin/catalog/sources/${sourceDto.id}`,
    `/api/v1/admin/catalog/sources/${sourceDto.id}`,
  ]);
  expect(bodyAt(fetchMock, 2)).toMatchObject({ expected_version: 4 });
  expect(bodyAt(fetchMock, 2)).not.toHaveProperty("source_entity_id");
  expect(bodyAt(fetchMock, 6)).toMatchObject({
    expected_version: 4,
    publication_year: 1950,
  });
  expect(bodyAt(fetchMock, 7)).toEqual({ expected_version: 5 });
});

it.each([
  [401, "unauthorized"],
  [403, "forbidden"],
  [409, "conflict"],
] as const)("exposes HTTP %s as %s", async (status, code) => {
  vi.stubGlobal(
    "fetch",
    vi.fn<typeof fetch>().mockResolvedValue(failed(status, code)),
  );
  await expect(
    adminCatalogApi.updateEntity(entityDto.id, input, 3, permissions, signal),
  ).rejects.toMatchObject({ code });
});

it("maps the flat audit page and downloads the binary export", async () => {
  const audit = {
    id: "80000000-0000-4000-8000-000000000001",
    actor_id: "70000000-0000-4000-8000-000000000001",
    action: "catalog.entity.update",
    resource_type: "entity",
    resource_id: entityDto.id,
    resource_version: 4,
    created_at: "2026-07-19T10:00:00Z",
  };
  vi.stubGlobal(
    "fetch",
    vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        ok({ items: [audit], limit: 20, offset: 0, total: 1 }),
      )
      .mockResolvedValueOnce(
        new Response("id,title\n1,Artifact", {
          status: 200,
          headers: {
            "Content-Type": "text/csv;charset=utf-8",
            "Content-Disposition":
              'attachment; filename="catalog-export-published.csv"',
          },
        }),
      ),
  );
  const page = await adminCatalogApi.listAudit(20, 0, permissions, signal);
  const file = await adminCatalogApi.exportCatalog(
    "csv",
    "published",
    permissions,
    signal,
  );
  expect(page).toEqual({
    items: [
      expect.objectContaining({
        action: "catalog.entity.update",
        resourceId: entityDto.id,
        resourceVersion: 4,
      }),
    ],
    meta: { limit: 20, offset: 0, total: 1 },
  });
  expect(file.filename).toBe("catalog-export-published.csv");
  expect(await file.blob.text()).toContain("Artifact");
});

function ok(data: unknown) {
  return new Response(JSON.stringify({ ok: true, data, error: null }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function failed(status: number, code: string) {
  return new Response(
    JSON.stringify({ ok: false, data: null, error: { code, message: "safe" } }),
    { status, headers: { "Content-Type": "application/json" } },
  );
}

function bodyAt(
  fetchMock: ReturnType<typeof vi.fn<typeof fetch>>,
  index: number,
) {
  const body = fetchMock.mock.calls[index]?.[1]?.body;
  if (typeof body !== "string") throw new Error("Expected JSON request body");
  return JSON.parse(body) as object;
}
