import type { GraphViewModel } from "../api/viewModels";

export type NetworkNode = GraphViewModel["nodes"][number];
export type NetworkEdge = GraphViewModel["edges"][number];

export const relationTypeLabels: Readonly<Record<NetworkEdge["type"], string>> =
  {
    born_in: "Родился в",
    lived_in: "Жил в",
    worked_in: "Работал в",
    studied_in: "Учился в",
    taught_at: "Преподавал в",
    participated_in: "Участвовал в",
    located_in: "Расположен в",
    part_of: "Часть объекта",
    created_by: "Создан автором",
    described_in: "Описан в",
    connected_with: "Связан с",
    connected_with_chgu: "Связан с ЧГУ",
  };

export interface NetworkBranch {
  node: NetworkNode;
  centerEdges: NetworkEdge[];
  levelTwoNodes: Array<{ node: NetworkNode; edges: NetworkEdge[] }>;
  peerEdges: NetworkEdge[];
}

export interface NetworkLegendItem {
  type: NetworkEdge["type"];
  titles: string[];
}

export interface NetworkLayoutNode {
  id: string;
  title: string;
  level: 0 | 1 | 2;
  x: number;
  y: number;
}

export interface NetworkLayoutEdge {
  edge: NetworkEdge;
  source: NetworkLayoutNode;
  target: NetworkLayoutNode;
}

export interface NetworkLayout {
  width: number;
  height: number;
  nodes: NetworkLayoutNode[];
  edges: NetworkLayoutEdge[];
  omittedNodesCount: number;
}

const NETWORK_WIDTH = 1280;
const NETWORK_MIN_HEIGHT = 660;
const NETWORK_ROW_HEIGHT = 76;

function otherEndpoint(edge: NetworkEdge, nodeId: string): string | null {
  if (edge.source_id === nodeId) return edge.target_id;
  if (edge.target_id === nodeId) return edge.source_id;
  return null;
}

function graphDistances(graph: GraphViewModel): Map<string, number> {
  const distances = new Map([[graph.center.id, 0]]);
  const queue = [graph.center.id];
  for (let index = 0; index < queue.length; index += 1) {
    const currentId = queue[index];
    const distance = distances.get(currentId) ?? 0;
    if (distance >= 2) continue;
    graph.edges.forEach((edge) => {
      const nextId = otherEndpoint(edge, currentId);
      if (!nextId || distances.has(nextId)) return;
      distances.set(nextId, distance + 1);
      queue.push(nextId);
    });
  }
  return distances;
}

function levelPoint(index: number, count: number, x: number, height: number) {
  const contentHeight = Math.max((count - 1) * NETWORK_ROW_HEIGHT, 0);
  return { x, y: (height - contentHeight) / 2 + index * NETWORK_ROW_HEIGHT };
}

export function createNetworkLayout(graph: GraphViewModel): NetworkLayout {
  const distances = graphDistances(graph);
  const levelOne = graph.nodes.filter((node) => distances.get(node.id) === 1);
  const levelTwo = graph.nodes.filter((node) => distances.get(node.id) === 2);
  const largestLevel = Math.max(levelOne.length, levelTwo.length, 1);
  const height = Math.max(
    NETWORK_MIN_HEIGHT,
    (largestLevel - 1) * NETWORK_ROW_HEIGHT + 180,
  );
  const center: NetworkLayoutNode = {
    id: graph.center.id,
    title: graph.center.title.ru,
    level: 0,
    x: 160,
    y: height / 2,
  };
  const nodes: NetworkLayoutNode[] = [
    center,
    ...levelOne.map((node, index) => ({
      id: node.id,
      title: node.title.ru,
      level: 1 as const,
      ...levelPoint(index, levelOne.length, 610, height),
    })),
    ...levelTwo.map((node, index) => ({
      id: node.id,
      title: node.title.ru,
      level: 2 as const,
      ...levelPoint(index, levelTwo.length, 1080, height),
    })),
  ];
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const edges = graph.edges.flatMap((edge) => {
    const source = byId.get(edge.source_id);
    const target = byId.get(edge.target_id);
    return source && target ? [{ edge, source, target }] : [];
  });
  return {
    width: NETWORK_WIDTH,
    height,
    nodes,
    edges,
    omittedNodesCount: graph.nodes.length + 1 - nodes.length,
  };
}

export function buildNetworkBranches(graph: GraphViewModel): NetworkBranch[] {
  const distances = graphDistances(graph);
  const nodesById = new Map(graph.nodes.map((node) => [node.id, node]));
  const levelOneIds = new Set(
    graph.nodes
      .filter((node) => distances.get(node.id) === 1)
      .map((node) => node.id),
  );
  return graph.nodes
    .filter((node) => levelOneIds.has(node.id))
    .map((node) => {
      const incident = graph.edges.filter((edge) =>
        [edge.source_id, edge.target_id].includes(node.id),
      );
      const levelTwoIds = new Set(
        incident
          .map((edge) => otherEndpoint(edge, node.id))
          .filter((id): id is string => Boolean(id && distances.get(id) === 2)),
      );
      return {
        node,
        centerEdges: incident.filter((edge) =>
          [edge.source_id, edge.target_id].includes(graph.center.id),
        ),
        levelTwoNodes: [...levelTwoIds].flatMap((id) => {
          const child = nodesById.get(id);
          if (!child) return [];
          return [
            {
              node: child,
              edges: incident.filter(
                (edge) => otherEndpoint(edge, node.id) === id,
              ),
            },
          ];
        }),
        peerEdges: incident.filter((edge) => {
          const otherId = otherEndpoint(edge, node.id);
          return Boolean(otherId && levelOneIds.has(otherId));
        }),
      };
    });
}

export function buildNetworkLegend(graph: GraphViewModel): NetworkLegendItem[] {
  const titlesByType = new Map<NetworkEdge["type"], Set<string>>();
  graph.edges.forEach((edge) => {
    const titles = titlesByType.get(edge.type) ?? new Set<string>();
    titles.add(edge.title.ru);
    titlesByType.set(edge.type, titles);
  });
  return [...titlesByType].map(([type, titles]) => ({
    type,
    titles: [...titles],
  }));
}
