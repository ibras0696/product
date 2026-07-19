import type {
  ModerationFilters,
  ModerationPage,
  ModerationQueueItem,
} from "../domain/types";
import { moderationTypeLabels } from "./labels";

interface Props {
  page: ModerationPage<ModerationQueueItem>;
  filters: ModerationFilters;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onFiltersChange: (filters: ModerationFilters) => void;
}

function OpenButton({
  item,
  onSelect,
}: {
  item: ModerationQueueItem;
  onSelect: (id: string) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => {
        onSelect(item.id);
      }}
    >
      Открыть
    </button>
  );
}

function QueueTable({
  items,
  selectedId,
  onSelect,
}: {
  items: ModerationQueueItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="mod-table-wrap">
      <table>
        <caption>Заявки, ожидающие модерации</caption>
        <thead>
          <tr>
            <th scope="col">Материал</th>
            <th scope="col">Тип</th>
            <th scope="col">Статус</th>
            <th scope="col">Версия</th>
            <th scope="col">Действие</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.id}
              aria-current={item.id === selectedId ? "true" : undefined}
            >
              <td>{item.title}</td>
              <td>{moderationTypeLabels[item.type]}</td>
              <td>
                <span className="mod-status">{item.status}</span>
              </td>
              <td>{item.version}</td>
              <td>
                <OpenButton item={item} onSelect={onSelect} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function QueueCards({
  items,
  selectedId,
  onSelect,
}: {
  items: ModerationQueueItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <ul className="mod-mobile-list" aria-label="Заявки, ожидающие модерации">
      {items.map((item) => (
        <li key={item.id}>
          <article aria-current={item.id === selectedId ? "true" : undefined}>
            <span className="mod-status">{item.status}</span>
            <h3>{item.title}</h3>
            <p>
              {moderationTypeLabels[item.type]} · версия {item.version}
            </p>
            <OpenButton item={item} onSelect={onSelect} />
          </article>
        </li>
      ))}
    </ul>
  );
}

export function ModerationQueue({
  page,
  filters,
  selectedId,
  onSelect,
  onFiltersChange,
}: Props) {
  if (page.items.length === 0)
    return <p className="mod-empty">По выбранным фильтрам заявок нет.</p>;
  const nextOffset = filters.offset + page.meta.limit;
  return (
    <section className="mod-queue" aria-labelledby="mod-queue-title">
      <div className="mod-section-heading">
        <h2 id="mod-queue-title">Очередь</h2>
        <span>{page.meta.total} заявок</span>
      </div>
      <QueueTable
        items={page.items}
        selectedId={selectedId}
        onSelect={onSelect}
      />
      <QueueCards
        items={page.items}
        selectedId={selectedId}
        onSelect={onSelect}
      />
      <nav className="mod-pagination" aria-label="Страницы очереди">
        <button
          type="button"
          disabled={filters.offset === 0}
          onClick={() => {
            onFiltersChange({
              ...filters,
              offset: Math.max(0, filters.offset - page.meta.limit),
            });
          }}
        >
          Назад
        </button>
        <button
          type="button"
          disabled={nextOffset >= page.meta.total}
          onClick={() => {
            onFiltersChange({ ...filters, offset: nextOffset });
          }}
        >
          Далее
        </button>
      </nav>
    </section>
  );
}
