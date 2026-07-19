import type { ReactNode } from "react";

type StateTone = "neutral" | "danger" | "warning";

interface StatePanelProps {
  title: string;
  description: string;
  action?: ReactNode;
  tone?: StateTone;
  live?: boolean;
}

export function StatePanel({
  title,
  description,
  action,
  tone = "neutral",
  live = false,
}: StatePanelProps) {
  return (
    <section
      className={`state-panel state-panel-${tone}`}
      role={tone === "danger" ? "alert" : "status"}
      aria-live={live ? "polite" : "off"}
    >
      <h1>{title}</h1>
      <p>{description}</p>
      {action ? <div className="state-panel-action">{action}</div> : null}
    </section>
  );
}
