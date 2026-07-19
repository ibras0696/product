import { useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";

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

type CatalogSection = "entities" | "relations" | "sources" | "service";

const catalogSections: Array<{ id: CatalogSection; label: string }> = [
  { id: "entities", label: "Сущности" },
  { id: "relations", label: "Связи" },
  { id: "sources", label: "Источники" },
  { id: "service", label: "Аудит и экспорт" },
];

function CatalogTabs({
  active,
  onChange,
}: {
  active: CatalogSection;
  onChange: (section: CatalogSection) => void;
}) {
  return (
    <nav className="catalog-tabs" aria-label="Разделы каталога">
      {catalogSections.map((section) => (
        <button
          key={section.id}
          type="button"
          aria-current={section.id === active ? "page" : undefined}
          onClick={() => {
            onChange(section.id);
          }}
        >
          {section.label}
        </button>
      ))}
    </nav>
  );
}

function activeSection(params: URLSearchParams, pathname: string) {
  const requested = params.get("section");
  if (catalogSections.some((section) => section.id === requested))
    return requested as CatalogSection;
  return pathname.endsWith("/audit") ? "service" : "entities";
}

function EntitySection({
  port,
  permissions,
  filters,
}: AdminCatalogPageProps & {
  filters: ReturnType<typeof catalogFiltersFromUrl>;
}) {
  const [editing, setEditing] = useState<AdminEntityView | "create" | null>(
    null,
  );
  const query = useAdminEntities(port, permissions, filters);
  const mutations = useCatalogMutations(port, permissions);
  async function save(input: EntityInput) {
    if (editing === "create") await mutations.create.mutateAsync(input);
    else if (editing)
      await mutations.update.mutateAsync({ entity: editing, input });
    setEditing(null);
  }
  return (
    <>
      <CatalogFilters filters={filters} />
      <CatalogEntityList
        page={query.data}
        pending={query.isPending}
        error={query.error}
        canWrite={permissions.write}
        onCreate={() => {
          setEditing("create");
        }}
        onEdit={setEditing}
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
    </>
  );
}

export function AdminCatalogPage({ port, permissions }: AdminCatalogPageProps) {
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const filters = catalogFiltersFromUrl(params);
  const section = activeSection(params, location.pathname);
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
      <CatalogTabs
        active={section}
        onChange={(nextSection) => {
          setParams((current) => {
            const next = new URLSearchParams(current);
            next.set("section", nextSection);
            next.delete("page");
            return next;
          });
        }}
      />
      {section === "entities" ? (
        <EntitySection
          port={port}
          permissions={permissions}
          filters={filters}
        />
      ) : null}
      {section === "relations" ? (
        <RelationsPanel port={port} permissions={permissions} />
      ) : null}
      {section === "sources" ? (
        <SourcesPanel port={port} permissions={permissions} />
      ) : null}
      {section === "service" ? (
        <div className="catalog-secondary">
          <AuditView port={port} permissions={permissions} />
          <ExportPanel port={port} permissions={permissions} />
        </div>
      ) : null}
    </div>
  );
}
