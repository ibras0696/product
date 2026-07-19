import { CircleIcon } from "@phosphor-icons/react";
import type { ReactNode } from "react";

import { useTimelineEvents } from "../api/timelineQueries";
import type { TimelineFilters } from "../api/timelineViewModels";

interface ExplorerTimelineProps {
  filters: TimelineFilters;
  eventsEnabled: boolean;
  onOpenEvent: (id: string) => void;
}

function periodLabel(from: number | null, to: number | null) {
  if (from !== null && to !== null) {
    return from === to ? String(from) : `${String(from)}–${String(to)}`;
  }
  if (from !== null) return `с ${String(from)}`;
  if (to !== null) return `до ${String(to)}`;
  return "Дата не указана";
}

function TimelineMessage({
  kind,
  children,
}: {
  kind: "status" | "alert";
  children: ReactNode;
}) {
  return (
    <div className="hx-timeline hx-timeline-state" role={kind}>
      {children}
    </div>
  );
}

export function ExplorerTimeline({
  filters,
  eventsEnabled,
  onOpenEvent,
}: ExplorerTimelineProps) {
  const timelineQuery = useTimelineEvents(filters, eventsEnabled);

  if (!eventsEnabled) {
    return (
      <TimelineMessage kind="status">
        События скрыты выбранными типами объектов.
      </TimelineMessage>
    );
  }
  if (timelineQuery.isPending) {
    return (
      <TimelineMessage kind="status">Загружаем хронологию…</TimelineMessage>
    );
  }
  if (timelineQuery.isError) {
    return (
      <TimelineMessage kind="alert">
        <span>Не удалось загрузить хронологию.</span>
        <button type="button" onClick={() => void timelineQuery.refetch()}>
          Повторить
        </button>
      </TimelineMessage>
    );
  }
  if (timelineQuery.data.items.length === 0) {
    return (
      <TimelineMessage kind="status">
        По выбранным фильтрам событий нет.
      </TimelineMessage>
    );
  }

  return (
    <ol className="hx-timeline" aria-label="Хронология событий">
      {timelineQuery.data.items.map((item) => (
        <li key={item.id}>
          <CircleIcon size={10} weight="fill" aria-hidden="true" />
          <time>{periodLabel(item.periodFrom, item.periodTo)}</time>
          <button
            type="button"
            onClick={() => {
              onOpenEvent(item.id);
            }}
          >
            {item.title}
          </button>
          <span>{item.shortDescription}</span>
        </li>
      ))}
    </ol>
  );
}
