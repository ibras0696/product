import {
  BuildingsIcon,
  CalendarDotsIcon,
  FileTextIcon,
  MapPinIcon,
  UserIcon,
} from "@phosphor-icons/react";

import type { EntityKind } from "../model/historyData";

export function GraphNodeIcon({ kind }: { kind: EntityKind }) {
  const iconProps = {
    size: 14,
    weight: "regular" as const,
    "aria-hidden": true,
  };
  if (kind === "person") return <UserIcon {...iconProps} />;
  if (kind === "event") return <CalendarDotsIcon {...iconProps} />;
  if (kind === "landmark") return <BuildingsIcon {...iconProps} />;
  if (kind === "source") return <FileTextIcon {...iconProps} />;
  return <MapPinIcon {...iconProps} />;
}
