import { useState } from "react";
import { useForm, type UseFormReturn } from "react-hook-form";

import type { AdminCatalogPort } from "../api/adminCatalogPort";
import type {
  AdminCatalogPermissions,
  AdminSourceType,
  AdminSourceView,
  SourceInput,
  SourceListFilters,
} from "../domain/catalog";
import { useAdminSources, useSourceMutations } from "../model/catalogQueries";
import { resourceError } from "./resourceMessages";
import { ResourcePagination } from "./ResourcePagination";
import { SourceEditor } from "./SourceEditor";
import { sourceTypes } from "./sourceForm";

interface FilterValues {
  query: string;
  type: "" | AdminSourceType;
}

function sourceFilters(values: FilterValues): SourceListFilters {
  return {
    query: values.query.trim() || undefined,
    type: values.type || undefined,
    limit: 20,
    offset: 0,
  };
}

function SourcePagination({
  page,
  onOffsetChange,
}: {
  page: NonNullable<ReturnType<typeof useAdminSources>["data"]>;
  onOffsetChange: (offset: number) => void;
}) {
  return (
    <ResourcePagination
      label="Страницы источников"
      meta={page.meta}
      onOffsetChange={onOffsetChange}
    />
  );
}

export function SourcesPanel({
  port,
  permissions,
}: {
  port: AdminCatalogPort;
  permissions: AdminCatalogPermissions;
}) {
  const [filters, setFilters] = useState<SourceListFilters>({
    limit: 20,
    offset: 0,
  });
  const [editing, setEditing] = useState<AdminSourceView | "create" | null>(
    null,
  );
  const [actionError, setActionError] = useState<string | null>(null);
  const filterForm = useForm<FilterValues>({
    defaultValues: { query: "", type: "" },
  });
  const query = useAdminSources(port, permissions, filters);
  const mutations = useSourceMutations(port, permissions);
  const apply = filterForm.handleSubmit((values) => {
    setFilters(sourceFilters(values));
  });
  async function save(input: SourceInput) {
    if (editing === "create") await mutations.create.mutateAsync(input);
    else if (editing)
      await mutations.update.mutateAsync({ source: editing, input });
    setEditing(null);
  }
  function archive(item: AdminSourceView) {
    if (!window.confirm(`Архивировать источник «${item.title}»?`)) return;
    setActionError(null);
    void mutations.archive.mutateAsync(item).catch((error: unknown) => {
      setActionError(resourceError(error, "Не удалось архивировать источник."));
    });
  }
  return (
    <section className="catalog-resource" aria-labelledby="sources-title">
      <div className="catalog-heading">
        <h2 id="sources-title">Источники</h2>
        {permissions.write ? (
          <button
            type="button"
            onClick={() => {
              setEditing("create");
            }}
          >
            Добавить источник
          </button>
        ) : (
          <span>Только чтение</span>
        )}
      </div>
      <SourceFilters form={filterForm} onApply={apply} />
      <SourceQueryState
        actionError={actionError}
        query={query}
        canWrite={permissions.write}
        onEdit={setEditing}
        onArchive={archive}
      />
      {query.data ? (
        <SourcePagination
          page={query.data}
          onOffsetChange={(offset) => {
            setFilters((current) => ({ ...current, offset }));
          }}
        />
      ) : null}
      <SourceEditorPanel
        editing={editing}
        onSave={save}
        onCancel={() => {
          setEditing(null);
        }}
      />
      <SourceLinkingNotice />
    </section>
  );
}

function SourceLinkingNotice() {
  return (
    <aside
      className="catalog-contract-gap"
      aria-label="Ограничение привязки источников"
    >
      <strong>Привязка к сущности или связи пока недоступна.</strong>
      <p>
        В текущем admin OpenAPI нет link/unlink endpoint. CRUD источника
        работает независимо.
      </p>
    </aside>
  );
}

function SourceEditorPanel({
  editing,
  onSave,
  onCancel,
}: {
  editing: AdminSourceView | "create" | null;
  onSave: (input: SourceInput) => Promise<void>;
  onCancel: () => void;
}) {
  if (!editing) return null;
  const source = editing === "create" ? null : editing;
  const key = source ? `${source.id}-${String(source.version)}` : "create";
  return (
    <SourceEditor
      key={key}
      source={source}
      onSave={onSave}
      onCancel={onCancel}
    />
  );
}

function SourceFilters({
  form,
  onApply,
}: {
  form: UseFormReturn<FilterValues>;
  onApply: ReturnType<UseFormReturn<FilterValues>["handleSubmit"]>;
}) {
  return (
    <form
      className="catalog-resource__filters"
      aria-label="Фильтры источников"
      onSubmit={(event) => {
        void onApply(event);
      }}
    >
      <label>
        Поиск
        <input {...form.register("query")} />
      </label>
      <label>
        Тип источника
        <select {...form.register("type")}>
          <option value="">Все</option>
          {sourceTypes.map((type) => (
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

function SourceQueryState({
  actionError,
  query,
  canWrite,
  onEdit,
  onArchive,
}: {
  actionError: string | null;
  query: ReturnType<typeof useAdminSources>;
  canWrite: boolean;
  onEdit: (item: AdminSourceView | "create" | null) => void;
  onArchive: (item: AdminSourceView) => void;
}) {
  return (
    <>
      {actionError ? <p role="alert">{actionError}</p> : null}
      {query.isPending ? <p role="status">Загружаем источники…</p> : null}
      {query.isError ? (
        <p role="alert">
          {resourceError(query.error, "Не удалось загрузить источники.")}
        </p>
      ) : null}
      {query.data?.items.length === 0 ? (
        <p>Источников по этим фильтрам нет.</p>
      ) : null}
      {query.data ? (
        <SourceList
          items={query.data.items}
          canWrite={canWrite}
          onEdit={onEdit}
          onArchive={onArchive}
        />
      ) : null}
    </>
  );
}

function SourceList({
  items,
  canWrite,
  onEdit,
  onArchive,
}: {
  items: AdminSourceView[];
  canWrite: boolean;
  onEdit: (item: AdminSourceView) => void;
  onArchive: (item: AdminSourceView) => void;
}) {
  return (
    <ul className="catalog-resource__list">
      {items.map((item) => (
        <li key={item.id}>
          <div>
            <strong>{item.title}</strong>
            <span>
              {item.type} · версия {item.version}
            </span>
            <small>
              {item.isVerified ? "Проверен" : "Не проверен"} · {item.status}
            </small>
          </div>
          {canWrite ? (
            <div className="catalog-actions">
              <button
                type="button"
                aria-label={`Изменить ${item.title}`}
                disabled={item.status === "archived"}
                onClick={() => {
                  onEdit(item);
                }}
              >
                Изменить
              </button>
              <button
                type="button"
                aria-label={`Архивировать ${item.title}`}
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
