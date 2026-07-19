import { entityIds, mapEntities, type MapEntity } from "../model/historyData";
import { createMarkerLayout } from "./markerLayout";

it("clusters dense map points and progressively reveals individual markers after zoom", () => {
  const entities = mapEntities.slice(0, 5);
  const denseProjection = () => ({ x: 100, y: 100 });

  const overview = createMarkerLayout(
    entities,
    entityIds.grozny,
    7.5,
    denseProjection,
  );
  expect(overview).toHaveLength(2);
  expect(overview.map((group) => group.entities.length).sort()).toEqual([1, 4]);
  expect(
    overview.find((group) => group.entities[0]?.id === entityIds.grozny)
      ?.showLabel,
  ).toBe(true);

  const detailed = createMarkerLayout(
    entities,
    entityIds.grozny,
    10.2,
    (coordinates) => ({
      x: coordinates[0] * 10_000,
      y: coordinates[1] * 10_000,
    }),
  );
  expect(detailed).toHaveLength(5);
  expect(detailed.every((group) => group.showLabel)).toBe(true);
});

it("keeps semantic satellites compact in overview and expands them on detail zoom", () => {
  const anchor = mapEntities[0];
  const satellites: MapEntity[] = Array.from({ length: 40 }, (_, index) => ({
    ...anchor,
    id: `satellite-${String(index)}`,
    name: `Спутник ${String(index)}`,
    virtualAnchorId: anchor.id,
  }));
  const project = ([x, y]: readonly [number, number]) => ({ x, y });
  const unproject = ({ x, y }: { x: number; y: number }) => [x, y] as const;
  const extent = (zoom: number) =>
    Math.max(
      ...createMarkerLayout(
        [anchor, ...satellites],
        "",
        zoom,
        project,
        unproject,
      ).map((group) =>
        Math.hypot(
          group.coordinates[0] - anchor.coordinates[0],
          group.coordinates[1] - anchor.coordinates[1],
        ),
      ),
    );

  expect(extent(6)).toBeLessThan(extent(9));
  expect(extent(6)).toBeLessThanOrEqual(90);
});
