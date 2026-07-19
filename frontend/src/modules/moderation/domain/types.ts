export const moderationSubmissionTypes = [
  "new_entity",
  "update_entity",
  "new_relation",
  "new_source",
  "new_media",
  "report_error",
] as const;

export type ModerationSubmissionType =
  (typeof moderationSubmissionTypes)[number];

export const moderationStatuses = [
  "draft",
  "pending",
  "in_review",
  "needs_revision",
  "rejected",
  "published",
] as const;

export type ModerationStatus = (typeof moderationStatuses)[number];

export interface ModerationFilters {
  status: ModerationStatus | null;
  type: ModerationSubmissionType | null;
  settlementId: string | null;
  createdFrom: string | null;
  createdTo: string | null;
  limit: number;
  offset: number;
}

export interface ModerationQueueItem {
  id: string;
  type: ModerationSubmissionType;
  title: string;
  status: ModerationStatus;
  settlementId: string | null;
  submittedAt: string | null;
  createdAt: string;
  claimedBy: string | null;
  version: number;
}

export interface ModerationPage<T> {
  items: T[];
  meta: { limit: number; offset: number; total: number };
}

export interface ModerationSubmission extends ModerationQueueItem {
  relatedEntityId: string | null;
  description: string;
  sourceDescription: string;
  authorName: string;
  contact: string;
  consent: boolean;
  updatedAt: string;
  media: ModerationMedia[];
}

export interface ModerationMedia {
  id: string;
  originalName: string;
  mimeType: string;
  sizeBytes: number;
  width: number;
  height: number;
  previewUrl: string | null;
  caption: string;
  author: string;
  approximateDate: string | null;
  sourceDescription: string;
  relatedEntityId: string | null;
  status: "pending";
}

export interface ModerationClaimInput {
  expectedVersion: number;
}

export interface ModerationDecisionInput {
  expectedVersion: number;
  comment: string;
}

export interface LocalizedText {
  ru: string;
  ce: string | null;
}

export type EntityType =
  | "settlement"
  | "person"
  | "event"
  | "landmark"
  | "natural_object"
  | "cultural_object"
  | "organization"
  | "university_object"
  | "artifact";

export type SourceType =
  | "archive_document"
  | "book"
  | "scientific_article"
  | "museum_material"
  | "official_publication"
  | "photo"
  | "audio"
  | "video"
  | "oral_testimony"
  | "web_resource";

export type RelationType =
  | "born_in"
  | "lived_in"
  | "worked_in"
  | "studied_in"
  | "taught_at"
  | "participated_in"
  | "located_in"
  | "part_of"
  | "created_by"
  | "described_in"
  | "connected_with"
  | "connected_with_chgu";

export interface SourceInput {
  title: string;
  type: SourceType;
  author: string | null;
  publisher: string | null;
  publicationYear: number | null;
  url: string | null;
  archiveReference: string | null;
  description: string;
}

export interface EntityPatch {
  slug?: string | null;
  title?: LocalizedText | null;
  shortDescription?: LocalizedText | null;
  fullDescription?: LocalizedText | null;
  coordinates?: { latitude: number; longitude: number } | null;
  periodFrom?: number | null;
  periodTo?: number | null;
  districtId?: string | null;
}

interface PublishCommandBase {
  expectedVersion: number;
  idempotencyKey: string;
  comment: string;
}

export interface PublishNewEntityCommand extends PublishCommandBase {
  action: "create_entity";
  payload: {
    entity: {
      type: EntityType;
      slug: string;
      title: LocalizedText;
      shortDescription: LocalizedText;
      fullDescription: LocalizedText;
      coordinates: { latitude: number; longitude: number } | null;
      periodFrom: number | null;
      periodTo: number | null;
      districtId: string | null;
    };
    relations: [];
    sources: SourceInput[];
    approvedMediaIds: string[];
  };
}

export type PublishCommand =
  | PublishNewEntityCommand
  | (PublishCommandBase & {
      action: "update_entity";
      payload: {
        entityId: string;
        entityPatch: EntityPatch;
        sources: SourceInput[];
        approvedMediaIds: string[];
      };
    })
  | (PublishCommandBase & {
      action: "create_relation";
      payload: {
        relation: {
          sourceEntityId: string;
          targetEntityId: string;
          type: RelationType;
          title: LocalizedText;
          description: LocalizedText;
          periodFrom: number | null;
          periodTo: number | null;
        };
        sources: SourceInput[];
      };
    })
  | (PublishCommandBase & {
      action: "add_source";
      payload: {
        targetType: "entity" | "relation";
        targetId: string;
        source: SourceInput;
      };
    })
  | (PublishCommandBase & {
      action: "publish_media";
      payload: { targetEntityId: string; approvedMediaIds: string[] };
    })
  | (PublishCommandBase & {
      action: "resolve_report";
      payload: {
        resolution: string;
        entityPatch?: EntityPatch | null;
        archiveEntityId?: string | null;
      };
    });

export interface PublishResult {
  submissionId: string;
  status: "published";
  action: PublishCommand["action"];
  publishedEntityIds: string[];
  publishedRelationIds: string[];
  publishedSourceIds: string[];
  publishedMediaIds: string[];
  auditId: string;
}
