import { useQuery } from "@tanstack/react-query";

import type { EntityBundle } from "../domain/entity";
import { ENTITY_PAGE_LIMIT, type EntitiesPort } from "../api/entitiesPort";

async function loadEntityBundle(
  entitiesPort: EntitiesPort,
  entityId: string,
  signal: AbortSignal,
): Promise<EntityBundle> {
  const [entity, graph, sources, media] = await Promise.all([
    entitiesPort.getEntity(entityId, signal),
    entitiesPort.getGraph(entityId, signal),
    entitiesPort.getSources(entityId, ENTITY_PAGE_LIMIT, 0, signal),
    entitiesPort.getMedia(entityId, ENTITY_PAGE_LIMIT, 0, signal),
  ]);
  return { entity, graph, sources, media };
}

export function useEntityBundle(entitiesPort: EntitiesPort, entityId: string) {
  return useQuery({
    queryKey: ["entities", "details", entityId],
    queryFn: ({ signal }) => loadEntityBundle(entitiesPort, entityId, signal),
  });
}
