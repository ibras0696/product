import type {
  CreateSubmissionInput,
  SubmissionDraft,
} from "../domain/submission";
import {
  deleteSubmissionMedia,
  getSubmissionMedia,
  patchSubmissionMedia,
  uploadSubmissionMedia,
} from "./mockMediaOperations";
import { createMockSubmissionState } from "./mockState";
import {
  createNeedsRevisionFixture,
  createSubmission,
  getSubmissionStatus,
  patchSubmission,
  submitSubmission,
} from "./mockSubmissionOperations";
import type { SubmissionsPort } from "./submissionsPort";

export interface MockSubmissionsPort extends SubmissionsPort {
  mockOnlyCreateNeedsRevisionFixture(
    input: CreateSubmissionInput,
    publicComment: string,
    signal: AbortSignal,
  ): Promise<SubmissionDraft>;
  mockOnlyLoseNextUploadResponse(idempotencyKey: string): void;
}

export function createMockSubmissionsPort(): MockSubmissionsPort {
  const state = createMockSubmissionState();
  return {
    createSubmission: (input, signal) => createSubmission(state, input, signal),
    patchSubmission: (id, version, patch, signal) =>
      patchSubmission(state, id, version, patch, signal),
    submitSubmission: (id, version, signal) =>
      submitSubmission(state, id, version, signal),
    getSubmissionStatus: (code, signal) =>
      getSubmissionStatus(state, code, signal),
    uploadSubmissionMedia: (id, input, key, signal) =>
      uploadSubmissionMedia(state, id, input, key, signal),
    getSubmissionMedia: (id, signal) => getSubmissionMedia(state, id, signal),
    patchSubmissionMedia: (id, mediaId, patch, signal) =>
      patchSubmissionMedia(state, id, mediaId, patch, signal),
    deleteSubmissionMedia: (id, mediaId, signal) =>
      deleteSubmissionMedia(state, id, mediaId, signal),
    mockOnlyCreateNeedsRevisionFixture: (input, comment, signal) =>
      createNeedsRevisionFixture(state, input, comment, signal),
    mockOnlyLoseNextUploadResponse(key) {
      state.lostResponseKeys.add(key);
    },
  };
}
