import type { SubmissionMedia } from "../domain/media";
import type { StoredSubmission } from "../domain/submission";

export interface UploadReplay {
  signature: string;
  media: SubmissionMedia;
}

export interface MockSubmissionState {
  submissions: Map<string, StoredSubmission>;
  submissionIdByTrackingCode: Map<string, string>;
  mediaBySubmissionId: Map<string, SubmissionMedia[]>;
  uploadsByIdempotencyKey: Map<string, UploadReplay>;
  lostResponseKeys: Set<string>;
}

export function createMockSubmissionState(): MockSubmissionState {
  return {
    submissions: new Map(),
    submissionIdByTrackingCode: new Map(),
    mediaBySubmissionId: new Map(),
    uploadsByIdempotencyKey: new Map(),
    lostResponseKeys: new Set(),
  };
}
