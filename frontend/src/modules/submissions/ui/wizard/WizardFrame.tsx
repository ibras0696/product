import { forwardRef, type ReactNode } from "react";

import { wizardSteps } from "../../model/wizardSteps";

interface WizardFrameProps {
  step: number;
  children: ReactNode;
  navigation: ReactNode;
}

export const WizardFrame = forwardRef<HTMLHeadingElement, WizardFrameProps>(
  function WizardFrame(props, ref) {
    return (
      <div className="submission-wizard-layout">
        <aside className="submission-progress" aria-label="Шаги заявки">
          <div className="submission-progress-summary">
            <span>
              Шаг {props.step + 1} из {wizardSteps.length}
            </span>
            <strong>{wizardSteps[props.step]}</strong>
          </div>
          <progress
            aria-label={`Выполнено шагов: ${String(props.step + 1)} из ${String(wizardSteps.length)}`}
            value={props.step + 1}
            max={wizardSteps.length}
          />
          <ol>
            {wizardSteps.map((title, index) => (
              <li
                key={title}
                aria-current={index === props.step ? "step" : undefined}
              >
                <span>{index + 1}</span>
                {title}
              </li>
            ))}
          </ol>
        </aside>
        <div className="submission-wizard-card">
          <header className="submission-step-heading">
            <span>Шаг {props.step + 1}</span>
            <h2 ref={ref} tabIndex={-1}>
              {wizardSteps[props.step]}
            </h2>
          </header>
          {props.children}
          <div className="submission-wizard-navigation">{props.navigation}</div>
        </div>
        <aside className="submission-privacy-note">
          <strong>Приватность</strong>
          <p>
            Контакты и код отслеживания не попадают в адрес страницы или
            хранилище браузера. Доступ к черновику подтверждает защищённая
            серверная cookie.
          </p>
        </aside>
      </div>
    );
  },
);
