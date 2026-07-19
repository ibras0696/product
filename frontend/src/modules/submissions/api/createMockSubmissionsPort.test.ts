import { SubmissionApplicationError } from "../domain/errors";
import type { CreateSubmissionInput } from "../domain/submission";
import { createMockSubmissionsPort } from "./createMockSubmissionsPort";
import { MAX_SUBMISSION_MEDIA_BYTES } from "./mediaPrecheck";

const signal = new AbortController().signal;

function validDraft(
  overrides: Partial<CreateSubmissionInput> = {},
): CreateSubmissionInput {
  return {
    type: "new_entity",
    relatedEntityId: null,
    settlementId: "10000000-0000-4000-8000-000000000010",
    title: "История семейной башни",
    description: "Подробное описание материала",
    sourceDescription: "Семейный архив",
    authorName: "Автор материала",
    contact: "author@example.com",
    consent: true,
    ...overrides,
  };
}

function image(name = "tower.jpg", content = "image-bytes") {
  return new File([content], name, { type: "image/jpeg" });
}

it("creates, edits and submits each supported draft type through one workflow", async () => {
  const port = createMockSubmissionsPort();
  const drafts = await Promise.all(
    (
      [
        "new_entity",
        "update_entity",
        "new_relation",
        "new_source",
        "new_media",
        "report_error",
      ] as const
    ).map((type) => port.createSubmission(validDraft({ type }), signal)),
  );
  expect(drafts.map(({ type }) => type)).toEqual([
    "new_entity",
    "update_entity",
    "new_relation",
    "new_source",
    "new_media",
    "report_error",
  ]);

  const patched = await port.patchSubmission(
    drafts[0]?.id ?? "missing",
    drafts[0]?.version ?? 1,
    { title: "Уточнённая история башни" },
    signal,
  );
  expect(patched).toMatchObject({
    title: "Уточнённая история башни",
    status: "draft",
    version: 2,
  });
  const submitted = await port.submitSubmission(
    patched.id,
    patched.version,
    signal,
  );
  expect(submitted).toMatchObject({ status: "pending", title: patched.title });
  await expect(
    port.submitSubmission(patched.id, patched.version, signal),
  ).resolves.toEqual(submitted);
});

it("edits a mock-only revision fixture and sends it back to moderation", async () => {
  const port = createMockSubmissionsPort();
  const revision = await port.mockOnlyCreateNeedsRevisionFixture(
    validDraft(),
    "Добавьте точную ссылку на источник",
    signal,
  );
  expect(revision.status).toBe("needs_revision");

  const patched = await port.patchSubmission(
    revision.id,
    revision.version,
    { sourceDescription: "Семейный архив, опись 12" },
    signal,
  );
  expect(patched).toMatchObject({ status: "needs_revision", version: 2 });
  await expect(
    port.submitSubmission(revision.id, patched.version, signal),
  ).resolves.toMatchObject({ status: "pending" });
});

it("rejects a stale expected version without overwriting the draft", async () => {
  const port = createMockSubmissionsPort();
  const draft = await port.createSubmission(validDraft(), signal);

  await expect(
    port.patchSubmission(
      draft.id,
      draft.version + 1,
      { title: "Устаревшая запись" },
      signal,
    ),
  ).rejects.toMatchObject({ code: "conflict" });
  await expect(
    port.patchSubmission(
      draft.id,
      draft.version,
      { title: "Актуальная запись" },
      signal,
    ),
  ).resolves.toMatchObject({ title: "Актуальная запись", version: 2 });
});

it("replays a lost upload response and rejects key reuse with another payload", async () => {
  const port = createMockSubmissionsPort();
  const draft = await port.createSubmission(validDraft(), signal);
  const input = {
    file: image(),
    caption: "Семейная башня",
    author: "Автор фотографии",
    approximateDate: "1950-е",
    sourceDescription: "Семейный архив",
    relatedEntityId: null,
  };
  const key = "40000000-0000-4000-8000-000000000001";
  port.mockOnlyLoseNextUploadResponse(key);

  await expect(
    port.uploadSubmissionMedia(draft.id, input, key, signal),
  ).rejects.toMatchObject({ code: "service_unavailable" });
  const replay = await port.uploadSubmissionMedia(draft.id, input, key, signal);
  expect(replay.originalName).toBe("tower.jpg");
  await expect(
    port.uploadSubmissionMedia(
      draft.id,
      { ...input, file: image("other.jpg", "different") },
      key,
      signal,
    ),
  ).rejects.toMatchObject({ code: "idempotency_conflict" });
  await expect(port.getSubmissionMedia(draft.id, signal)).resolves.toHaveLength(
    1,
  );
});

it("rejects invalid media and does not reveal an unknown tracking code", async () => {
  const port = createMockSubmissionsPort();
  const draft = await port.createSubmission(validDraft(), signal);
  const oversized = new File(["x"], "scan.gif", { type: "image/gif" });
  Object.defineProperty(oversized, "size", {
    value: MAX_SUBMISSION_MEDIA_BYTES + 1,
  });

  await expect(
    port.uploadSubmissionMedia(
      draft.id,
      {
        file: oversized,
        caption: "Скан",
        author: "Автор",
        approximateDate: null,
        sourceDescription: "Архив",
        relatedEntityId: null,
      },
      "40000000-0000-4000-8000-000000000002",
      signal,
    ),
  ).rejects.toBeInstanceOf(SubmissionApplicationError);
  await expect(
    port.getSubmissionStatus("unknown-tracking-code", signal),
  ).rejects.toMatchObject({ code: "not_found" });
});
