import { useQuery } from "@tanstack/react-query";

import { explorationApi } from "./explorationApi";
import { normalizeTimelineFilters } from "./timelineFilters";
import type { TimelineFilters } from "./timelineViewModels";

export const timelineQueryKeys = {
  events: (filters: TimelineFilters) =>
    ["exploration", "timeline", normalizeTimelineFilters(filters)] as const,
};

export function useTimelineEvents(filters: TimelineFilters, enabled = true) {
  return useQuery({
    queryKey: timelineQueryKeys.events(filters),
    queryFn: ({ signal }) => explorationApi.getTimelineEvents(filters, signal),
    enabled,
  });
}
