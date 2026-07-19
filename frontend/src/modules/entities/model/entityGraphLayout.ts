import type { EntityGraph, EntityGraphEdge } from "../domain/entity";

export interface GraphLayoutNode {
  id: string;
  title: string;
  level: 0 | 1 | 2;
  x: number;
  y: number;
}

export interface GraphLayoutEdge {
  edge: EntityGraphEdge;
  source: GraphLayoutNode;
  target: GraphLayoutNode;
}

export const MAX_GRAPH_NODES = 18;

function otherEndpoint(edge: EntityGraphEdge, nodeId: string) {
  if (edge.sourceId === nodeId) return edge.targetId;
  if (edge.targetId === nodeId) return edge.sourceId;
  return null;
}

export function graphDepths(graph: EntityGraph) {
  const depths = new Map<string, 0 | 1 | 2>([[graph.center.id, 0]]);
  const queue = [graph.center.id];
  for (let index = 0; index < queue.length; index += 1) {
    const currentId = queue[index];
    const depth = depths.get(currentId) ?? 0;
    if (depth >= 2) continue;
    graph.edges.forEach((edge) => {
      const nextId = otherEndpoint(edge, currentId);
      if (!nextId || depths.has(nextId)) return;
      depths.set(nextId, (depth + 1) as 1 | 2);
      queue.push(nextId);
    });
  }
  return depths;
}

function ringPoint(index: number, count: number, radius: number) {
  const angle = -Math.PI / 2 + (index * Math.PI * 2) / Math.max(count, 1);
  return {
    x: 500 + Math.cos(angle) * radius,
    y: 310 + Math.sin(angle) * radius,
  };
}

export function createEntityGraphLayout(graph: EntityGraph) {
  const depths = graphDepths(graph);
  const visible = graph.nodes
    .filter((node) => depths.has(node.id))
    .sort(
      (left, right) => (depths.get(left.id) ?? 2) - (depths.get(right.id) ?? 2),
    )
    .slice(0, MAX_GRAPH_NODES - 1);
  const nodes: GraphLayoutNode[] = [
    {
      id: graph.center.id,
      title: graph.center.title.ru,
      level: 0,
      x: 500,
      y: 310,
    },
  ];
  ([1, 2] as const).forEach((level) => {
    const ring = visible.filter((node) => depths.get(node.id) === level);
    ring.forEach((node, index) => {
      nodes.push({
        id: node.id,
        title: node.title.ru,
        level,
        ...ringPoint(index, ring.length, level === 1 ? 170 : 275),
      });
    });
  });
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const edges = graph.edges.flatMap((edge): GraphLayoutEdge[] => {
    const source = byId.get(edge.sourceId);
    const target = byId.get(edge.targetId);
    return source && target ? [{ edge, source, target }] : [];
  });
  return {
    nodes,
    edges,
    omittedCount: Math.max(graph.nodes.length + 1 - nodes.length, 0),
  };
}
