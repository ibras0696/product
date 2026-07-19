import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { AdminCatalogPort } from "../api/adminCatalogPort";
import type {
  AdminCatalogPermissions,
  AdminEntityView,
  AdminRelationView,
  AdminSourceView,
  BoundedPage,
  EntityInput,
  EntityListFilters,
  RelationInput,
  RelationListFilters,
  SourceInput,
  SourceListFilters,
} from "../domain/catalog";

export const catalogKeys = {
  all: ["admin-catalog"] as const,
  entitiesRoot: ["admin-catalog", "entities"] as const,
  entities: (filters: EntityListFilters) =>
    ["admin-catalog", "entities", filters] as const,
  audit: ["admin-catalog", "audit"] as const,
  relations: (filters: RelationListFilters) =>
    ["admin-catalog", "relations", filters] as const,
  sources: (filters: SourceListFilters) =>
    ["admin-catalog", "sources", filters] as const,
};

export function useAdminEntities(
  port: AdminCatalogPort,
  permissions: AdminCatalogPermissions,
  filters: EntityListFilters,
) {
  return useQuery({
    queryKey: catalogKeys.entities(filters),
    queryFn: ({ signal }) => port.listEntities(filters, permissions, signal),
  });
}

export function useAdminRelations(
  port: AdminCatalogPort,
  permissions: AdminCatalogPermissions,
  filters: RelationListFilters,
) {
  return useQuery({
    queryKey: catalogKeys.relations(filters),
    queryFn: ({ signal }) => port.listRelations(filters, permissions, signal),
  });
}

export function useAdminSources(
  port: AdminCatalogPort,
  permissions: AdminCatalogPermissions,
  filters: SourceListFilters,
) {
  return useQuery({
    queryKey: catalogKeys.sources(filters),
    queryFn: ({ signal }) => port.listSources(filters, permissions, signal),
  });
}

export function useAudit(
  port: AdminCatalogPort,
  permissions: AdminCatalogPermissions,
) {
  return useQuery({
    queryKey: catalogKeys.audit,
    queryFn: ({ signal }) => port.listAudit(20, 0, permissions, signal),
    enabled: permissions.auditRead,
  });
}

export function useRelationMutations(
  port: AdminCatalogPort,
  permissions: AdminCatalogPermissions,
) {
  const client = useQueryClient();
  const invalidate = () =>
    client.invalidateQueries({ queryKey: catalogKeys.all });
  const create = useMutation({
    mutationFn: (input: RelationInput) =>
      port.createRelation(input, permissions, new AbortController().signal),
    onSuccess: invalidate,
  });
  const update = useMutation({
    mutationFn: ({
      relation,
      input,
    }: {
      relation: AdminRelationView;
      input: RelationInput;
    }) =>
      port.updateRelation(
        relation.id,
        input,
        relation.version,
        permissions,
        new AbortController().signal,
      ),
    onSuccess: invalidate,
  });
  const archive = useMutation({
    mutationFn: (relation: AdminRelationView) =>
      port.archiveRelation(
        relation.id,
        relation.version,
        permissions,
        new AbortController().signal,
      ),
    onSuccess: invalidate,
  });
  return { create, update, archive };
}

export function useSourceMutations(
  port: AdminCatalogPort,
  permissions: AdminCatalogPermissions,
) {
  const client = useQueryClient();
  const invalidate = () =>
    client.invalidateQueries({ queryKey: catalogKeys.all });
  const create = useMutation({
    mutationFn: (input: SourceInput) =>
      port.createSource(input, permissions, new AbortController().signal),
    onSuccess: invalidate,
  });
  const update = useMutation({
    mutationFn: ({
      source,
      input,
    }: {
      source: AdminSourceView;
      input: SourceInput;
    }) =>
      port.updateSource(
        source.id,
        input,
        source.version,
        permissions,
        new AbortController().signal,
      ),
    onSuccess: invalidate,
  });
  const archive = useMutation({
    mutationFn: (source: AdminSourceView) =>
      port.archiveSource(
        source.id,
        source.version,
        permissions,
        new AbortController().signal,
      ),
    onSuccess: invalidate,
  });
  return { create, update, archive };
}

export function useCatalogMutations(
  port: AdminCatalogPort,
  permissions: AdminCatalogPermissions,
) {
  const client = useQueryClient();
  const invalidate = () =>
    Promise.all([
      client.invalidateQueries({ queryKey: catalogKeys.all }),
      client.invalidateQueries({ queryKey: catalogKeys.audit }),
    ]);
  const create = useMutation({
    mutationFn: (input: EntityInput) =>
      port.createEntity(input, permissions, new AbortController().signal),
    onSuccess: invalidate,
  });
  const update = useMutation({
    mutationFn: ({
      entity,
      input,
    }: {
      entity: AdminEntityView;
      input: EntityInput;
    }) =>
      port.updateEntity(
        entity.id,
        input,
        entity.version,
        permissions,
        new AbortController().signal,
      ),
    onSuccess: invalidate,
  });
  const archive = useMutation({
    mutationFn: (entity: AdminEntityView) =>
      port.archiveEntity(
        entity.id,
        entity.version,
        permissions,
        new AbortController().signal,
      ),
    onMutate: async (entity) => {
      await client.cancelQueries({ queryKey: catalogKeys.entitiesRoot });
      const snapshot = client.getQueriesData<BoundedPage<AdminEntityView>>({
        queryKey: catalogKeys.entitiesRoot,
      });
      client.setQueriesData<BoundedPage<AdminEntityView>>(
        { queryKey: catalogKeys.entitiesRoot },
        (page) => optimisticArchive(page, entity),
      );
      return { snapshot };
    },
    onError: (_error, _entity, context) => {
      context?.snapshot.forEach(([key, page]) =>
        client.setQueryData(key, page),
      );
    },
    onSettled: invalidate,
  });
  return { create, update, archive };
}

function optimisticArchive(
  page: BoundedPage<AdminEntityView> | undefined,
  entity: AdminEntityView,
) {
  if (!page) return page;
  return {
    ...page,
    items: page.items.map((item) =>
      item.id === entity.id
        ? { ...item, status: "archived" as const, version: item.version + 1 }
        : item,
    ),
  };
}
