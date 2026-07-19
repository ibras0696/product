import type { MapEntity, Relation } from "../model/historyData";

export const chechnyaOutsideMaskLayer = {
  id: "chechnya-outside-mask",
  type: "fill" as const,
  source: "chechnya-mask",
  paint: { "fill-color": "#02080b", "fill-opacity": 0.3 },
};

export function createRelationGeoJson(
  entities: MapEntity[],
  relations: Relation[],
  selectedId: string,
) {
  const entitiesById = new Map(entities.map((entity) => [entity.id, entity]));
  return {
    type: "FeatureCollection" as const,
    features: relations.flatMap((relation) => {
      const source = entitiesById.get(relation.from);
      const target = entitiesById.get(relation.to);
      if (!source || !target) return [];
      return [
        {
          type: "Feature" as const,
          properties: {
            connected:
              relation.from === selectedId || relation.to === selectedId,
          },
          geometry: {
            type: "LineString" as const,
            coordinates: [[...source.coordinates], [...target.coordinates]],
          },
        },
      ];
    }),
  };
}
