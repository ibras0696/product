import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import {
  AdminCatalogError,
  type AdminEntityView,
  type BoundedPage,
} from "../domain/catalog";

interface CatalogEntityListProps {
  page?: BoundedPage<AdminEntityView>;
  pending: boolean;
  error: Error | null;
  canWrite: boolean;
  onCreate: () => void;
  onEdit: (entity: AdminEntityView) => void;
  onArchive: (entity: AdminEntityView) => Promise<void>;
}

function setPage(current: URLSearchParams, page: number) {
  const next = new URLSearchParams(current);
  next.set("page", String(page));
  return next;
}

function ListState({
  pending,
  error,
  empty,
}: {
  pending: boolean;
  error: Error | null;
  empty: boolean;
}) {
  if (pending) return <p role="status">Загружаем каталог…</p>;
  if (error instanceof AdminCatalogError && error.code === "unauthorized")
    return <p role="alert">Сессия завершилась. Войдите снова.</p>;
  if (error instanceof AdminCatalogError && error.code === "forbidden")
    return <p role="alert">Недостаточно прав для просмотра каталога.</p>;
  if (error) return <p role="alert">Не удалось загрузить каталог.</p>;
  if (empty) return <p>По этим фильтрам ничего не найдено.</p>;
  return null;
}

function archiveMessage(error: unknown) {
  if (!(error instanceof AdminCatalogError))
    return "Не удалось архивировать запись. Обновите список.";
  const messages: Partial<Record<AdminCatalogError["code"], string>> = {
    conflict: "Запись уже изменена. Обновите список перед архивацией.",
    unauthorized: "Сессия завершилась. Войдите снова.",
    forbidden: "Недостаточно прав для архивации.",
  };
  return (
    messages[error.code] ?? "Не удалось архивировать запись. Обновите список."
  );
}

export function CatalogEntityList(props: CatalogEntityListProps) {
  const [params, setParams] = useSearchParams();
  const [archiveError, setArchiveError] = useState<string | null>(null);
  const pageNumber = Math.max(
    Number.parseInt(params.get("page") ?? "1", 10) || 1,
    1,
  );
  function archive(entity: AdminEntityView) {
    if (!window.confirm(`Архивировать «${entity.title.ru}»?`)) return;
    setArchiveError(null);
    void props.onArchive(entity).catch((error: unknown) => {
      setArchiveError(archiveMessage(error));
    });
  }
  return (
    <section aria-labelledby="catalog-list-title">
      <div className="catalog-heading">
        <h2 id="catalog-list-title">Сущности</h2>
        {props.canWrite ? (
          <button
            type="button"
            onClick={() => {
              props.onCreate();
            }}
          >
            Добавить
          </button>
        ) : (
          <span>Только чтение</span>
        )}
      </div>
      {archiveError ? <p role="alert">{archiveError}</p> : null}
      <ListState
        pending={props.pending}
        error={props.error}
        empty={props.page?.items.length === 0}
      />
      {props.page ? (
        <EntityTable
          items={props.page.items}
          canWrite={props.canWrite}
          onEdit={props.onEdit}
          onArchive={archive}
        />
      ) : null}
      {props.page ? (
        <nav className="catalog-pagination" aria-label="Страницы каталога">
          <button
            type="button"
            disabled={pageNumber <= 1}
            onClick={() => {
              setParams((current) => setPage(current, pageNumber - 1));
            }}
          >
            Назад
          </button>
          <span>Страница {String(pageNumber)}</span>
          <button
            type="button"
            disabled={
              pageNumber * props.page.meta.limit >= props.page.meta.total
            }
            onClick={() => {
              setParams((current) => setPage(current, pageNumber + 1));
            }}
          >
            Дальше
          </button>
        </nav>
      ) : null}
    </section>
  );
}

interface EntityTableProps {
  items: AdminEntityView[];
  canWrite: boolean;
  onEdit: (entity: AdminEntityView) => void;
  onArchive: (entity: AdminEntityView) => void;
}

function EntityTable({ items, canWrite, onEdit, onArchive }: EntityTableProps) {
  return (
    <div className="catalog-table-wrap">
      <table>
        <caption className="sr-only">Сущности каталога</caption>
        <thead>
          <tr>
            <th scope="col">Название</th>
            <th scope="col">Тип</th>
            <th scope="col">Статус</th>
            <th scope="col">Версия</th>
            <th scope="col">Действия</th>
          </tr>
        </thead>
        <tbody>
          {items.map((entity) => (
            <tr key={entity.id}>
              <th scope="row">
                <strong>{entity.title.ru}</strong>
                <small>{entity.slug}</small>
              </th>
              <td data-label="Тип">{entity.type}</td>
              <td data-label="Статус">{entity.status}</td>
              <td data-label="Версия">{entity.version}</td>
              <td data-label="Действия">
                <div className="catalog-actions">
                  <button
                    type="button"
                    disabled={!canWrite || entity.status === "archived"}
                    onClick={() => {
                      onEdit(entity);
                    }}
                  >
                    Изменить {entity.title.ru}
                  </button>
                  <button
                    type="button"
                    disabled={!canWrite || entity.status === "archived"}
                    onClick={() => {
                      onArchive(entity);
                    }}
                  >
                    Архивировать {entity.title.ru}
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
