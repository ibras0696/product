interface WizardNavigationProps {
  step: number;
  lastStep: number;
  pending: boolean;
  blocked: boolean;
  onBack: () => void;
}

export function WizardNavigation(props: WizardNavigationProps) {
  const onLastStep = props.step === props.lastStep;
  return (
    <>
      <button
        type="button"
        className="submission-secondary-action"
        disabled={props.step === 0 || props.pending}
        onClick={props.onBack}
      >
        Назад
      </button>
      <button
        type="submit"
        className="submission-primary-action"
        disabled={props.pending || (onLastStep && props.blocked)}
      >
        {props.pending
          ? "Сохраняем…"
          : onLastStep
            ? "Отправить в редакцию"
            : "Продолжить"}
      </button>
    </>
  );
}
