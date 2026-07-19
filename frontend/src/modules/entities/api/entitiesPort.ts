import type {
  BoundedPage,
  EntityDetails,
  EntityGraph,
  EntitySource,
  PublishedMedia,
} from "../domain/entity";

export const ENTITY_PAGE_LIMIT = 100;

export class EntityNotFoundError extends Error {
  constructor() {
    super("Entity was not found");
    this.name = "EntityNotFoundError";
  }
}

export interface EntitiesPort {
  getEntity(entityId: string, signal: AbortSignal): Promise<EntityDetails>;
  getGraph(entityId: string, signal: AbortSignal): Promise<EntityGraph>;
  getSources(
    entityId: string,
    limit: number,
    offset: number,
    signal: AbortSignal,
  ): Promise<BoundedPage<EntitySource>>;
  getMedia(
    entityId: string,
    limit: number,
    offset: number,
    signal: AbortSignal,
  ): Promise<BoundedPage<PublishedMedia>>;
}
