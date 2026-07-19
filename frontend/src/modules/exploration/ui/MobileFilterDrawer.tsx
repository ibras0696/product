import { useEffect, useRef, type KeyboardEvent, type RefObject } from "react";

import type {
  CatalogEntityType,
  CatalogOptionsViewModel,
  ResearchStatus,
} from "../api/viewModels";
import type { ExplorerDateRange } from "../model/dateRange";
import type { EntityKind } from "../model/historyData";
import { ExplorerDateRange as ExplorerDateRangeControl } from "./ExplorerDateRange";
import { researchStatusLabels } from "./researchStatusLabels";

export interface PresentedFilterType {
  id: CatalogEntityType;
  label: string;
  kind: EntityKind;
}

export interface ExplorerFilterProps {
  activeTypes: Set<CatalogEntityType>;
  activeResearchStatuses: Set<ResearchStatus>;
  districtId: string | null;
  dateRange: ExplorerDateRange;
  options?: CatalogOptionsViewModel;
  presentedTypes: PresentedFilterType[];
  onTypeToggle: (type: CatalogEntityType) => void;
  onResearchStatusToggle: (status: ResearchStatus) => void;
  onDistrictChange: (id: string | null) => void;
  onDateRangeChange: (range: ExplorerDateRange) => void;
  onReset: () => void;
}

interface FilterSelectProps {
  label: string;
  value: string | null;
  allLabel: string;
  options: Array<{ id: string; title: { ru: string } }>;
  onChange: (value: string | null) => void;
}

function FilterSelect(props: FilterSelectProps) {
  return (
    <label className="hx-filter-select">
      <span>{props.label}</span>
      <select
        value={props.value ?? ""}
        onChange={(event) => {
          props.onChange(event.target.value || null);
        }}
      >
        <option value="">{props.allLabel}</option>
        {props.options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.title.ru}
          </option>
        ))}
      </select>
    </label>
  );
}

export function ExplorerFilterControls(props: ExplorerFilterProps) {
  return (
    <div className="hx-filter-block">
      <div className="hx-filter-heading">
        <p>Фильтры</p>
        <button type="button" onClick={props.onReset}>
          Сбросить
        </button>
      </div>
      <div className="hx-filter-list" role="group" aria-label="Типы объектов">
        {props.presentedTypes.map((type) => (
          <button
            key={type.id}
            type="button"
            className={`hx-kind-${type.kind}`}
            aria-pressed={props.activeTypes.has(type.id)}
            onClick={() => {
              props.onTypeToggle(type.id);
            }}
          >
            <span className="hx-kind-dot" aria-hidden="true" />
            {type.label}
          </button>
        ))}
      </div>
      <fieldset className="hx-status-filter">
        <legend>Статус исследования</legend>
        <div role="group" aria-label="Статусы исследования">
          {(props.options?.researchStatuses ?? []).map((status) => (
            <button
              key={status}
              type="button"
              aria-pressed={props.activeResearchStatuses.has(status)}
              onClick={() => props.onResearchStatusToggle(status)}
            >
              {researchStatusLabels[status]}
            </button>
          ))}
        </div>
      </fieldset>
      <FilterSelect
        label="Район"
        value={props.districtId}
        allLabel="Все районы"
        options={props.options?.districts ?? []}
        onChange={props.onDistrictChange}
      />
      <ExplorerDateRangeControl
        value={props.dateRange}
        onChange={props.onDateRangeChange}
      />
    </div>
  );
}

interface MobileFilterDrawerProps extends ExplorerFilterProps {
  open: boolean;
  onClose: () => void;
  triggerRef: RefObject<HTMLButtonElement | null>;
}

const focusableSelector = [
  "button:not([disabled])",
  "select:not([disabled])",
  "input:not([disabled])",
  "[href]",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

function trapTabFocus(
  event: KeyboardEvent<HTMLElement>,
  dialog: HTMLElement | null,
) {
  const focusable = Array.from(
    dialog?.querySelectorAll<HTMLElement>(focusableSelector) ?? [],
  );
  const first = focusable[0];
  const last = focusable.at(-1);
  if (!last) return;
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

export function MobileFilterDrawer(props: MobileFilterDrawerProps) {
  const dialogRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!props.open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();
    return () => {
      document.body.style.overflow = previousOverflow;
      props.triggerRef.current?.focus();
    };
  }, [props.open, props.triggerRef]);

  function handleKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      props.onClose();
      return;
    }
    if (event.key !== "Tab") return;
    trapTabFocus(event, dialogRef.current);
  }

  if (!props.open) return null;
  return (
    <div
      className="hx-filter-overlay"
      onPointerDown={(event) => {
        if (event.target === event.currentTarget) props.onClose();
      }}
    >
      <section
        ref={dialogRef}
        className="hx-filter-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="mobile-filter-title"
        onKeyDown={handleKeyDown}
      >
        <header className="hx-filter-sheet-header">
          <div>
            <span>Настройка карты</span>
            <h2 id="mobile-filter-title">Фильтры</h2>
          </div>
          <button ref={closeRef} type="button" onClick={props.onClose}>
            Закрыть
          </button>
        </header>
        <ExplorerFilterControls {...props} />
        <button
          type="button"
          className="hx-filter-apply"
          onClick={props.onClose}
        >
          Показать результаты
        </button>
      </section>
    </div>
  );
}
