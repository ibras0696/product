import {
  AdminCatalogError,
  type AdminCatalogPermissions,
} from "../domain/catalog";
import { createMockAdminCatalogPort } from "./createMockAdminCatalogPort";

const fullAccess: AdminCatalogPermissions = {
  read: true,
  write: true,
  export: true,
  auditRead: true,
};
const signal = new AbortController().signal;

function input(title: string) {
  return {
    type: "event" as const,
    slug: "formula-safe",
    title: { ru: title, ce: null },
    shortDescription: { ru: "Краткое описание", ce: null },
    fullDescription: { ru: "Полное описание", ce: null },
    coordinates: null,
    periodFrom: null,
    periodTo: null,
    districtId: null,
    status: "draft" as const,
  };
}

it("applies bounded catalog edits, version conflicts, archive and audit as one workflow", async () => {
  const port = createMockAdminCatalogPort();
  const page = await port.listEntities({ limit: 1000 }, fullAccess, signal);
  expect(page.meta).toMatchObject({ limit: 100, offset: 0, total: 3 });
  const entity = page.items[0];
  expect(entity.id).toBe("60000000-0000-4000-8000-000000000001");
  const updated = await port.updateEntity(
    entity.id,
    {
      type: entity.type,
      slug: entity.slug,
      title: { ru: "Грозный обновлённый", ce: null },
      shortDescription: entity.shortDescription,
      fullDescription: entity.fullDescription,
      coordinates: entity.coordinates,
      periodFrom: entity.periodFrom,
      periodTo: entity.periodTo,
      districtId: entity.districtId,
      status: "published",
    },
    entity.version,
    fullAccess,
    signal,
  );
  await expect(
    port.updateEntity(
      entity.id,
      {
        type: entity.type,
        slug: entity.slug,
        title: { ru: "Устаревшая правка", ce: null },
        shortDescription: entity.shortDescription,
        fullDescription: entity.fullDescription,
        coordinates: entity.coordinates,
        periodFrom: entity.periodFrom,
        periodTo: entity.periodTo,
        districtId: entity.districtId,
        status: "published",
      },
      entity.version,
      fullAccess,
      signal,
    ),
  ).rejects.toMatchObject({ code: "conflict" });
  await expect(
    port.archiveEntity(entity.id, updated.version, fullAccess, signal),
  ).resolves.toBeNull();
  const archived = await port.listEntities(
    { status: "archived" },
    fullAccess,
    signal,
  );
  expect(archived.items.map((item) => item.id)).toContain(entity.id);
  const audit = await port.listAudit(500, 0, fullAccess, signal);
  expect(audit.meta.limit).toBe(100);
  expect(audit.items.map((item) => item.action)).toEqual([
    "catalog.entity.archive",
    "catalog.entity.update",
  ]);
});

it("exports allowlisted safe JSON/CSV and rejects limit and forbidden access", async () => {
  const port = createMockAdminCatalogPort();
  await port.createEntity(input("=SUM(1+1)"), fullAccess, signal);
  const json = await port.exportCatalog("json", "all", fullAccess, signal);
  const jsonText = await json.blob.text();
  expect(json).toMatchObject({
    filename: "catalog-export.json",
    contentType: "application/json;charset=utf-8",
  });
  expect(jsonText).toContain("formula-safe");
  expect(jsonText).not.toMatch(
    /contact|submission|password|session|storage_key|audit/i,
  );
  const csv = await port.exportCatalog("csv", "all", fullAccess, signal);
  expect(csv).toMatchObject({
    filename: "catalog-export.csv",
    contentType: "text/csv;charset=utf-8",
  });
  expect(await csv.blob.text()).toContain("'=SUM(1+1)");

  port.mockOnlySetExportRecordCount(10_001);
  await expect(
    port.exportCatalog("json", "all", fullAccess, signal),
  ).rejects.toMatchObject({ code: "export_too_large" });
  const forbidden = { ...fullAccess, export: false };
  await expect(
    port.exportCatalog("json", "all", forbidden, signal),
  ).rejects.toBeInstanceOf(AdminCatalogError);
});
