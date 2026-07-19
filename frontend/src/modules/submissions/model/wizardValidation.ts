import type { FieldErrors, FieldPath } from "react-hook-form";

import type { SubmissionWizardValues } from "./submissionWizardSchema";

export interface WizardFieldError {
  field: FieldPath<SubmissionWizardValues>;
  label: string;
  message: string;
}

export const wizardFields: Array<Array<FieldPath<SubmissionWizardValues>>> = [
  ["type"],
  ["relatedEntityId", "settlementId"],
  ["title", "description", "sourceDescription"],
  ["authorName", "contact", "consent"],
  [],
  [
    "type",
    "relatedEntityId",
    "settlementId",
    "title",
    "description",
    "sourceDescription",
    "authorName",
    "contact",
    "consent",
  ],
];

const labels: Record<FieldPath<SubmissionWizardValues>, string> = {
  type: "Тип материала",
  relatedEntityId: "Связанный объект",
  settlementId: "Населённый пункт",
  title: "Заголовок",
  description: "Описание",
  sourceDescription: "Происхождение сведений",
  authorName: "Имя автора",
  contact: "Способ связи",
  consent: "Согласие",
};

export function visibleWizardErrors(
  errors: FieldErrors<SubmissionWizardValues>,
  step: number,
): WizardFieldError[] {
  return (wizardFields[step] ?? []).flatMap((field) => {
    const message = errors[field]?.message;
    return typeof message === "string"
      ? [{ field, label: labels[field], message }]
      : [];
  });
}

export function firstInvalidStep(errors: FieldErrors<SubmissionWizardValues>) {
  return wizardFields.findIndex((fields) =>
    fields.some((field) => Boolean(errors[field])),
  );
}
