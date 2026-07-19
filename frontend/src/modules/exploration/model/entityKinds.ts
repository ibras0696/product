import type { EntityKind } from "./types";

export const kindLabels: Record<EntityKind, string> = {
  place: "Населённые пункты",
  person: "Герои",
  event: "События",
  landmark: "Достопримечательности",
  source: "Источники",
};

export const entityKinds = Object.keys(kindLabels) as EntityKind[];
