import { useState } from "react";
import { useForm, type UseFormReturn } from "react-hook-form";

import type { AdminCatalogPort } from "../api/adminCatalogPort";
import type {
  AdminCatalogPermissions,
  AdminRelationType,
  AdminRelationView,
  RelationInput,
  RelationListFilters,
} from "../domain/catalog";
import {
  useAdminRelations,
  useRelationMutations,
} from "../model/catalogQueries";
import { RelationEditor } from "./RelationEditor";
import { ResourcePagination } from "./ResourcePagination";
import { relationTypes } from "./relationForm";
import { resourceError } from "./resourceMessages";

interface FilterValues {
  entityId: string;
  type: "" | AdminRelationType;
}

function relationFilters(values: FilterValues): RelationListFilters {
  return {
    entityId: values.entityId.trim() || undefined,
    type: values.type || undefined,
    limit: 20,
    offset: 0,
  };
}

function RelationPagination({
  page,
  onOffsetChange,
}: {
  page: NonNullable<ReturnType<typeof useAdminRelations>["data"]>;
  onOffsetChange: (offset: number) => void;
}) {
  return (
    <ResourcePagination
      label="Страницы связей"
      meta={page.meta}
      onOffsetChange={onOffsetChange}
    />
  );
}

export function RelationsPanel({
  port,
  permissions,
}: {
  port: AdminCatalogPort;
  permissions: AdminCatalogPermissions;
}) {
  const [filters, setFilters] = useState<RelationListFilters>({
    limit: 20,
    offset: 0,
  });
  const [editing, setEditing] = useState<AdminRelationView | "create" | null>(
    null,
  );
  const [actionError, setActionError] = useState<string | null>(null);
  const filterForm = useForm<FilterValues>({
    defaultValues: { entityId: "", type: "" },
  });
  const query = useAdminRelations(port, permissions, filters);
  const mutations = useRelationMutations(port, permissions);
  const apply = filterForm.handleSubmit((values) => {
    setFilters(relationFilters(values));
  });
  async function save(input: RelationInput) {
    if (editing === "create") await mutations.create.mutateAsync(input);
    else if (editing)
      await mutations.update.mutateAsync({ relation: editing, input });
    setEditing(null);
  }
  function archive(item: AdminRelationView) {
    if (!window.confirm(`Архивировать связь «${item.title.ru}»?`)) return;
    setActionError(null);
    void mutations.archive.mutateAsync(item).catch((error: unknown) => {
      setActionError(resourceError(error, "Не удалось архивировать связь."));
    });
  }
  return (
    <section className="catalog-resource" aria-labelledby="relations-title">
      <div className="catalog-heading">
        <h2 id="relations-title">Связи</h2>
        {permissions.write ? (
          <button
            type="button"
            onClick={() => {
              setEditing("create");
            }}
          >
            Добавить связь
          </button>
        ) : (
          <span>Только чтение</span>
        )}
      </div>
      <RelationFilters form={filterForm} onApply={apply} />
      <RelationQueryState
        actionError={actionError}
        query={query}
        canWrite={permissions.write}
        onEdit={setEditing}
        onArchive={archive}
      />
      {query.data ? (
        <RelationPagination
          page={query.data}
          onOffsetChange={(offset) => {
            setFilters((current) => ({ ...current, offset }));
          }}
        />
      ) : null}
      <RelationEditorPanel
        editing={editing}
        onSave={save}
        onCancel={() => {
          setEditing(null);
        }}
      />
    </section>
  );
}

function RelationEditorPanel({
  editing,
  onSave,
  onCancel,
}: {
  editing: AdminRelationView | "create" | null;
  onSave: (input: RelationInput) => Promise<void>;
  onCancel: () => void;
}) {
  if (!editing) return null;
  const relation = editing === "create" ? null : editing;
  const key = relation
    ? `${relation.id}-${String(relation.version)}`
    : "create";
  return (
    <RelationEditor
      key={key}
      relation={relation}
      onSave={onSave}
      onCancel={onCancel}
    />
  );
}

function RelationFilters({
  form,
  onApply,
}: {
  form: UseFormReturn<FilterValues>;
  onApply: ReturnType<UseFormReturn<FilterValues>["handleSubmit"]>;
}) {
  return (
    <form
      className="catalog-resource__filters"
      aria-label="Фильтры связей"
      onSubmit={(event) => {
        void onApply(event);
      }}
    >
      <label>
        UUID сущности
        <input {...form.register("entityId")} />
      </label>
      <label>
        Тип связи
        <select {...form.register("type")}>
          <option value="">Все</option>
          {relationTypes.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </label>
      <button type="submit">Применить</button>
    </form>
  );
}

function RelationQueryState({
  actionError,
  query,
  canWrite,
  onEdit,
  onArchive,
}: {
  actionError: string | null;
  query: ReturnType<typeof useAdminRelations>;
  canWrite: boolean;
  onEdit: (item: AdminRelationView | "create" | null) => void;
  onArchive: (item: AdminRelationView) => void;
}) {
  return (
    <>
      {actionError ? <p role="alert">{actionError}</p> : null}
      {query.isPending ? <p role="status">Загружаем связи…</p> : null}
      {query.isError ? (
        <p role="alert">
          {resourceError(query.error, "Не удалось загрузить связи.")}
        </p>
      ) : null}
      {query.data?.items.length === 0 ? (
        <p>Связей по этим фильтрам нет.</p>
      ) : null}
      {query.data ? (
        <RelationList
          items={query.data.items}
          canWrite={canWrite}
          onEdit={onEdit}
          onArchive={onArchive}
        />
      ) : null}
    </>
  );
}

function RelationList({
  items,
  canWrite,
  onEdit,
  onArchive,
}: {
  items: AdminRelationView[];
  canWrite: boolean;
  onEdit: (item: AdminRelationView) => void;
  onArchive: (item: AdminRelationView) => void;
}) {
  return (
    <ul className="catalog-resource__list">
      {items.map((item) => (
        <li key={item.id}>
          <div>
            <strong>{item.title.ru}</strong>
            <span>
              {item.type} · версия {item.version}
            </span>
            <small>
              {item.sourceEntityId} → {item.targetEntityId}
            </small>
          </div>
          {canWrite ? (
            <div className="catalog-actions">
              <button
                type="button"
                aria-label={`Изменить ${item.title.ru}`}
                disabled={item.status === "archived"}
                onClick={() => {
                  onEdit(item);
                }}
              >
                Изменить
              </button>
              <button
                type="button"
                aria-label={`Архивировать ${item.title.ru}`}
                disabled={item.status === "archived"}
                onClick={() => {
                  onArchive(item);
                }}
              >
                Архивировать
              </button>
            </div>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
