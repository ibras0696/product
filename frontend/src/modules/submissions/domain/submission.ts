export const submissionTypes = [
  "new_entity",
  "update_entity",
  "new_relation",
  "new_source",
  "new_media",
  "report_error",
] as const;

export type SubmissionType = (typeof submissionTypes)[number];

export type SubmissionStatus =
  | "draft"
  | "pending"
  | "in_review"
  | "needs_revision"
  | "rejected"
  | "published";

export interface CreateSubmissionInput {
  type: SubmissionType;
  relatedEntityId: string | null;
  settlementId: string | null;
  title: string;
  description: string;
  sourceDescription: string;
  authorName: string;
  contact: string;
  consent: boolean;
}

export type PatchSubmissionInput = Partial<Omit<CreateSubmissionInput, "type">>;

export interface SubmissionDraft extends CreateSubmissionInput {
  id: string;
  status: "draft" | "needs_revision";
  version: number;
  trackingCode: string;
  createdAt: string;
  updatedAt: string;
}

export interface SubmissionStatusView {
  id: string;
  trackingCode: string;
  type: SubmissionType;
  title: string;
  status: SubmissionStatus;
  publicComment: string | null;
  submittedAt: string | null;
  updatedAt: string;
}

export interface StoredSubmission extends CreateSubmissionInput {
  id: string;
  status: SubmissionStatus;
  version: number;
  trackingCode: string;
  createdAt: string;
  updatedAt: string;
  publicComment: string | null;
  submittedAt: string | null;
}

export function toDraft(submission: StoredSubmission): SubmissionDraft {
  if (submission.status !== "draft" && submission.status !== "needs_revision") {
    throw new Error("Only editable submissions can be returned as drafts");
  }
  return { ...submission, status: submission.status };
}

export function toStatusView(
  submission: StoredSubmission,
): SubmissionStatusView {
  return {
    id: submission.id,
    trackingCode: submission.trackingCode,
    type: submission.type,
    title: submission.title,
    status: submission.status,
    publicComment: submission.publicComment,
    submittedAt: submission.submittedAt,
    updatedAt: submission.updatedAt,
  };
}
