import type { TimelineFilters } from "./timelineViewModels";

export const TIMELINE_LIMIT = 100;

export function normalizeTimelineFilters(filters: TimelineFilters) {
  const query = filters.query?.trim() ?? "";
  return {
    query: query.length >= 2 && query.length <= 100 ? query : null,
    districtId: filters.districtId ?? null,
    periodFrom: filters.periodFrom ?? null,
    periodTo: filters.periodTo ?? null,
    limit: Math.min(
      Math.max(Math.trunc(filters.limit ?? TIMELINE_LIMIT), 1),
      TIMELINE_LIMIT,
    ),
    offset: Math.min(Math.max(Math.trunc(filters.offset ?? 0), 0), 1000),
  };
}
