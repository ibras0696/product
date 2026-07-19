import { entityIds, mapEntities, mapRelations } from "../model/historyData";
import { chechnyaMaskGeoJson } from "../model/chechnyaBoundary";
import { chechnyaOutsideMaskLayer, createRelationGeoJson } from "./mapGeoData";

it("defines an outside-only territory mask above raster with 30% opacity", () => {
  expect(chechnyaMaskGeoJson.geometry.coordinates).toHaveLength(2);
  expect(chechnyaOutsideMaskLayer).toMatchObject({
    id: "chechnya-outside-mask",
    type: "fill",
    source: "chechnya-mask",
    paint: { "fill-opacity": 0.3 },
  });
});

it("marks only relations connected to the selected map object as active", () => {
  const result = createRelationGeoJson(
    mapEntities,
    mapRelations,
    entityIds.argun,
  );
  const connected = result.features.filter(
    (feature) => feature.properties.connected,
  );
  expect(connected.length).toBeGreaterThan(0);
  expect(connected.length).toBeLessThan(result.features.length);
  expect(
    connected.every((feature) => feature.geometry.coordinates.length === 2),
  ).toBe(true);
});

it("does not create relation lines when the runtime payload is empty", () => {
  const result = createRelationGeoJson(mapEntities, [], entityIds.argun);

  expect(result.features).toEqual([]);
});

it("creates lines only when both runtime relation endpoints are on the map", () => {
  const visibleEntities = mapEntities.filter(
    (entity) => entity.id === entityIds.argun || entity.id === entityIds.grozny,
  );
  const result = createRelationGeoJson(
    visibleEntities,
    [
      { from: entityIds.argun, to: entityIds.grozny },
      { from: entityIds.argun, to: "entity-without-coordinates" },
    ],
    entityIds.argun,
  );

  expect(result.features).toHaveLength(1);
  expect(result.features[0]?.geometry.coordinates).toEqual([
    [
      ...(visibleEntities.find((entity) => entity.id === entityIds.argun)
        ?.coordinates ?? []),
    ],
    [
      ...(visibleEntities.find((entity) => entity.id === entityIds.grozny)
        ?.coordinates ?? []),
    ],
  ]);
});
