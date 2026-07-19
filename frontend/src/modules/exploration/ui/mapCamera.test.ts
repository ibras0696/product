import { describe, expect, it } from "vitest";

import {
  chechnyaBoundaryBounds,
  chechnyaNavigationBounds,
  chechnyaViewBounds,
  FALLBACK_MAP_MAX_SCALE,
  MAP_MAX_ZOOM,
  MAP_MIN_ZOOM,
  MAX_REGIONAL_SELECTION_ZOOM,
  regionalSelectionZoom,
} from "./mapCamera";

describe("regional map camera", () => {
  it("keeps the full Chechnya boundary in reset bounds and caps selection zoom", () => {
    expect(chechnyaViewBounds[0][0]).toBeLessThan(chechnyaBoundaryBounds[0][0]);
    expect(chechnyaViewBounds[0][1]).toBeLessThan(chechnyaBoundaryBounds[0][1]);
    expect(chechnyaViewBounds[1][0]).toBeGreaterThan(
      chechnyaBoundaryBounds[1][0],
    );
    expect(chechnyaViewBounds[1][1]).toBeGreaterThan(
      chechnyaBoundaryBounds[1][1],
    );
    expect(regionalSelectionZoom(12)).toBe(MAX_REGIONAL_SELECTION_ZOOM);
    expect(regionalSelectionZoom(7.4)).toBe(7.4);
    expect(chechnyaViewBounds[1][1]).toBeGreaterThan(44.01);
    expect(chechnyaNavigationBounds[1][1]).toBeGreaterThan(
      chechnyaViewBounds[1][1],
    );
    expect(chechnyaNavigationBounds[0][0]).toBeLessThan(43.2);
    expect(chechnyaNavigationBounds[1][0]).toBeGreaterThan(48.3);
    expect(MAP_MIN_ZOOM).toBe(4.3);
    expect(MAP_MAX_ZOOM).toBe(18);
    expect(FALLBACK_MAP_MAX_SCALE).toBeGreaterThan(4);
  });
});
