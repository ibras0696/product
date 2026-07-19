import { useFormContext } from "react-hook-form";

import type { SubmissionWizardValues } from "../../../model/submissionWizardSchema";
import { StepFieldError } from "./StepFieldError";

export function SubmissionContactStep() {
  const {
    register,
    formState: { errors },
  } = useFormContext<SubmissionWizardValues>();

  return (
    <section
      className="submission-step"
      aria-labelledby="submission-contact-title"
    >
      <h3 id="submission-contact-title">Автор и обратная связь</h3>
      <p className="submission-step-lead">
        Контакты нужны редакции, чтобы уточнить детали материала.
      </p>

      <label className="submission-field">
        <span>Как к вам обращаться</span>
        <input
          {...register("authorName")}
          aria-describedby={errors.authorName ? "author-name-error" : undefined}
          autoComplete="name"
        />
        <StepFieldError id="author-name-error" error={errors.authorName} />
      </label>

      <label className="submission-field">
        <span>Телефон, почта или другой способ связи</span>
        <input
          {...register("contact")}
          aria-describedby={errors.contact ? "contact-error" : undefined}
          autoComplete="off"
        />
        <StepFieldError id="contact-error" error={errors.contact} />
      </label>

      <label className="submission-consent">
        <input type="checkbox" {...register("consent")} />
        <span>
          Я согласен передать указанные сведения редакции для рассмотрения
          заявки.
        </span>
      </label>
      <StepFieldError id="consent-error" error={errors.consent} />
      <p className="submission-legal-note">
        Точный юридический текст согласия должен быть утверждён до запуска.
      </p>
    </section>
  );
}
