import type {
  PatchSubmissionMediaInput,
  SubmissionMedia,
  UploadSubmissionMediaInput,
} from "../domain/media";
import type {
  CreateSubmissionInput,
  PatchSubmissionInput,
  SubmissionDraft,
  SubmissionStatusView,
} from "../domain/submission";

export interface SubmissionsPort {
  createSubmission(
    input: CreateSubmissionInput,
    signal: AbortSignal,
  ): Promise<SubmissionDraft>;
  patchSubmission(
    submissionId: string,
    expectedVersion: number,
    patch: PatchSubmissionInput,
    signal: AbortSignal,
  ): Promise<SubmissionDraft>;
  submitSubmission(
    submissionId: string,
    expectedVersion: number,
    signal: AbortSignal,
  ): Promise<SubmissionStatusView>;
  getSubmissionStatus(
    trackingCode: string,
    signal: AbortSignal,
  ): Promise<SubmissionStatusView>;
  uploadSubmissionMedia(
    submissionId: string,
    input: UploadSubmissionMediaInput,
    idempotencyKey: string,
    signal: AbortSignal,
  ): Promise<SubmissionMedia>;
  getSubmissionMedia(
    submissionId: string,
    signal: AbortSignal,
  ): Promise<SubmissionMedia[]>;
  patchSubmissionMedia(
    submissionId: string,
    mediaId: string,
    patch: PatchSubmissionMediaInput,
    signal: AbortSignal,
  ): Promise<SubmissionMedia>;
  deleteSubmissionMedia(
    submissionId: string,
    mediaId: string,
    signal: AbortSignal,
  ): Promise<null>;
}
