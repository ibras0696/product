import { StatePanel } from "@/shared/ui";

interface EntityPageStateProps {
  title: string;
  description: string;
  onBack: () => void;
  danger?: boolean;
}

export function EntityPageState({
  title,
  description,
  onBack,
  danger = false,
}: EntityPageStateProps) {
  return (
    <main className="entity-state-page">
      <StatePanel
        title={title}
        description={description}
        tone={danger ? "danger" : "neutral"}
        live
        action={
          <button type="button" className="entity-button" onClick={onBack}>
            Вернуться к карте
          </button>
        }
      />
    </main>
  );
}
