import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MapStage } from "./MapStage";

vi.mock("./InteractiveHistoryMap", () => ({
  InteractiveHistoryMap: () => (
    <div aria-label="Базовая карта Чечни" data-testid="history-map" />
  ),
}));

const actions = {
  onSelect: vi.fn(),
  onRetry: vi.fn(),
  onReset: vi.fn(),
  onFocusRestored: vi.fn(),
};

describe("MapStage", () => {
  it.each(["loading", "error", "ready"] as const)(
    "keeps the base map visible in the %s state without entities",
    (status) => {
      render(
        <MapStage
          {...actions}
          entities={[]}
          relations={[]}
          selectedId=""
          focusEntityId={null}
          view="map"
          status={status}
          truncated={false}
          relationsTruncated={false}
        />,
      );

      expect(screen.getByTestId("history-map")).toBeVisible();
    },
  );
});
