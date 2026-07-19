import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { InteractiveHistoryMap } from "./InteractiveHistoryMap";

const { useInteractiveMapEngine } = vi.hoisted(() => ({
  useInteractiveMapEngine: vi.fn(() => ({
    containerRef: { current: null },
    state: "unsupported" as const,
    zoomIn: vi.fn(),
    zoomOut: vi.fn(),
    fit: vi.fn(),
  })),
}));

vi.mock("./interactiveMapEngine", () => ({
  useInteractiveMapEngine,
}));

vi.mock("./StylizedHistoryMap", () => ({
  StylizedHistoryMap: () => <div aria-label="Резервная карта Чечни" />,
}));

it("shows a local map fallback when WebGL is unavailable", () => {
  render(
    <InteractiveHistoryMap
      entities={[]}
      relations={[]}
      selectedId=""
      focusEntityId={null}
      onSelect={vi.fn()}
      onFocusRestored={vi.fn()}
    />,
  );

  expect(screen.getByLabelText("Резервная карта Чечни")).toBeVisible();
});

it("passes only the supplied runtime relations to the map engine", () => {
  const relations = [{ from: "entity-a", to: "entity-b" }];

  const { rerender } = render(
    <InteractiveHistoryMap
      entities={[]}
      relations={relations}
      selectedId="entity-a"
      focusEntityId={null}
      onSelect={vi.fn()}
      onFocusRestored={vi.fn()}
    />,
  );

  expect(useInteractiveMapEngine).toHaveBeenLastCalledWith(
    expect.objectContaining({ relations }),
  );

  rerender(
    <InteractiveHistoryMap
      entities={[]}
      relations={[]}
      selectedId="entity-a"
      focusEntityId={null}
      onSelect={vi.fn()}
      onFocusRestored={vi.fn()}
    />,
  );

  expect(useInteractiveMapEngine).toHaveBeenLastCalledWith(
    expect.objectContaining({ relations: [] }),
  );
});
