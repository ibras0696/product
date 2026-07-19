import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentProps } from "react";
import { vi } from "vitest";

import { explorationApi } from "../api/explorationApi";
import type { GraphViewModel } from "../api/viewModels";
import { NetworkStage } from "./NetworkStage";

const ids = {
  center: "10000000-0000-4000-8000-000000000001",
  levelOne: "10000000-0000-4000-8000-000000000002",
  levelTwo: "10000000-0000-4000-8000-000000000003",
  firstEdge: "30000000-0000-4000-8000-000000000001",
  secondEdge: "30000000-0000-4000-8000-000000000002",
};

const graph: GraphViewModel = {
  center: {
    id: ids.center,
    type: "settlement",
    title: { ru: "Грозный", ce: null },
  },
  nodes: [
    {
      id: ids.levelOne,
      type: "organization",
      title: { ru: "Чеченский государственный университет", ce: null },
      relations_count: 4,
    },
    {
      id: ids.levelTwo,
      type: "person",
      title: { ru: "Исследователь университета", ce: null },
      relations_count: 2,
    },
  ],
  edges: [
    {
      id: ids.firstEdge,
      source_id: ids.center,
      target_id: ids.levelOne,
      type: "connected_with_chgu",
      title: { ru: "Связь с ЧГУ", ce: null },
      description: { ru: "Университетская связь", ce: null },
      sources_count: 1,
    },
    {
      id: ids.secondEdge,
      source_id: ids.levelOne,
      target_id: ids.levelTwo,
      type: "studied_in",
      title: { ru: "Обучение в университете", ce: null },
      description: { ru: "Подтверждённое обучение", ce: null },
      sources_count: 2,
    },
  ],
  hidden_nodes_count: 7,
};

function renderStage(props: Partial<ComponentProps<typeof NetworkStage>> = {}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const defaults: ComponentProps<typeof NetworkStage> = {
    graph,
    selectedId: ids.center,
    status: "ready",
    onOpenEntity: vi.fn(),
    onRetry: vi.fn(),
    onReset: vi.fn(),
  };
  return {
    props: { ...defaults, ...props },
    ...render(
      <QueryClientProvider client={client}>
        <NetworkStage {...defaults} {...props} />
      </QueryClientProvider>,
    ),
  };
}

it("renders real depth-two branches, legend and exact relation evidence", async () => {
  const user = userEvent.setup();
  const getSources = vi
    .spyOn(explorationApi, "getRelationSources")
    .mockResolvedValue({
      items: [],
      meta: { limit: 20, offset: 0, total: 0 },
    });
  const { container } = renderStage();

  expect(
    screen.getByRole("heading", { name: "Паутина: Грозный" }),
  ).toBeVisible();
  expect(screen.getByText("Уровень 1 · связей: 4")).toBeVisible();
  expect(screen.getByText("Уровень 2 · связей: 2")).toBeVisible();
  expect(
    screen.getByText("За пределами лимита скрыто объектов: 7"),
  ).toBeVisible();
  expect(screen.getByText("Связан с ЧГУ")).toBeVisible();
  expect(screen.getByText("Учился в")).toBeVisible();
  expect(
    screen.getByRole("group", {
      name: "Визуальная паутина связей объекта Грозный",
    }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Грозный, уровень 0" }),
  ).toBeInTheDocument();
  expect(
    container.querySelector(".hx-network-edge.hx-network-line-studied_in"),
  ).toBeInTheDocument();

  const collapse = screen.getByRole("button", { name: "Свернуть ветвь" });
  collapse.focus();
  await user.keyboard("{Enter}");
  expect(screen.queryByText("Уровень 2 · связей: 2")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /Развернуть ветвь/ }));

  await user.click(
    screen.getByRole("button", { name: /Обучение в университете/ }),
  );
  await waitFor(() => {
    expect(getSources).toHaveBeenCalledWith(
      ids.secondEdge,
      expect.any(AbortSignal),
    );
  });
});

it("provides honest loading, error retry and empty states", async () => {
  const user = userEvent.setup();
  const retry = vi.fn();
  const { rerender } = renderStage({
    graph: undefined,
    status: "loading",
    onRetry: retry,
  });
  expect(screen.getByRole("status")).toHaveTextContent(
    "Загружаем паутину связей",
  );

  rerender(
    <QueryClientProvider client={new QueryClient()}>
      <NetworkStage
        graph={undefined}
        selectedId={ids.center}
        status="error"
        onOpenEntity={vi.fn()}
        onRetry={retry}
        onReset={vi.fn()}
      />
    </QueryClientProvider>,
  );
  await user.click(screen.getByRole("button", { name: "Повторить" }));
  expect(retry).toHaveBeenCalledOnce();

  rerender(
    <QueryClientProvider client={new QueryClient()}>
      <NetworkStage
        graph={{ ...graph, nodes: [], edges: [], hidden_nodes_count: 0 }}
        selectedId={ids.center}
        status="ready"
        onOpenEntity={vi.fn()}
        onRetry={retry}
        onReset={vi.fn()}
      />
    </QueryClientProvider>,
  );
  expect(screen.getByRole("status")).toHaveTextContent("Связей пока нет");
});

it("keeps every returned node readable in a scalable large graph", async () => {
  const user = userEvent.setup();
  const nodes = Array.from({ length: 18 }, (_, index) => ({
    id: `10000000-0000-4000-8000-${String(index + 10).padStart(12, "0")}`,
    type: "person" as const,
    title: { ru: `Участник ${String(index + 1)}`, ce: null },
    relations_count: 1,
  }));
  const largeGraph: GraphViewModel = {
    ...graph,
    nodes,
    edges: nodes.map((node, index) => ({
      id: `30000000-0000-4000-8000-${String(index + 10).padStart(12, "0")}`,
      source_id: ids.center,
      target_id: node.id,
      type: index % 2 === 0 ? "born_in" : "connected_with",
      title: { ru: "Подтверждённая связь", ce: null },
      description: { ru: "", ce: null },
      sources_count: 1,
    })),
    hidden_nodes_count: 23,
  };
  const { container } = renderStage({ graph: largeGraph });

  expect(
    screen.getAllByRole("button", { name: /Участник \d+, уровень 1/ }),
  ).toHaveLength(18);
  expect(container.querySelectorAll(".hx-network-edge")).toHaveLength(18);
  expect(
    container.querySelector(".hx-network-line-born_in"),
  ).toBeInTheDocument();
  expect(
    container.querySelector(".hx-network-line-connected_with"),
  ).toBeInTheDocument();
  expect(screen.queryByText(/не показано узлов/i)).not.toBeInTheDocument();
  expect(screen.getByText(/скрыто объектов: 23/)).toBeVisible();

  await user.click(screen.getByRole("button", { name: "Увеличить паутину" }));
  expect(screen.getByText("125%")).toBeVisible();
});
