import type { GraphViewModel } from "../api/viewModels";

export interface RelationBranch {
  edgeId: string;
  entityId: string;
  title: string;
  type: GraphViewModel["nodes"][number]["type"];
  relationTitle: string;
  sourcesCount: number;
  children: RelationBranch[];
}

function otherEnd(sourceId: string, targetId: string, currentId: string) {
  return sourceId === currentId ? targetId : sourceId;
}

export function buildRelationTree(graph: GraphViewModel): RelationBranch[] {
  const nodes = new Map(graph.nodes.map((node) => [node.id, node]));
  const adjacent = (id: string, visited: ReadonlySet<string>) =>
    graph.edges.flatMap((edge): RelationBranch[] => {
      if (edge.source_id !== id && edge.target_id !== id) return [];
      const entityId = otherEnd(edge.source_id, edge.target_id, id);
      if (visited.has(entityId)) return [];
      const node = nodes.get(entityId);
      if (!node) return [];
      return [
        {
          edgeId: edge.id,
          entityId,
          title: node.title.ru,
          type: node.type,
          relationTitle: edge.title.ru,
          sourcesCount: edge.sources_count,
          children: [],
        },
      ];
    });
  const first = adjacent(graph.center.id, new Set([graph.center.id]));
  return first.map((branch) => ({
    ...branch,
    children: adjacent(
      branch.entityId,
      new Set([graph.center.id, branch.entityId]),
    ),
  }));
}
