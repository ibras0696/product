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

export interface LocalizedText {
  ru: string;
  ce: string | null;
}

export interface EntityDetails {
  id: string;
  type: EntityType;
  slug: string;
  title: LocalizedText;
  shortDescription: LocalizedText;
  fullDescription: LocalizedText;
  coordinates: { latitude: number; longitude: number } | null;
  periodFrom: number | null;
  periodTo: number | null;
  coverUrl: string | null;
  counts: { relations: number; sources: number; media: number };
  status: "published";
  researchStatus: "verified" | "needs_review";
}

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

export interface EntityGraphNode {
  id: string;
  type: EntityType;
  title: LocalizedText;
  relationsCount: number;
}

export interface EntityGraphEdge {
  id: string;
  sourceId: string;
  targetId: string;
  type: RelationType;
  title: LocalizedText;
  description: LocalizedText;
  sourcesCount: number;
}

export interface EntityGraph {
  center: Omit<EntityGraphNode, "relationsCount">;
  nodes: EntityGraphNode[];
  edges: EntityGraphEdge[];
  hiddenNodesCount: number;
}

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

export interface EntitySource {
  id: string;
  title: string;
  type: SourceType;
  author: string | null;
  publisher: string | null;
  publicationYear: number | null;
  url: string | null;
  archiveReference: string | null;
  description: string;
  verificationStatus: "verified" | "contextual" | "oral_account";
}

export interface PublishedMedia {
  id: string;
  publicUrl: string;
  previewUrl: string;
  mimeType: string;
  width: number;
  height: number;
  caption: string;
  author: string | null;
  approximateDate: string | null;
  sourceDescription: string;
}

export interface BoundedPage<T> {
  items: T[];
  meta: { limit: number; offset: number; total: number };
}

export interface EntityBundle {
  entity: EntityDetails;
  graph: EntityGraph;
  sources: BoundedPage<EntitySource>;
  media: BoundedPage<PublishedMedia>;
}
