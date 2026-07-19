import type { Relation } from "../model/historyData";
import type { MarkerGroup } from "./markerLayout";

export const chechnyaOutsideMaskLayer = {
  id: "chechnya-outside-mask",
  type: "fill" as const,
  source: "chechnya-mask",
  paint: { "fill-color": "#02080b", "fill-opacity": 0.3 },
};

export function createRelationGeoJson(
  groups: MarkerGroup[],
  relations: Relation[],
  selectedId: string,
) {
  const groupsByEntity = new Map(
    groups.flatMap((group) =>
      group.entities.map((entity) => [entity.id, group] as const),
    ),
  );
  const visibleEdges = new Map<
    string,
    {
      source: MarkerGroup;
      target: MarkerGroup;
      connected: boolean;
      count: number;
    }
  >();
  relations.forEach((relation) => {
    const source = groupsByEntity.get(relation.from);
    const target = groupsByEntity.get(relation.to);
    if (!source || !target || source.id === target.id) return;
    const key = [source.id, target.id].sort().join("|");
    const current = visibleEdges.get(key);
    const connected =
      relation.from === selectedId || relation.to === selectedId;
    if (current) {
      current.connected ||= connected;
      current.count += 1;
    } else {
      visibleEdges.set(key, { source, target, connected, count: 1 });
    }
  });
  return {
    type: "FeatureCollection" as const,
    features: [...visibleEdges.values()].map((edge) => ({
      type: "Feature" as const,
      properties: {
        connected: edge.connected,
        relationCount: edge.count,
      },
      geometry: {
        type: "LineString" as const,
        coordinates: [
          [...edge.source.coordinates],
          [...edge.target.coordinates],
        ],
      },
    })),
  };
}
