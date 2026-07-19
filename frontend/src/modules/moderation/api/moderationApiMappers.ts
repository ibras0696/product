import type { components } from "@/shared/api/schema";

import type {
  ModerationFilters,
  ModerationPage,
  ModerationQueueItem,
  ModerationSubmission,
  EntityPatch,
  PublishCommand,
  PublishResult,
  SourceInput,
} from "../domain/types";

export type QueueDto = components["schemas"]["QueueItem"];
export type QueuePageDto = components["schemas"]["QueuePage"];
export type SubmissionDto = components["schemas"]["SubmissionDetails"];
type MediaDto = components["schemas"]["ModerationMedia"];
export type PublishDto = components["schemas"]["PublishResult"];
export type PublishCommandDto =
  | components["schemas"]["CreateEntityCommand"]
  | components["schemas"]["UpdateEntityCommand"]
  | components["schemas"]["CreateRelationCommand"]
  | components["schemas"]["AddSourceCommand"]
  | components["schemas"]["PublishMediaCommand"]
  | components["schemas"]["ResolveReportCommand"];

export function toQueueItem(dto: QueueDto): ModerationQueueItem {
  return {
    id: dto.id,
    type: dto.type,
    title: dto.title,
    status: dto.status,
    settlementId: dto.settlement_id,
    submittedAt: dto.submitted_at,
    createdAt: dto.created_at,
    claimedBy: dto.claimed_by,
    version: dto.version,
  };
}

export function toQueuePage(
  dto: QueuePageDto,
): ModerationPage<ModerationQueueItem> {
  return {
    items: dto.items.map(toQueueItem),
    meta: { limit: dto.limit, offset: dto.offset, total: dto.total },
  };
}

export function toSubmission(dto: SubmissionDto): ModerationSubmission {
  return {
    ...toQueueItem(dto),
    relatedEntityId: dto.related_entity_id,
    description: dto.description,
    sourceDescription: dto.source_description,
    authorName: dto.author_name,
    contact: dto.contact,
    consent: dto.consent,
    updatedAt: dto.updated_at,
    media: dto.media.map((media) => toModerationMedia(dto.id, media)),
  };
}

const supportedImageTypes = new Set(["image/jpeg", "image/png", "image/webp"]);

function safePreviewUrl(
  submissionId: string,
  mediaId: string,
  value: string,
  mimeType: string,
): string | null {
  if (!supportedImageTypes.has(mimeType)) return null;
  const expectedPath = `/api/v1/admin/submissions/${encodeURIComponent(submissionId)}/media/${encodeURIComponent(mediaId)}/preview`;
  try {
    const url = new URL(value, window.location.origin);
    if (url.origin !== window.location.origin || url.pathname !== expectedPath)
      return null;
    if (url.search || url.hash) return null;
    return url.pathname;
  } catch {
    return null;
  }
}

function toModerationMedia(
  submissionId: string,
  dto: MediaDto,
): ModerationSubmission["media"][number] {
  return {
    id: dto.id,
    originalName: dto.original_name,
    mimeType: dto.mime_type,
    sizeBytes: dto.size_bytes,
    width: dto.width,
    height: dto.height,
    previewUrl: safePreviewUrl(
      submissionId,
      dto.id,
      dto.preview_url,
      dto.mime_type,
    ),
    caption: dto.caption,
    author: dto.author,
    approximateDate: dto.approximate_date,
    sourceDescription: dto.source_description,
    relatedEntityId: dto.related_entity_id,
    status: dto.status,
  };
}

function toSource(source: SourceInput) {
  return {
    title: source.title,
    type: source.type,
    author: source.author,
    publisher: source.publisher,
    publication_year: source.publicationYear,
    url: source.url,
    archive_reference: source.archiveReference,
    description: source.description,
  };
}

function publishCommon(input: PublishCommand) {
  return {
    expected_version: input.expectedVersion,
    idempotency_key: input.idempotencyKey,
    comment: input.comment,
  };
}

function toEntityPatch(patch: EntityPatch) {
  return {
    ...(patch.slug !== undefined ? { slug: patch.slug } : {}),
    ...(patch.title !== undefined ? { title: patch.title } : {}),
    ...(patch.shortDescription !== undefined
      ? { short_description: patch.shortDescription }
      : {}),
    ...(patch.fullDescription !== undefined
      ? { full_description: patch.fullDescription }
      : {}),
    ...(patch.coordinates !== undefined
      ? { coordinates: patch.coordinates }
      : {}),
    ...(patch.periodFrom !== undefined
      ? { period_from: patch.periodFrom }
      : {}),
    ...(patch.periodTo !== undefined ? { period_to: patch.periodTo } : {}),
    ...(patch.districtId !== undefined
      ? { district_id: patch.districtId }
      : {}),
  };
}

