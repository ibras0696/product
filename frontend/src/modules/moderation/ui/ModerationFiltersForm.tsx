import {
  moderationStatuses,
  moderationSubmissionTypes,
  type ModerationFilters,
} from "../domain/types";
import { moderationTypeLabels } from "./labels";

interface Props {
  filters: ModerationFilters;
  onChange: (filters: ModerationFilters) => void;
}

function FilterSelectors({ filters, onChange }: Props) {
  return (
    <>
      <label>
        <span>Статус</span>
        <select
          value={filters.status ?? ""}
          onChange={(event) => {
            onChange({
              ...filters,
              status: event.target.value
                ? (event.target.value as ModerationFilters["status"])
                : null,
              offset: 0,
            });
          }}
        >
          <option value="">Все статусы</option>
          {moderationStatuses.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Тип заявки</span>
        <select
          value={filters.type ?? ""}
          onChange={(event) => {
            onChange({
              ...filters,
              type: event.target.value
                ? (event.target.value as ModerationFilters["type"])
                : null,
              offset: 0,
            });
          }}
        >
          <option value="">Все типы</option>
          {moderationSubmissionTypes.map((type) => (
            <option key={type} value={type}>
              {moderationTypeLabels[type]}
            </option>
          ))}
        </select>
      </label>
    </>
  );
}

function DateFilter({
  label,
  value,
  suffix,
  onChange,
}: {
  label: string;
  value: string | null;
  suffix: string;
  onChange: (value: string | null) => void;
}) {
  return (
    <label>
      <span>{label}</span>
      <input
        type="date"
        value={value?.slice(0, 10) ?? ""}
        onChange={(event) => {
          onChange(
            event.target.value ? `${event.target.value}${suffix}` : null,
          );
        }}
      />
    </label>
  );
}

export function ModerationFiltersForm({ filters, onChange }: Props) {
  const patch = (value: Partial<ModerationFilters>) => {
    onChange({ ...filters, ...value, offset: 0 });
  };
  return (
    <section className="mod-filters" aria-labelledby="mod-filters-title">
      <h2 id="mod-filters-title">Фильтры очереди</h2>
      <div className="mod-filter-grid">
        <FilterSelectors filters={filters} onChange={onChange} />
        <label>
          <span>ID населённого пункта</span>
          <input
            value={filters.settlementId ?? ""}
            onChange={(event) => {
              patch({ settlementId: event.target.value || null });
            }}
          />
        </label>
        <DateFilter
          label="Создано с"
          value={filters.createdFrom}
          suffix="T00:00:00Z"
          onChange={(createdFrom) => {
            patch({ createdFrom });
          }}
        />
        <DateFilter
          label="Создано до"
          value={filters.createdTo}
          suffix="T23:59:59Z"
          onChange={(createdTo) => {
            patch({ createdTo });
          }}
        />
      </div>
    </section>
  );
}
