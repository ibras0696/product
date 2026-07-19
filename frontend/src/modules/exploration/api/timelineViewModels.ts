export interface TimelineEventViewModel {
  id: string;
  title: string;
  shortDescription: string;
  periodFrom: number | null;
  periodTo: number | null;
  coordinates: { latitude: number; longitude: number } | null;
}

export interface TimelineEventsViewModel {
  items: TimelineEventViewModel[];
  meta: { limit: number; offset: number; total: number };
}

export interface TimelineFilters {
  query?: string;
  districtId?: string;
  periodFrom?: number;
  periodTo?: number;
  limit?: number;
  offset?: number;
}
