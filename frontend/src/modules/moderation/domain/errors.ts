export type ModerationErrorCode =
  | "bad_request"
  | "unauthorized"
  | "not_found"
  | "forbidden"
  | "conflict"
  | "invalid_transition"
  | "idempotency_conflict"
  | "source_required"
  | "validation_error"
  | "rate_limited"
  | "internal_error"
  | "service_unavailable";

export class ModerationApplicationError extends Error {
  constructor(
    readonly code: ModerationErrorCode,
    message: string,
  ) {
    super(message);
    this.name = "ModerationApplicationError";
  }
}

export function moderationError(
  code: ModerationErrorCode,
  message: string,
): ModerationApplicationError {
  return new ModerationApplicationError(code, message);
}

export function isModerationError(
  error: unknown,
): error is ModerationApplicationError {
  return error instanceof ModerationApplicationError;
}
