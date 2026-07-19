import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import type {
  EntityDetailsViewModel,
  GraphViewModel,
  MapEntityViewModel,
} from "../api/viewModels";
import { ExplorerSupportingContent } from "./ExplorerSupportingContent";

const selectedId = "10000000-0000-4000-8000-000000000001";
const relatedId = "10000000-0000-4000-8000-000000000002";

const entity: MapEntityViewModel = {
  id: selectedId,
  entityType: "settlement",
  researchStatus: "verified",
  kind: "place",
  name: "Выбранный объект",
  title: { ru: "Выбранный объект", ce: null },
  districtId: "20000000-0000-4000-8000-000000000001",
  periodFrom: null,
  periodTo: null,
  coordinates: [45.7, 43.3],
  caption: "",
  subtitle: "",
  summary: "",
  image: "",
  description: "",
  x: 0,
  y: 0,
  stats: { relations: 4, heroes: 0, events: 0, landmarks: 0, sources: 0 },
};

const details: EntityDetailsViewModel = {
  id: selectedId,
  type: "settlement",
  slug: "selected-entity",
  title: { ru: "Название из API", ce: null },
  short_description: { ru: "Краткое описание из API", ce: null },
  full_description: { ru: "Полное описание из API", ce: null },
  coordinates: { latitude: 43.3, longitude: 45.7 },
  period_from: null,
  period_to: null,
  cover_url: null,
  relations_count: 7,
  sources_count: 3,
  media_count: 2,
  status: "published",
  research_status: "verified",
};

const graph: GraphViewModel = {
  center: {
    id: selectedId,
    type: "settlement",
    title: { ru: "Название из API", ce: null },
  },
  nodes: [
    {
      id: relatedId,
      type: "event",
      title: { ru: "Связанный объект", ce: null },
      relations_count: 5,
    },
  ],
  edges: [
    {
      id: "30000000-0000-4000-8000-000000000001",
      source_id: selectedId,
      target_id: relatedId,
      type: "connected_with",
      title: { ru: "Подтверждённая связь", ce: null },
      description: { ru: "Описание отношения из API", ce: null },
      sources_count: 2,
    },
  ],
  hidden_nodes_count: 1,
};

it("renders published details and graph data and opens a related UUID", async () => {
  const user = userEvent.setup();
  const onOpenEntity = vi.fn();
  render(
    <ExplorerSupportingContent
      entity={entity}
      details={details}
      graph={graph}
      graphPending={false}
      graphError={false}
      onOpenEntity={onOpenEntity}
    />,
  );

  expect(
    screen.getByRole("heading", { name: "Название из API" }),
  ).toBeVisible();
  expect(screen.getByText("Полное описание из API")).toBeVisible();
  expect(screen.getByLabelText("Данные объекта")).toHaveTextContent(
    "Связей7Источников3Медиа2",
  );
  expect(screen.getByText("Подтверждённая связь")).toBeVisible();
  expect(screen.getByText("Описание отношения из API")).toBeVisible();
  expect(screen.getByLabelText("Состав графа")).toHaveTextContent(
    "Скрыто объектов: 1",
  );

  await user.click(screen.getByRole("button", { name: /Связанный объект/ }));
  expect(onOpenEntity).toHaveBeenCalledOnce();
  expect(onOpenEntity).toHaveBeenCalledWith(relatedId);
});

it("exposes loading, error, and empty graph states", () => {
  const onOpenEntity = vi.fn();
  const view = render(
    <ExplorerSupportingContent
      entity={entity}
      graphPending
      graphError={false}
      onOpenEntity={onOpenEntity}
    />,
  );
  expect(screen.getByRole("status")).toHaveTextContent(
    "Загружаем подтверждённые связи",
  );

  view.rerender(
    <ExplorerSupportingContent
      entity={entity}
      graphPending={false}
      graphError
      onOpenEntity={onOpenEntity}
    />,
  );
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Не удалось загрузить связи объекта",
  );

  view.rerender(
    <ExplorerSupportingContent
      entity={entity}
      graph={{ ...graph, nodes: [], edges: [], hidden_nodes_count: 0 }}
      graphPending={false}
      graphError={false}
      onOpenEntity={onOpenEntity}
    />,
  );
  expect(screen.getByRole("status")).toHaveTextContent(
    "нет опубликованных связей",
  );
});
