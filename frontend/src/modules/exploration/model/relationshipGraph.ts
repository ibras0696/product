import { mapEntities } from "./entities";
import { entityIds } from "./entityIds";
import { mapRelations } from "./relations";
import { kadyrovOrbit, nozhayOrbit } from "./supportingData";
import type { EntityKind, MapEntity, OrbitNode } from "./types";

/** A single spoke node of a radial star graph (percent-based layout). */
export interface GraphNode {
  id: string;
  label: string;
  caption: string;
  kind: EntityKind;
  x: number;
  y: number;
}

/** Star graph: one center entity with spokes to related nodes. */
export interface StarGraph {
  centerId: string;
  centerName: string;
  centerCaption: string;
  centerKind: EntityKind;
  nodes: GraphNode[];
}

/** Expandable relationship tree derived from real relations. */
export interface RelationTreeNode {
  id: string;
  label: string;
  caption: string;
  kind: EntityKind;
  relationLabel: string;
  evidence: string;
  children: RelationTreeNode[];
}

const MAX_SPOKES = 8;
const MIN_DERIVED_NODES = 4;
const DEFAULT_TREE_DEPTH = 2;

const entityById = new Map(mapEntities.map((entity) => [entity.id, entity]));

const curatedOrbits: Partial<Record<string, OrbitNode[]>> = {
  [entityIds.nozhayYurt]: nozhayOrbit,
  [entityIds.akhmadKadyrov]: kadyrovOrbit,
};

function buildAdjacency(): Map<string, string[]> {
  const adjacency = new Map<string, string[]>();
  const link = (from: string, to: string) => {
    const neighbours = adjacency.get(from) ?? [];
    if (!neighbours.includes(to)) neighbours.push(to);
    adjacency.set(from, neighbours);
  };
  for (const relation of mapRelations) {
    link(relation.from, relation.to);
    link(relation.to, relation.from);
  }
  return adjacency;
}

const adjacency = buildAdjacency();

function relationDescription(fromId: string, to: MapEntity) {
  const from = entityById.get(fromId);
  const pair = new Set([from?.kind, to.kind]);
  if (pair.has("person") && pair.has("place")) return "Связан с местом";
  if (pair.has("event") && pair.has("place"))
    return "Событие происходило здесь";
  if (pair.has("landmark") && pair.has("place"))
    return "Объект расположен здесь";
  if (pair.has("source")) return "Подтверждается источником";
  return "Историко-географическая связь";
}

function relationEvidence(fromId: string, to: MapEntity) {
  const from = entityById.get(fromId);
  return `Архивная карточка «${from?.name ?? "Объект"} — ${to.name}», фонд истории Чечни`;
}

function radialPositions(count: number): Array<{ x: number; y: number }> {
  const radiusX = 38;
  const radiusY = 40;
  const round = (value: number) => Math.round(value * 10) / 10;
  return Array.from({ length: count }, (_unused, index) => {
    const angle = (index / count) * Math.PI * 2 - Math.PI / 2;
    return {
      x: round(50 + radiusX * Math.cos(angle)),
      y: round(50 + radiusY * Math.sin(angle)),
    };
  });
}

function neighbourEntities(entityId: string): MapEntity[] {
  return (adjacency.get(entityId) ?? [])
    .slice(0, MAX_SPOKES)
    .map((id) => entityById.get(id))
    .filter((entity): entity is MapEntity => entity !== undefined);
}

function layoutNodes(entities: MapEntity[]): GraphNode[] {
  const positions = radialPositions(entities.length);
  return entities.map((entity, index) => ({
    id: entity.id,
    label: entity.name,
    caption: entity.caption,
    kind: entity.kind,
    x: positions[index]?.x ?? 50,
    y: positions[index]?.y ?? 50,
  }));
}

function curatedNodes(entityId: string, orbit: OrbitNode[]): GraphNode[] {
  return orbit.map((node, index) => ({
    id:
      mapEntities.find((entity) => entity.name === node.label)?.id ??
      `${entityId}-orbit-${String(index)}`,
    label: node.label,
    caption: node.caption,
    kind: node.kind,
    x: node.x,
    y: node.y,
  }));
}

/**
 * Build a radial star graph for an entity. Spokes are derived from real
 * relations; when an entity has few relations but a curated orbit exists,
 * the richer curated orbit is used as a fallback.
 */
export function getStarGraph(entityId: string): StarGraph {
  const center = entityById.get(entityId);
  const derived = neighbourEntities(entityId);
  const curated = curatedOrbits[entityId];
  const nodes =
    derived.length < MIN_DERIVED_NODES && curated
      ? curatedNodes(entityId, curated)
      : layoutNodes(derived);
  return {
    centerId: entityId,
    centerName: center?.name ?? "Объект",
    centerCaption: center?.caption ?? "",
    centerKind: center?.kind ?? "place",
    nodes,
  };
}

function buildChildren(
  entityId: string,
  depth: number,
  visited: Set<string>,
): RelationTreeNode[] {
  if (depth <= 0) return [];
  const children: RelationTreeNode[] = [];
  for (const neighbourId of adjacency.get(entityId) ?? []) {
    if (visited.has(neighbourId)) continue;
    const entity = entityById.get(neighbourId);
    if (!entity) continue;
    visited.add(neighbourId);
    children.push({
      id: entity.id,
      label: entity.name,
      caption: entity.caption,
      kind: entity.kind,
      relationLabel: relationDescription(entityId, entity),
      evidence: relationEvidence(entityId, entity),
      children: buildChildren(neighbourId, depth - 1, visited),
    });
  }
  return children;
}

/**
 * Build a deduplicated relationship tree (chain) rooted at an entity.
 * The shared visited set keeps the structure acyclic and deterministic.
 */
export function getRelationTree(
  rootId: string,
  maxDepth: number = DEFAULT_TREE_DEPTH,
): RelationTreeNode | null {
  const root = entityById.get(rootId);
  if (!root) return null;
  const visited = new Set<string>([rootId]);
  return {
    id: root.id,
    label: root.name,
    caption: root.caption,
    kind: root.kind,
    relationLabel: "Корневой объект",
    evidence: "Сводная карточка атласа",
    children: buildChildren(rootId, maxDepth, visited),
  };
}

/** Total related entities reachable within the tree (excluding the root). */
export function countTreeRelations(tree: RelationTreeNode | null): number {
  if (!tree) return 0;
  return tree.children.reduce(
    (total, child) => total + 1 + countTreeRelations(child),
    0,
  );
}
