import { useFormContext, useWatch } from "react-hook-form";

import {
  submissionTypePresentation,
  type SubmissionWizardValues,
} from "../../../model/submissionWizardSchema";
import { submissionTypes } from "../../../domain/submission";

export function SubmissionTypeStep({ locked = false }: { locked?: boolean }) {
  const { control, register, formState } =
    useFormContext<SubmissionWizardValues>();
  const selectedType = useWatch({ control, name: "type" });
  if (locked) {
    const selected = submissionTypePresentation[selectedType];
    return (
      <section className="submission-step" aria-labelledby="locked-type-title">
        <h3 id="locked-type-title">Тип заявки сохранён</h3>
        <div className="submission-type-option submission-type-option--locked">
          <span className="submission-type-marker" aria-hidden="true" />
          <span>
            <strong>{selected.title}</strong>
            <small>{selected.description}</small>
          </span>
        </div>
        <p className="submission-step-lead">
          После создания защищённого черновика тип нельзя изменить. Остальные
          сведения по-прежнему можно исправить.
        </p>
      </section>
    );
  }
  return (
    <fieldset className="submission-step submission-type-step">
      <legend>Что вы хотите добавить?</legend>
      <p className="submission-step-lead">
        Выберите один вариант. Набор следующих полей изменится автоматически.
      </p>
      <div className="submission-type-grid">
        {submissionTypes.map((type) => {
          const presentation = submissionTypePresentation[type];
          return (
            <label key={type} className="submission-type-option">
              <input type="radio" value={type} {...register("type")} />
              <span>
                <strong>{presentation.title}</strong>
                <small>{presentation.description}</small>
              </span>
            </label>
          );
        })}
      </div>
      {formState.errors.type?.message ? (
        <span className="submission-field-error" role="alert">
          {formState.errors.type.message}
        </span>
      ) : null}
    </fieldset>
  );
}
