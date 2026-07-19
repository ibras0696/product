import { submissionError } from "../domain/errors";
import type {
  SubmissionMedia,
  UploadSubmissionMediaInput,
} from "../domain/media";
import type { StoredSubmission } from "../domain/submission";
import { precheckSubmissionMedia } from "./mediaPrecheck";
import type { MockSubmissionState } from "./mockState";

export function getOwnedSubmission(
  state: MockSubmissionState,
  submissionId: string,
): StoredSubmission {
  const submission = state.submissions.get(submissionId);
  if (!submission) throw submissionError("not_found", "Заявка не найдена");
  return submission;
}

export function assertEditable(submission: StoredSubmission): void {
  if (submission.status !== "draft" && submission.status !== "needs_revision") {
    throw submissionError(
      "draft_not_editable",
      "Заявка больше не доступна для редактирования",
    );
  }
}

export function assertSubmittable(
  submission: StoredSubmission,
  media: SubmissionMedia[],
): void {
  const required = [
    submission.title,
    submission.description,
    submission.authorName,
    submission.contact,
  ];
  if (required.some((value) => value.trim().length === 0)) {
    throw submissionError("validation_error", "Заполните обязательные поля");
  }
  if (submission.sourceDescription.trim().length === 0) {
    throw submissionError("source_required", "Укажите источник материала");
  }
  if (!submission.consent) {
    throw submissionError("validation_error", "Необходимо согласие автора");
  }
  const hasIncompleteMedia = media.some(
    (item) =>
      item.caption.trim().length === 0 ||
      item.author.trim().length === 0 ||
      item.sourceDescription.trim().length === 0,
  );
  if (hasIncompleteMedia) {
    throw submissionError("media_rejected", "Заполните описание медиа");
  }
}

export function assertUploadAllowed(input: UploadSubmissionMediaInput): void {
  const result = precheckSubmissionMedia(input.file);
  if (!result.ok) {
    throw submissionError(result.code, "Файл не прошёл проверку");
  }
}

export async function createUploadSignature(
  submissionId: string,
  input: UploadSubmissionMediaInput,
): Promise<string> {
  const bytes = new Uint8Array(await input.file.arrayBuffer());
  let hash = 2166136261;
  for (const byte of bytes) hash = Math.imul(hash ^ byte, 16777619);
  return JSON.stringify({
    submissionId,
    name: input.file.name,
    type: input.file.type,
    size: input.file.size,
    contentHash: hash >>> 0,
    caption: input.caption,
    author: input.author,
    approximateDate: input.approximateDate,
    sourceDescription: input.sourceDescription,
    relatedEntityId: input.relatedEntityId,
  });
}

export function makeUuid(): string {
  return crypto.randomUUID();
}

export function nowIso(): string {
  return new Date().toISOString();
}
