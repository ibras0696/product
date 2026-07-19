import { forwardRef } from "react";
import type { FieldPath } from "react-hook-form";

import type { SubmissionWizardValues } from "../../model/submissionWizardSchema";
import type { WizardFieldError } from "../../model/wizardValidation";

interface WizardErrorSummaryProps {
  errors: WizardFieldError[];
  onFieldFocus: (field: FieldPath<SubmissionWizardValues>) => void;
}

export const WizardErrorSummary = forwardRef<
  HTMLDivElement,
  WizardErrorSummaryProps
>(function WizardErrorSummary({ errors, onFieldFocus }, ref) {
  if (errors.length === 0) return null;
  return (
    <div
      ref={ref}
      className="submission-error-summary"
      role="alert"
      tabIndex={-1}
    >
      <h2>Проверьте заполнение</h2>
      <p>Исправьте отмеченные поля, чтобы продолжить.</p>
      <ul>
        {errors.map((error) => (
          <li key={error.field}>
            <button
              type="button"
              onClick={() => {
                onFieldFocus(error.field);
              }}
            >
              <strong>{error.label}:</strong> {error.message}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
});
