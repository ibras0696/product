import { entityIds, mapEntities, mapRelations } from "../model/historyData";
import { chechnyaMaskGeoJson } from "../model/chechnyaBoundary";
import { chechnyaOutsideMaskLayer, createRelationGeoJson } from "./mapGeoData";
import { createMarkerLayout } from "./markerLayout";

function groupsFor(entities = mapEntities, zoom = 10) {
  return createMarkerLayout(entities, "", zoom, ([longitude, latitude]) => ({
    x: longitude * 100,
    y: latitude * 100,
  }));
}

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
    groupsFor(),
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
  const result = createRelationGeoJson(groupsFor(), [], entityIds.argun);

  expect(result.features).toEqual([]);
});

it("creates lines only when both runtime relation endpoints are on the map", () => {
  const visibleEntities = mapEntities.filter(
    (entity) => entity.id === entityIds.argun || entity.id === entityIds.grozny,
  );
  const result = createRelationGeoJson(
    groupsFor(visibleEntities),
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

it("aggregates visible cluster connections and reveals internal links after groups split", () => {
  const entities = mapEntities.slice(0, 3);
  const [first, second, third] = entities;
  const relations = [
    { from: first.id, to: third.id },
    { from: second.id, to: third.id },
    { from: third.id, to: first.id },
    { from: first.id, to: second.id },
  ];
  const clustered = createMarkerLayout(entities, "", 6, (coordinates) => ({
    x: coordinates === third.coordinates ? 500 : 100,
    y: 100,
  }));
  const overview = createRelationGeoJson(clustered, relations, first.id);
  expect(overview.features).toHaveLength(1);
  expect(overview.features[0]?.properties.relationCount).toBe(3);

  const detailed = createMarkerLayout(entities, "", 11, ([longitude]) => ({
    x: longitude * 10_000,
    y: 100,
  }));
  expect(
    createRelationGeoJson(detailed, relations, first.id).features.length,
  ).toBeGreaterThan(overview.features.length);
});
