import type { components } from "@/shared/api/schema";

import { submissionError } from "../domain/errors";
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

type SubmissionCreate = components["schemas"]["SubmissionCreate"];
type SubmissionPatch = components["schemas"]["SubmissionPatch"];
type DraftDto = components["schemas"]["SubmissionDraft"];
type StatusDto = components["schemas"]["SubmissionStatusView"];
type MediaDto = components["schemas"]["SubmissionMedia"];
type MediaPatch = components["schemas"]["SubmissionMediaPatch"];
type UploadBody =
  components["schemas"]["Body_upload_submission_media_api_v1_submissions__submission_id__media_post"];

export function toCreateDto(input: CreateSubmissionInput): SubmissionCreate {
  return {
    type: input.type,
    related_entity_id: input.relatedEntityId,
    settlement_id: input.settlementId,
    title: input.title,
    description: input.description,
    source_description: input.sourceDescription,
    author_name: input.authorName,
    contact: input.contact,
    consent: input.consent,
  };
}

export function toPatchDto(
  expectedVersion: number,
  patch: PatchSubmissionInput,
): SubmissionPatch {
  return {
    expected_version: expectedVersion,
    related_entity_id: patch.relatedEntityId,
    settlement_id: patch.settlementId,
    title: patch.title,
    description: patch.description,
    source_description: patch.sourceDescription,
    author_name: patch.authorName,
    contact: patch.contact,
    consent: patch.consent,
  };
}

export function toDraft(dto: DraftDto): SubmissionDraft {
  if (dto.status !== "draft" && dto.status !== "needs_revision") {
    throw submissionError("internal_error", "Unexpected submission status");
  }
  return {
    id: dto.id,
    type: dto.type,
    relatedEntityId: dto.related_entity_id,
    settlementId: dto.settlement_id,
    title: dto.title,
    description: dto.description,
    sourceDescription: dto.source_description,
    authorName: dto.author_name,
    contact: dto.contact,
    consent: dto.consent,
    status: dto.status,
    version: dto.version,
    trackingCode: dto.tracking_code,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

export function toStatus(dto: StatusDto): SubmissionStatusView {
  return {
    id: dto.id,
    trackingCode: dto.tracking_code,
    type: dto.type,
    title: dto.title,
    status: dto.status,
    publicComment: dto.public_comment,
    submittedAt: dto.submitted_at,
    updatedAt: dto.updated_at,
  };
}

export function toMedia(dto: MediaDto): SubmissionMedia {
  if (dto.status !== "pending") {
    throw submissionError("internal_error", "Unexpected media status");
  }
  return {
    id: dto.id,
    submissionId: dto.submission_id,
    originalName: dto.original_name,
    mimeType: dto.mime_type,
    sizeBytes: dto.size_bytes,
    width: dto.width,
    height: dto.height,
    previewUrl: dto.preview_url,
    caption: dto.caption,
    author: dto.author,
    approximateDate: dto.approximate_date,
    sourceDescription: dto.source_description,
    relatedEntityId: dto.related_entity_id,
    status: "pending",
  };
}

export function uploadForm(input: UploadSubmissionMediaInput): FormData {
  const metadata: Omit<UploadBody, "file"> = {
    caption: input.caption,
    author: input.author,
    source_description: input.sourceDescription,
    approximate_date: input.approximateDate,
    related_entity_id: input.relatedEntityId,
  };
  const form = new FormData();
  form.append("file", input.file);
  form.append("caption", metadata.caption);
  form.append("author", metadata.author);
  form.append("source_description", metadata.source_description);
  if (metadata.approximate_date != null)
    form.append("approximate_date", metadata.approximate_date);
  if (metadata.related_entity_id != null)
    form.append("related_entity_id", metadata.related_entity_id);
  return form;
}

export function toMediaPatch(patch: PatchSubmissionMediaInput): MediaPatch {
  return {
    caption: patch.caption,
    author: patch.author,
    approximate_date: patch.approximateDate,
    source_description: patch.sourceDescription,
    related_entity_id: patch.relatedEntityId,
  };
}
