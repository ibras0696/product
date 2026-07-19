interface ResourcePaginationProps {
  label: string;
  meta: { limit: number; offset: number; total: number };
  onOffsetChange: (offset: number) => void;
}

export function ResourcePagination({
  label,
  meta,
  onOffsetChange,
}: ResourcePaginationProps) {
  const pageCount = Math.max(Math.ceil(meta.total / meta.limit), 1);
  const page = Math.min(Math.floor(meta.offset / meta.limit) + 1, pageCount);
  const first = meta.total === 0 ? 0 : meta.offset + 1;
  const last = Math.min(meta.offset + meta.limit, meta.total);
  return (
    <nav className="catalog-pagination" aria-label={label}>
      <span className="catalog-pagination__summary">
        {String(first)}–{String(last)} из {String(meta.total)}
      </span>
      <div>
        <button
          type="button"
          disabled={meta.offset === 0}
          onClick={() => {
            onOffsetChange(Math.max(0, meta.offset - meta.limit));
          }}
        >
          Назад
        </button>
        <span>
          {String(page)} / {String(pageCount)}
        </span>
        <button
          type="button"
          disabled={meta.offset + meta.limit >= meta.total}
          onClick={() => {
            onOffsetChange(meta.offset + meta.limit);
          }}
        >
          Дальше
        </button>
      </div>
    </nav>
  );
}
