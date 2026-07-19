import { entityIds, mapEntities } from "../model/historyData";
import { createMarkerLayout } from "./markerLayout";

it("clusters dense map points while preserving the selected entity and declutters labels after zoom", () => {
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
    denseProjection,
  );
  expect(detailed).toHaveLength(5);
  expect(detailed.filter((group) => group.showLabel)).toHaveLength(1);
});
