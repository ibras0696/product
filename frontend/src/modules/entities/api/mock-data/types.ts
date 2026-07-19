import type {
  EntityDetails,
  EntitySource,
  EntityType,
  PublishedMedia,
  SourceType,
} from "../../domain/entity";

export interface EntityRecord {
  details: EntityDetails;
  sources: EntitySource[];
  media: PublishedMedia[];
}

export interface EntitySeed {
  id: string;
  type: EntityType;
  slug: string;
  title: string;
  shortDescription: string;
  fullDescription: string;
  coordinates: { latitude: number; longitude: number } | null;
  periodFrom: number | null;
  periodTo?: number | null;
  relations: number;
  sourceType?: SourceType;
  sourceTitle: string;
  coverUrl?: string;
  mediaWidth?: number;
  mediaHeight?: number;
}
