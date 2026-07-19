import type { CSSProperties, ChangeEvent } from "react";

import {
  dateRangeLabel,
  EXPLORER_MAX_YEAR,
  EXPLORER_MIN_YEAR,
  sliderYear,
  type ExplorerDateRange,
} from "../model/dateRange";

interface ExplorerDateRangeProps {
  value: ExplorerDateRange;
  onChange: (value: ExplorerDateRange) => void;
}

function handleFromChange(
  event: ChangeEvent<HTMLInputElement>,
  value: ExplorerDateRange,
  onChange: ExplorerDateRangeProps["onChange"],
) {
  const next = Number(event.target.value);
  const upper = sliderYear(value.to, "max");
  const from = Math.min(next, upper);
  onChange({ from: from === EXPLORER_MIN_YEAR ? null : from, to: value.to });
}

function handleToChange(
  event: ChangeEvent<HTMLInputElement>,
  value: ExplorerDateRange,
  onChange: ExplorerDateRangeProps["onChange"],
) {
  const next = Number(event.target.value);
  const lower = sliderYear(value.from, "min");
  const to = Math.max(next, lower);
  onChange({ from: value.from, to: to === EXPLORER_MAX_YEAR ? null : to });
}

export function ExplorerDateRange({ value, onChange }: ExplorerDateRangeProps) {
  const from = sliderYear(value.from, "min");
  const to = sliderYear(value.to, "max");
  const span = EXPLORER_MAX_YEAR - EXPLORER_MIN_YEAR;
  const top = ((EXPLORER_MAX_YEAR - to) / span) * 100;
  const bottom = ((from - EXPLORER_MIN_YEAR) / span) * 100;
  const selectionStyle: CSSProperties = {
    top: `${String(top)}%`,
    bottom: `${String(bottom)}%`,
  };

  return (
    <fieldset className="hx-date-filter">
      <legend>Диапазон дат</legend>
      <output aria-live="polite">{dateRangeLabel(value)}</output>
      <div className="hx-date-range-layout">
        <span aria-hidden="true">{EXPLORER_MAX_YEAR}</span>
        <div className="hx-date-range-track">
          <span className="hx-date-range-selection" style={selectionStyle} />
          <input
            type="range"
            min={EXPLORER_MIN_YEAR}
            max={EXPLORER_MAX_YEAR}
            value={from}
            aria-label="Начало периода"
            aria-valuetext={
              value.from === null ? "Без нижней границы" : String(value.from)
            }
            onChange={(event) => handleFromChange(event, value, onChange)}
          />
          <input
            type="range"
            min={EXPLORER_MIN_YEAR}
            max={EXPLORER_MAX_YEAR}
            value={to}
            aria-label="Конец периода"
            aria-valuetext={
              value.to === null ? "Без верхней границы" : String(value.to)
            }
            onChange={(event) => handleToChange(event, value, onChange)}
          />
        </div>
        <span aria-hidden="true">{EXPLORER_MIN_YEAR}</span>
      </div>
      <p>Крайние положения включают весь более ранний или поздний период.</p>
    </fieldset>
  );
}