function toUpdateEntityCommand(
  input: Extract<PublishCommand, { action: "update_entity" }>,
): PublishCommandDto {
  return {
    ...publishCommon(input),
    action: input.action,
    payload: {
      entity_id: input.payload.entityId,
      entity_patch: toEntityPatch(input.payload.entityPatch),
      sources: input.payload.sources.map(toSource),
      approved_media_ids: input.payload.approvedMediaIds,
    },
  };
}

function toRelationCommand(
  input: Extract<PublishCommand, { action: "create_relation" }>,
): PublishCommandDto {
  const relation = input.payload.relation;
  return {
    ...publishCommon(input),
    action: input.action,
    payload: {
      relation: {
        source_entity_id: relation.sourceEntityId,
        target_entity_id: relation.targetEntityId,
        type: relation.type,
        title: relation.title,
        description: relation.description,
        period_from: relation.periodFrom,
        period_to: relation.periodTo,
      },
      sources: input.payload.sources.map(toSource),
    },
  };
}

function toSourceCommand(
  input: Extract<PublishCommand, { action: "add_source" }>,
): PublishCommandDto {
  return {
    ...publishCommon(input),
    action: input.action,
    payload: {
      target_type: input.payload.targetType,
      target_id: input.payload.targetId,
      source: toSource(input.payload.source),
    },
  };
}

function toMediaCommand(
  input: Extract<PublishCommand, { action: "publish_media" }>,
): PublishCommandDto {
  return {
    ...publishCommon(input),
    action: input.action,
    payload: {
      target_entity_id: input.payload.targetEntityId,
      approved_media_ids: input.payload.approvedMediaIds,
    },
  };
}

function toReportCommand(
  input: Extract<PublishCommand, { action: "resolve_report" }>,
): PublishCommandDto {
  return {
    ...publishCommon(input),
    action: input.action,
    payload: {
      resolution: input.payload.resolution,
      ...(input.payload.entityPatch !== undefined
        ? {
            entity_patch: input.payload.entityPatch
              ? toEntityPatch(input.payload.entityPatch)
              : null,
          }
        : {}),
      ...(input.payload.archiveEntityId !== undefined
        ? { archive_entity_id: input.payload.archiveEntityId }
        : {}),
    },
  };
}

function toNewEntityCommand(
  input: Extract<PublishCommand, { action: "create_entity" }>,
): PublishCommandDto {
  const entity = input.payload.entity;
  return {
    ...publishCommon(input),
    action: input.action,
    payload: {
      entity: {
        type: entity.type,
        slug: entity.slug,
        title: entity.title,
        short_description: entity.shortDescription,
        full_description: entity.fullDescription,
        coordinates: entity.coordinates,
        period_from: entity.periodFrom,
        period_to: entity.periodTo,
        district_id: entity.districtId,
      },
      relations: [],
      sources: input.payload.sources.map(toSource),
      approved_media_ids: input.payload.approvedMediaIds,
    },
  };
}

export function toPublishCommand(input: PublishCommand): PublishCommandDto {
  switch (input.action) {
    case "create_entity":
      return toNewEntityCommand(input);
    case "update_entity":
      return toUpdateEntityCommand(input);
    case "create_relation":
      return toRelationCommand(input);
    case "add_source":
      return toSourceCommand(input);
    case "publish_media":
      return toMediaCommand(input);
    case "resolve_report":
      return toReportCommand(input);
  }
}

export function toPublishResult(
  dto: PublishDto,
  expectedAction: PublishCommand["action"],
): PublishResult {
  if (dto.action !== expectedAction)
    throw new Error("Unexpected publish action");
  return {
    submissionId: dto.submission_id,
    status: dto.status,
    action: dto.action,
    publishedEntityIds: dto.published_entity_ids,
    publishedRelationIds: dto.published_relation_ids,
    publishedSourceIds: dto.published_source_ids,
    publishedMediaIds: dto.published_media_ids,
    auditId: dto.audit_id,
  };
}

export function moderationQueueParams(filters: ModerationFilters): string {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.type) params.set("type", filters.type);
  if (filters.settlementId) params.set("settlement_id", filters.settlementId);
  if (filters.createdFrom) params.set("created_from", filters.createdFrom);
  if (filters.createdTo) params.set("created_to", filters.createdTo);
  params.set("limit", String(filters.limit));
  params.set("offset", String(filters.offset));
  return params.toString();
}
