import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { explorationApi } from "../api/explorationApi";
import type { GraphViewModel } from "../api/viewModels";
import { EntityRelationTree } from "./EntityRelationTree";

const graph: GraphViewModel = {
  center: {
    id: "center",
    type: "settlement",
    title: { ru: "Центр", ce: null },
  },
  nodes: [
    {
      id: "first",
      type: "person",
      title: { ru: "Первый уровень", ce: null },
      relations_count: 2,
    },
    {
      id: "second",
      type: "event",
      title: { ru: "Второй уровень", ce: null },
      relations_count: 1,
    },
  ],
  edges: [
    {
      id: "edge-first",
      source_id: "center",
      target_id: "first",
      type: "connected_with",
      title: { ru: "связан", ce: null },
      description: { ru: "", ce: null },
      sources_count: 1,
    },
    {
      id: "edge-second",
      source_id: "first",
      target_id: "second",
      type: "participated_in",
      title: { ru: "участвовал", ce: null },
      description: { ru: "", ce: null },
      sources_count: 1,
    },
  ],
  hidden_nodes_count: 0,
};

it("loads evidence for a second-level relation only when requested", async () => {
  const user = userEvent.setup();
  const getSources = vi
    .spyOn(explorationApi, "getRelationSources")
    .mockResolvedValue({
      items: [],
      meta: { limit: 20, offset: 0, total: 0 },
    });
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <EntityRelationTree graph={graph} pending={false} onOpen={vi.fn()} />
    </QueryClientProvider>,
  );

  await user.click(
    screen.getByRole("button", { name: "Показать подтверждение связи" }),
  );
  await user.click(
    screen.getByRole("button", {
      name: "Показать источник связи второго уровня: Второй уровень",
    }),
  );

  expect(getSources).toHaveBeenCalledWith(
    "edge-second",
    expect.any(AbortSignal),
  );
});
