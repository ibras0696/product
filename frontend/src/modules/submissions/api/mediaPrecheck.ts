export const MAX_SUBMISSION_MEDIA = 10;
export const MAX_SUBMISSION_MEDIA_BYTES = 10 * 1024 * 1024;

const supportedMediaTypes = new Set(["image/jpeg", "image/png", "image/webp"]);

export type MediaPrecheckResult =
  | { ok: true }
  | {
      ok: false;
      code: "payload_too_large" | "unsupported_media_type" | "media_rejected";
    };

export function precheckSubmissionMedia(
  file: Pick<File, "size" | "type">,
): MediaPrecheckResult {
  if (!supportedMediaTypes.has(file.type)) {
    return { ok: false, code: "unsupported_media_type" };
  }
  if (file.size === 0) return { ok: false, code: "media_rejected" };
  if (file.size > MAX_SUBMISSION_MEDIA_BYTES) {
    return { ok: false, code: "payload_too_large" };
  }
  return { ok: true };
}
