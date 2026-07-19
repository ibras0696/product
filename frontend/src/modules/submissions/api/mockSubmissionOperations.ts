import { submissionError } from "../domain/errors";
import {
  toDraft,
  toStatusView,
  type CreateSubmissionInput,
  type PatchSubmissionInput,
  type SubmissionDraft,
  type SubmissionStatusView,
  type StoredSubmission,
} from "../domain/submission";
import {
  assertEditable,
  assertSubmittable,
  getOwnedSubmission,
  makeUuid,
  nowIso,
} from "./mockHelpers";
import type { MockSubmissionState } from "./mockState";

function makeStoredSubmission(
  input: CreateSubmissionInput,
  status: "draft" | "needs_revision",
  publicComment: string | null,
): StoredSubmission {
  const timestamp = nowIso();
  return {
    ...input,
    id: makeUuid(),
    status,
    version: 1,
    trackingCode: `tracking_${makeUuid()}_${makeUuid()}`,
    createdAt: timestamp,
    updatedAt: timestamp,
    publicComment,
    submittedAt: null,
  };
}

function storeSubmission(
  state: MockSubmissionState,
  submission: StoredSubmission,
): void {
  state.submissions.set(submission.id, submission);
  state.submissionIdByTrackingCode.set(submission.trackingCode, submission.id);
  state.mediaBySubmissionId.set(submission.id, []);
}

export function createSubmission(
  state: MockSubmissionState,
  input: CreateSubmissionInput,
  signal: AbortSignal,
): Promise<SubmissionDraft> {
  return Promise.resolve().then(() => {
    signal.throwIfAborted();
    const submission = makeStoredSubmission(input, "draft", null);
    storeSubmission(state, submission);
    return toDraft(submission);
  });
}

export function patchSubmission(
  state: MockSubmissionState,
  submissionId: string,
  expectedVersion: number,
  patch: PatchSubmissionInput,
  signal: AbortSignal,
): Promise<SubmissionDraft> {
  return Promise.resolve().then(() => {
    signal.throwIfAborted();
    const current = getOwnedSubmission(state, submissionId);
    assertEditable(current);
    if (current.version !== expectedVersion) {
      throw submissionError("conflict", "Версия черновика устарела");
    }
    const updated = {
      ...current,
      ...patch,
      version: current.version + 1,
      updatedAt: nowIso(),
    } satisfies StoredSubmission;
    state.submissions.set(updated.id, updated);
    return toDraft(updated);
  });
}

export function submitSubmission(
  state: MockSubmissionState,
  submissionId: string,
  expectedVersion: number,
  signal: AbortSignal,
): Promise<SubmissionStatusView> {
  return Promise.resolve().then(() => {
    signal.throwIfAborted();
    const current = getOwnedSubmission(state, submissionId);
    if (current.status === "pending") return toStatusView(current);
    assertEditable(current);
    if (current.version !== expectedVersion) {
      throw submissionError("conflict", "Версия черновика устарела");
    }
    assertSubmittable(
      current,
      state.mediaBySubmissionId.get(submissionId) ?? [],
    );
    const timestamp = nowIso();
    const submitted = {
      ...current,
      status: "pending",
      updatedAt: timestamp,
      submittedAt: timestamp,
    } satisfies StoredSubmission;
    state.submissions.set(submitted.id, submitted);
    return toStatusView(submitted);
  });
}

export function getSubmissionStatus(
  state: MockSubmissionState,
  trackingCode: string,
  signal: AbortSignal,
): Promise<SubmissionStatusView> {
  return Promise.resolve().then(() => {
    signal.throwIfAborted();
    const id = state.submissionIdByTrackingCode.get(trackingCode);
    if (!id) throw submissionError("not_found", "Заявка не найдена");
    return toStatusView(getOwnedSubmission(state, id));
  });
}

export function createNeedsRevisionFixture(
  state: MockSubmissionState,
  input: CreateSubmissionInput,
  publicComment: string,
  signal: AbortSignal,
): Promise<SubmissionDraft> {
  return Promise.resolve().then(() => {
    signal.throwIfAborted();
    const submission = makeStoredSubmission(
      input,
      "needs_revision",
      publicComment,
    );
    storeSubmission(state, submission);
    return toDraft(submission);
  });
}
