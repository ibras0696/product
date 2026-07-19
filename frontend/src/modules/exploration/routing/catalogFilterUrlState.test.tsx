import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, beforeEach, vi } from "vitest";

import { explorationApi } from "../api/explorationApi";
import { districtIds } from "../api/mockCatalogData";
import { mockExplorationApi } from "../api/mockExplorationApi";
import { useHistoryExplorerScreen } from "./useHistoryExplorerScreen";

function RoutingProbe() {
  const explorer = useHistoryExplorerScreen();
  const location = useLocation();
  return (
    <div>
      <output data-testid="search">{location.search}</output>
      <output data-testid="notice">
        {explorer.filterNotice?.message ?? "none"}
      </output>
      <output data-testid="entities">{explorer.entities.length}</output>
    </div>
  );
}

beforeEach(() => {
  vi.spyOn(explorationApi, "getMapEntities").mockImplementation(
    (filters, signal) => mockExplorationApi.getMapEntities(filters, signal),
  );
  vi.spyOn(explorationApi, "getCatalogOptions").mockImplementation((signal) =>
    mockExplorationApi.getCatalogOptions(signal),
  );
});

afterEach(() => {
  vi.restoreAllMocks();
});

function renderRoute(path: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <RoutingProbe />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

it("removes unknown catalog filters with a notice and preserves valid IDs", async () => {
  renderRoute(
    "/?district=unknown-district&period=unknown-period&types=settlement,unknown",
  );

  await waitFor(() => {
    expect(screen.getByTestId("search")).toHaveTextContent(
      "?types=settlement%2Cunknown",
    );
  });
  expect(screen.getByTestId("notice")).toHaveTextContent(
    "Неизвестные район и период удалены из фильтров.",
  );
  await waitFor(() => {
    expect(Number(screen.getByTestId("entities").textContent)).toBeGreaterThan(
      0,
    );
  });

  cleanup();
  const validPath = `/?district=${districtIds.central}&period=1800-1916`;
  renderRoute(validPath);

  await waitFor(() => {
    expect(Number(screen.getByTestId("entities").textContent)).toBeGreaterThan(
      0,
    );
  });
  expect(screen.getByTestId("search")).toHaveTextContent(
    `district=${districtIds.central}`,
  );
  expect(screen.getByTestId("search")).toHaveTextContent("period=1800-1916");
  expect(screen.getByTestId("notice")).toHaveTextContent("none");
});

it("keeps research status and direct dates in the URL-backed map request", async () => {
  renderRoute(
    "/?research_statuses=needs_review&period_from=1800&period_to=1950",
  );

  await waitFor(() => {
    expect(explorationApi.getMapEntities).toHaveBeenLastCalledWith(
      expect.objectContaining({
        researchStatuses: ["needs_review"],
        periodFrom: 1800,
        periodTo: 1950,
      }),
      expect.any(AbortSignal),
    );
  });
  const address = screen.getByTestId("search");
  expect(address).toHaveTextContent("research_statuses=needs_review");
  expect(address).toHaveTextContent("period_from=1800");
  expect(address).toHaveTextContent("period_to=1950");
});
