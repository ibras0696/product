import { submissionError } from "../domain/errors";
import type {
  PatchSubmissionMediaInput,
  SubmissionMedia,
  UploadSubmissionMediaInput,
} from "../domain/media";
import {
  assertEditable,
  assertUploadAllowed,
  createUploadSignature,
  getOwnedSubmission,
  makeUuid,
} from "./mockHelpers";
import type { MockSubmissionState } from "./mockState";
import { MAX_SUBMISSION_MEDIA } from "./mediaPrecheck";

function makeMedia(
  submissionId: string,
  input: UploadSubmissionMediaInput,
): SubmissionMedia {
  return {
    id: makeUuid(),
    submissionId,
    originalName: input.file.name,
    mimeType: input.file.type,
    sizeBytes: input.file.size,
    width: 1600,
    height: 1200,
    previewUrl: "/images/history/mountains.jpg",
    caption: input.caption,
    author: input.author,
    approximateDate: input.approximateDate,
    sourceDescription: input.sourceDescription,
    relatedEntityId: input.relatedEntityId,
    status: "pending",
  };
}

function replayUpload(
  state: MockSubmissionState,
  key: string,
  signature: string,
): SubmissionMedia | null {
  const replay = state.uploadsByIdempotencyKey.get(key);
  if (!replay) return null;
  if (replay.signature !== signature) {
    throw submissionError(
      "idempotency_conflict",
      "Ключ уже использован с другим файлом",
    );
  }
  return replay.media;
}

export async function uploadSubmissionMedia(
  state: MockSubmissionState,
  submissionId: string,
  input: UploadSubmissionMediaInput,
  idempotencyKey: string,
  signal: AbortSignal,
): Promise<SubmissionMedia> {
  signal.throwIfAborted();
  const current = getOwnedSubmission(state, submissionId);
  assertEditable(current);
  assertUploadAllowed(input);
  if (idempotencyKey.trim().length === 0) {
    throw submissionError("bad_request", "Idempotency-Key обязателен");
  }
  const signature = await createUploadSignature(submissionId, input);
  signal.throwIfAborted();
  const replay = replayUpload(state, idempotencyKey, signature);
  if (replay) return replay;
  const media = state.mediaBySubmissionId.get(submissionId) ?? [];
  if (media.length >= MAX_SUBMISSION_MEDIA) {
    throw submissionError("media_rejected", "Достигнут лимит файлов");
  }
  const uploaded = makeMedia(submissionId, input);
  state.mediaBySubmissionId.set(submissionId, [...media, uploaded]);
  state.uploadsByIdempotencyKey.set(idempotencyKey, {
    signature,
    media: uploaded,
  });
  if (state.lostResponseKeys.delete(idempotencyKey)) {
    throw submissionError("service_unavailable", "Ответ загрузки был потерян");
  }
  return uploaded;
}

export function getSubmissionMedia(
  state: MockSubmissionState,
  submissionId: string,
  signal: AbortSignal,
): Promise<SubmissionMedia[]> {
  return Promise.resolve().then(() => {
    signal.throwIfAborted();
    getOwnedSubmission(state, submissionId);
    return [...(state.mediaBySubmissionId.get(submissionId) ?? [])];
  });
}

export function patchSubmissionMedia(
  state: MockSubmissionState,
  submissionId: string,
  mediaId: string,
  patch: PatchSubmissionMediaInput,
  signal: AbortSignal,
): Promise<SubmissionMedia> {
  return Promise.resolve().then(() => {
    signal.throwIfAborted();
    const current = getOwnedSubmission(state, submissionId);
    assertEditable(current);
    const media = state.mediaBySubmissionId.get(submissionId) ?? [];
    const found = media.find((item) => item.id === mediaId);
    if (!found) throw submissionError("not_found", "Медиа не найдено");
    const updated = { ...found, ...patch };
    state.mediaBySubmissionId.set(
      submissionId,
      media.map((item) => (item.id === mediaId ? updated : item)),
    );
    return updated;
  });
}

export function deleteSubmissionMedia(
  state: MockSubmissionState,
  submissionId: string,
  mediaId: string,
  signal: AbortSignal,
): Promise<null> {
  return Promise.resolve().then(() => {
    signal.throwIfAborted();
    const current = getOwnedSubmission(state, submissionId);
    assertEditable(current);
    const media = state.mediaBySubmissionId.get(submissionId) ?? [];
    const remaining = media.filter((item) => item.id !== mediaId);
    if (remaining.length === media.length) {
      throw submissionError("not_found", "Медиа не найдено");
    }
    state.mediaBySubmissionId.set(submissionId, remaining);
    return null;
  });
}
