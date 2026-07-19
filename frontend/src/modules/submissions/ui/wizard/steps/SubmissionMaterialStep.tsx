import { useFormContext, useWatch } from "react-hook-form";

import {
  submissionTypePresentation,
  type SubmissionWizardValues,
} from "../../../model/submissionWizardSchema";
import { StepFieldError } from "./StepFieldError";

export function SubmissionMaterialStep() {
  const {
    control,
    register,
    formState: { errors },
  } = useFormContext<SubmissionWizardValues>();
  const type = useWatch({ control, name: "type" });
  const copy = submissionTypePresentation[type];

  return (
    <section
      className="submission-step"
      aria-labelledby="submission-material-title"
    >
      <h3 id="submission-material-title">Материал</h3>
      <p className="submission-step-lead">{copy.materialDescription}</p>

      <label className="submission-field">
        <span>{copy.materialTitle}</span>
        <input
          {...register("title")}
          aria-describedby={errors.title ? "title-error" : undefined}
          autoComplete="off"
        />
        <StepFieldError id="title-error" error={errors.title} />
      </label>

      <label className="submission-field">
        <span>Описание</span>
        <textarea
          {...register("description")}
          aria-describedby={
            errors.description ? "description-error" : undefined
          }
          rows={7}
        />
        <StepFieldError id="description-error" error={errors.description} />
      </label>

      <label className="submission-field">
        <span>Откуда взялись сведения</span>
        <textarea
          {...register("sourceDescription")}
          aria-describedby={
            errors.sourceDescription ? "source-description-error" : undefined
          }
          rows={4}
        />
        <StepFieldError
          id="source-description-error"
          error={errors.sourceDescription}
        />
      </label>
    </section>
  );
}
