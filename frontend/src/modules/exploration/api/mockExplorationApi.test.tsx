import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, vi } from "vitest";

import { explorationApi } from "./explorationApi";
import { explorationQueryKeys, useMapEntities } from "./explorationQueries";
import { districtIds } from "./mockCatalogData";
import { ExplorationMockError, mockExplorationApi } from "./mockExplorationApi";

function activeSignal() {
  return new AbortController().signal;
}

afterEach(() => {
  vi.restoreAllMocks();
});

it("filters the bounded map by normalized query, type, district and period", async () => {
  const result = await mockExplorationApi.getMapEntities(
    {
      query: "  ГРОЗНЫЙ ",
      types: ["settlement", "settlement"],
      districtId: districtIds.central,
      periodFrom: 1800,
      periodTo: 1900,
      limit: 10,
    },
    activeSignal(),
  );

  expect(result).toMatchObject({
    truncated: false,
    items: [
      {
        id: "10000000-0000-4000-8000-000000000001",
        entityType: "settlement",
        name: "Грозный",
      },
    ],
  });

  const truncated = await mockExplorationApi.getMapEntities(
    { districtId: districtIds.central, limit: 1 },
    activeSignal(),
  );
  expect(truncated.items).toHaveLength(1);
  expect(truncated.truncated).toBe(true);
});

it("returns deterministic empty, error and aborted outcomes", async () => {
  await expect(
    mockExplorationApi.getMapEntities({}, activeSignal(), "empty"),
  ).resolves.toEqual({
    items: [],
    relations: [],
    truncated: false,
    relationsTruncated: false,
  });
  await expect(
    mockExplorationApi.getCatalogOptions(activeSignal(), "error"),
  ).rejects.toBeInstanceOf(ExplorationMockError);

  const controller = new AbortController();
  controller.abort();
  await expect(
    mockExplorationApi.search({ query: "Грозный" }, controller.signal),
  ).rejects.toMatchObject({ name: "AbortError" });
});

it("searches with bounded pagination and keeps normalized server state in Query", async () => {
  vi.spyOn(explorationApi, "getMapEntities").mockImplementation(
    (filters, signal) => mockExplorationApi.getMapEntities(filters, signal),
  );
  const search = await mockExplorationApi.search(
    {
      query: "  АРГУН ",
      types: ["settlement"],
      districtId: districtIds.central,
      limit: 1,
    },
    activeSignal(),
  );
  expect(search).toMatchObject({
    items: [
      {
        id: "10000000-0000-4000-8000-000000000009",
        title: { ru: "Аргун", ce: null },
      },
    ],
    meta: { limit: 1, offset: 0, total: 1 },
  });

  expect(
    explorationQueryKeys.map({
      query: " грозный ",
      types: ["settlement", "settlement"],
    }),
  ).toEqual(
    explorationQueryKeys.map({ query: "ГРОЗНЫЙ", types: ["settlement"] }),
  );

  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  const { result } = renderHook(() => useMapEntities({ query: "Грозный" }), {
    wrapper,
  });

  await waitFor(() => {
    expect(result.current.isSuccess).toBe(true);
  });
  expect(result.current.data?.items[0]?.name).toBe("Грозный");
});
