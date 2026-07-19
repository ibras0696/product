import {
  defaultModerationFilters,
  parseModerationFilters,
  toModerationSearchParams,
} from "../domain/filters";
import type { PublishNewEntityCommand } from "../domain/types";
import {
  createMockModerationPort,
  MODERATION_MOCK_IDS,
} from "./mockModerationPort";

const signal = new AbortController().signal;

function publishCommand(version: number): PublishNewEntityCommand {
  return {
    expectedVersion: version,
    idempotencyKey: "60000000-0000-4000-8000-000000000001",
    action: "create_entity",
    payload: {
      entity: {
        type: "landmark",
        slug: "school-history",
        title: { ru: "История сельской школы", ce: null },
        shortDescription: { ru: "История школьного образования", ce: null },
        fullDescription: {
          ru: "Проверенная история школы по архивной книге приказов.",
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
          title: "Книга приказов",
          type: "archive_document",
          author: null,
          publisher: null,
          publicationYear: null,
          url: null,
          archiveReference: "Опись 12",
          description: "Школьный архив",
        },
      ],
      approvedMediaIds: [],
    },
    comment: "Материал проверен",
  };
}

it("bounds queue filters and enforces permission before returning admin data", async () => {
  const urlFilters = parseModerationFilters(
    toModerationSearchParams({
      ...defaultModerationFilters,
      type: "report_error",
      limit: 500,
      offset: -10,
    }),
  );
  expect(urlFilters).toMatchObject({
    status: "pending",
    type: "report_error",
    limit: 50,
    offset: 0,
  });

  const port = createMockModerationPort("publish");
  const page = await port.getQueue(
    { ...defaultModerationFilters, limit: 500, type: "report_error" },
    signal,
  );
  expect(page.meta).toMatchObject({ limit: 50, total: 1 });
  expect(page.items[0]).toMatchObject({
    id: MODERATION_MOCK_IDS.reportPending,
    type: "report_error",
  });
  expect(page.items[0]).not.toHaveProperty("contact");

  const forbiddenPort = createMockModerationPort("none");
  await expect(
    forbiddenPort.getQueue(defaultModerationFilters, signal),
  ).rejects.toMatchObject({ code: "forbidden" });
  await expect(
    forbiddenPort.getSubmission(MODERATION_MOCK_IDS.reportPending, signal),
  ).rejects.toMatchObject({ code: "forbidden" });
});

it("replays the same publish command and rejects changed content for its key", async () => {
  const port = createMockModerationPort("publish");
  const detail = await port.getSubmission(
    MODERATION_MOCK_IDS.newEntityInReview,
    signal,
  );
  const command = publishCommand(detail.version);
  const first = await port.publishSubmission(detail.id, command, signal);
  await expect(
    port.publishSubmission(detail.id, command, signal),
  ).resolves.toEqual(first);
  await expect(
    port.publishSubmission(
      detail.id,
      { ...command, comment: "Другой комментарий" },
      signal,
    ),
  ).rejects.toMatchObject({ code: "idempotency_conflict" });
  await expect(port.getSubmission(detail.id, signal)).resolves.toMatchObject({
    status: "published",
  });
});
