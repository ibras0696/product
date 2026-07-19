import type {
  AdminEntityStatus,
  AdminEntityType,
  EntityListFilters,
} from "../domain/catalog";

const types = new Set<AdminEntityType>([
  "settlement",
  "person",
  "event",
  "landmark",
  "natural_object",
  "cultural_object",
  "organization",
  "university_object",
  "artifact",
]);
const statuses = new Set<AdminEntityStatus>(["draft", "published", "archived"]);

export function catalogFiltersFromUrl(
  params: URLSearchParams,
): EntityListFilters {
  const type = params.get("type") as AdminEntityType | null;
  const status = params.get("status") as AdminEntityStatus | null;
  const page = Math.max(Number.parseInt(params.get("page") ?? "1", 10) || 1, 1);
  return {
    query: params.get("query")?.trim() || undefined,
    type: type && types.has(type) ? type : undefined,
    status: status && statuses.has(status) ? status : undefined,
    limit: 10,
    offset: (page - 1) * 10,
  };
}

export function updateCatalogUrl(
  current: URLSearchParams,
  values: Record<string, string>,
) {
  const next = new URLSearchParams(current);
  Object.entries(values).forEach(([key, value]) => {
    if (value) next.set(key, value);
    else next.delete(key);
  });
  next.delete("page");
  return next;
}
