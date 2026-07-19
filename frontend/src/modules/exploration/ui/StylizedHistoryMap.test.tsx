import { render } from "@testing-library/react";
import { vi } from "vitest";

import { StylizedHistoryMap } from "./StylizedHistoryMap";

it("dims only the surroundings outside the real boundary in fallback mode", () => {
  const { container } = render(
    <StylizedHistoryMap
      entities={[]}
      relations={[]}
      selectedId=""
      focusEntityId={null}
      onSelect={vi.fn()}
      onFocusRestored={vi.fn()}
    />,
  );

  const mask = container.querySelector(".hx-artmap-outside-mask");
  expect(mask).toHaveAttribute("fill-rule", "evenodd");
  expect(mask?.getAttribute("d")).toContain("M 0 0 H");
});
