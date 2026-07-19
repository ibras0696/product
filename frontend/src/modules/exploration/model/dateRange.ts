export const EXPLORER_MIN_YEAR = 1000;
export const EXPLORER_MAX_YEAR = new Date().getFullYear();

export interface ExplorerDateRange {
  from: number | null;
  to: number | null;
}

export function parseExplorerYear(value: string | null): number | null {
  if (!value || !/^\d{4}$/.test(value)) return null;
  const year = Number(value);
  return year >= EXPLORER_MIN_YEAR && year <= EXPLORER_MAX_YEAR ? year : null;
}

export function dateRangeLabel({ from, to }: ExplorerDateRange): string {
  if (from === null && to === null) return "Весь период";
  if (from === null) return `До ${String(to)}`;
  if (to === null) return `После ${String(from)}`;
  if (from === to) return String(from);
  return `${String(from)}-${String(to)}`;
}

export function sliderYear(value: number | null, boundary: "min" | "max") {
  if (value === null) {
    return boundary === "min" ? EXPLORER_MIN_YEAR : EXPLORER_MAX_YEAR;
  }
  return Math.min(Math.max(value, EXPLORER_MIN_YEAR), EXPLORER_MAX_YEAR);
}
