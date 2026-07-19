import {
  moderationStatuses,
  moderationSubmissionTypes,
  type ModerationFilters,
  type ModerationStatus,
  type ModerationSubmissionType,
} from "./types";

export const defaultModerationFilters: ModerationFilters = {
  status: "pending",
  type: null,
  settlementId: null,
  createdFrom: null,
  createdTo: null,
  limit: 10,
  offset: 0,
};

function enumValue<T extends string>(
  value: string | null,
  allowed: readonly T[],
): T | null {
  return value && allowed.includes(value as T) ? (value as T) : null;
}

function boundedInteger(
  value: string | null,
  fallback: number,
  min: number,
  max: number,
): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed)) return fallback;
  return Math.min(Math.max(parsed, min), max);
}

export function parseModerationFilters(
  params: URLSearchParams,
): ModerationFilters {
  return {
    status: enumValue<ModerationStatus>(
      params.get("status"),
      moderationStatuses,
    ),
    type: enumValue<ModerationSubmissionType>(
      params.get("type"),
      moderationSubmissionTypes,
    ),
    settlementId: params.get("settlement_id") || null,
    createdFrom: params.get("created_from") || null,
    createdTo: params.get("created_to") || null,
    limit: boundedInteger(params.get("limit"), 10, 1, 50),
    offset: boundedInteger(params.get("offset"), 0, 0, 1000),
  };
}

export function toModerationSearchParams(
  filters: ModerationFilters,
): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.type) params.set("type", filters.type);
  if (filters.settlementId) params.set("settlement_id", filters.settlementId);
  if (filters.createdFrom) params.set("created_from", filters.createdFrom);
  if (filters.createdTo) params.set("created_to", filters.createdTo);
  params.set("limit", String(Math.min(Math.max(filters.limit, 1), 50)));
  params.set("offset", String(Math.min(Math.max(filters.offset, 0), 1000)));
  return params;
}
