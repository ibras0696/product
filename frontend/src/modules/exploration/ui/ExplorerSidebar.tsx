import {
  ClockCounterClockwiseIcon,
  GraphIcon,
  MapTrifoldIcon,
} from "@phosphor-icons/react";
import { useRef, useState } from "react";

import type {
  CatalogEntityType,
  CatalogOptionsViewModel,
  ResearchStatus,
} from "../api/viewModels";
import type { ExplorerDateRange } from "../model/dateRange";
import type { EntityKind, ExplorerView } from "../model/historyData";
import {
  ExplorerFilterControls,
  MobileFilterDrawer,
  type PresentedFilterType,
} from "./MobileFilterDrawer";

interface ExplorerSidebarProps {
  activeTypes: Set<CatalogEntityType>;
  activeResearchStatuses: Set<ResearchStatus>;
  activeView: ExplorerView;
  districtId: string | null;
  periodId: string | null;
  dateRange: ExplorerDateRange;
  options?: CatalogOptionsViewModel;
  onTypeToggle: (type: CatalogEntityType) => void;
  onResearchStatusToggle: (status: ResearchStatus) => void;
  onViewChange: (view: ExplorerView) => void;
  onDistrictChange: (id: string | null) => void;
  onDateRangeChange: (range: ExplorerDateRange) => void;
  onReset: () => void;
}

const views: Array<{ id: ExplorerView; label: string }> = [
  { id: "map", label: "Карта" },
  { id: "network", label: "Паутина связей" },
  { id: "timeline", label: "Хронология" },
];

function ViewIcon({ view }: { view: ExplorerView }) {
  const iconProps = {
    size: 20,
    weight: "regular" as const,
    "aria-hidden": true,
  };
  if (view === "map") return <MapTrifoldIcon {...iconProps} />;
  if (view === "network") return <GraphIcon {...iconProps} />;
  return <ClockCounterClockwiseIcon {...iconProps} />;
}

const typePresentation: Record<
  CatalogEntityType,
  { label: string; kind: EntityKind }
> = {
  settlement: { label: "Населённые пункты", kind: "place" },
  person: { label: "Личности", kind: "person" },
  event: { label: "События", kind: "event" },
  landmark: { label: "Достопримечательности", kind: "landmark" },
  natural_object: { label: "Природные объекты", kind: "landmark" },
  cultural_object: { label: "Культурные объекты", kind: "landmark" },
  organization: { label: "Организации", kind: "source" },
  university_object: { label: "Объекты университета", kind: "source" },
  artifact: { label: "Источники", kind: "source" },
};

const referenceTypes: CatalogEntityType[] = [
  "settlement",
  "person",
  "event",
  "landmark",
  "natural_object",
  "cultural_object",
  "organization",
  "university_object",
  "artifact",
];

export function ExplorerSidebar(props: ExplorerSidebarProps) {
  const { options } = props;
  const [filterOpen, setFilterOpen] = useState(false);
  const filterTriggerRef = useRef<HTMLButtonElement>(null);
  const presentedTypes: PresentedFilterType[] = referenceTypes
    .filter((type) => options?.entityTypes.includes(type))
    .map((type) => ({ id: type, ...typePresentation[type] }));
  const activeFilterCount =
    (props.activeTypes.size > 0 ? 1 : 0) +
    (props.activeResearchStatuses.size > 0 ? 1 : 0) +
    (props.districtId ? 1 : 0) +
    (props.periodId || props.dateRange.from || props.dateRange.to ? 1 : 0);
  const filterProps = {
    activeTypes: props.activeTypes,
    activeResearchStatuses: props.activeResearchStatuses,
    districtId: props.districtId,
    dateRange: props.dateRange,
    options,
    presentedTypes,
    onTypeToggle: props.onTypeToggle,
    onResearchStatusToggle: props.onResearchStatusToggle,
    onDistrictChange: props.onDistrictChange,
    onDateRangeChange: props.onDateRangeChange,
    onReset: props.onReset,
  };
  return (
    <aside className="hx-sidebar" aria-label="Навигация и фильтры атласа">
      <div className="hx-view-tabs" role="group" aria-label="Режим просмотра">
        {views.map((view) => (
          <button
            key={view.id}
            type="button"
            aria-pressed={props.activeView === view.id}
            onClick={() => {
              props.onViewChange(view.id);
            }}
          >
            <span className="hx-view-icon">
              <ViewIcon view={view.id} />
            </span>
            {view.label}
          </button>
        ))}
      </div>
      <ExplorerFilterControls {...filterProps} />
      <button
        ref={filterTriggerRef}
        type="button"
        className="hx-mobile-filter-trigger"
        aria-haspopup="dialog"
        aria-expanded={filterOpen}
        onClick={() => {
          setFilterOpen(true);
        }}
      >
        Фильтры{activeFilterCount > 0 ? ` · ${String(activeFilterCount)}` : ""}
      </button>
      <MobileFilterDrawer
        {...filterProps}
        open={filterOpen}
        triggerRef={filterTriggerRef}
        onClose={() => {
          setFilterOpen(false);
        }}
      />
      <a className="hx-about-link" href="#about">
        <span aria-hidden="true">ⓘ</span>О проекте
      </a>
    </aside>
  );
}
