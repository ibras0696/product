export type SubmissionErrorCode =
  | "bad_request"
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "conflict"
  | "payload_too_large"
  | "unsupported_media_type"
  | "validation_error"
  | "rate_limited"
  | "internal_error"
  | "service_unavailable"
  | "source_required"
  | "draft_not_editable"
  | "invalid_transition"
  | "media_rejected"
  | "idempotency_conflict";

export class SubmissionApplicationError extends Error {
  readonly code: SubmissionErrorCode;

  constructor(code: SubmissionErrorCode, message: string) {
    super(message);
    this.name = "SubmissionApplicationError";
    this.code = code;
  }
}

export function submissionError(
  code: SubmissionErrorCode,
  message: string,
): SubmissionApplicationError {
  return new SubmissionApplicationError(code, message);
}
