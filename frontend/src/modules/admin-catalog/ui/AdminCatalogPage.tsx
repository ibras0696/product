import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import type { AdminCatalogPort } from "../api/adminCatalogPort";
import type {
  AdminCatalogPermissions,
  AdminEntityView,
  EntityInput,
} from "../domain/catalog";
import { useAdminEntities, useCatalogMutations } from "../model/catalogQueries";
import { catalogFiltersFromUrl } from "../model/urlFilters";
import { AuditView } from "./AuditView";
import { CatalogEntityList } from "./CatalogEntityList";
import { CatalogFilters } from "./CatalogFilters";
import { EntityEditor } from "./EntityEditor";
import { ExportPanel } from "./ExportPanel";
import { RelationsPanel } from "./RelationsPanel";
import { SourcesPanel } from "./SourcesPanel";
import "./admin-catalog.css";

export interface AdminCatalogPageProps {
  port: AdminCatalogPort;
  permissions: AdminCatalogPermissions;
}

export function AdminCatalogPage({ port, permissions }: AdminCatalogPageProps) {
  const [params] = useSearchParams();
  const [editing, setEditing] = useState<AdminEntityView | "create" | null>(
    null,
  );
  const filters = catalogFiltersFromUrl(params);
  const query = useAdminEntities(port, permissions, filters);
  const mutations = useCatalogMutations(port, permissions);
  async function save(input: EntityInput) {
    if (editing === "create") await mutations.create.mutateAsync(input);
    else if (editing)
      await mutations.update.mutateAsync({ entity: editing, input });
    setEditing(null);
  }
  if (!permissions.read) {
    return (
      <section className="catalog-state" role="alert">
        <h1>Каталог недоступен</h1>
        <p>Backend permission catalog:read обязателен.</p>
      </section>
    );
  }
  return (
    <div className="admin-catalog">
      <header className="admin-catalog__hero">
        <p>Управление данными</p>
        <h1>Каталог истории</h1>
        <span>Изменения версионируются и попадают в аудит.</span>
      </header>
      <CatalogFilters filters={filters} />
      <CatalogEntityList
        page={query.data}
        pending={query.isPending}
        error={query.error}
        canWrite={permissions.write}
        onCreate={() => {
          setEditing("create");
        }}
        onEdit={(entity) => {
          setEditing(entity);
        }}
        onArchive={(entity) =>
          mutations.archive.mutateAsync(entity).then(() => undefined)
        }
      />
      {editing ? (
        <EntityEditor
          key={
            editing === "create"
              ? "create"
              : `${editing.id}-${String(editing.version)}`
          }
          entity={editing === "create" ? null : editing}
          onSave={save}
          onCancel={() => {
            setEditing(null);
          }}
        />
      ) : null}
      <RelationsPanel port={port} permissions={permissions} />
      <SourcesPanel port={port} permissions={permissions} />
      <div className="catalog-secondary">
        <AuditView port={port} permissions={permissions} />
        <ExportPanel port={port} permissions={permissions} />
      </div>
    </div>
  );
}
