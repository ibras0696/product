import { z } from "zod";

import type {
  CreateSubmissionInput,
  PatchSubmissionInput,
} from "../domain/submission";
import { submissionTypes, type SubmissionType } from "../domain/submission";

const requiredText = (message: string, maximum: number) =>
  z
    .string()
    .trim()
    .min(1, message)
    .max(maximum, `Не более ${String(maximum)} символов`);
const optionalUuid = z.uuid("Выберите значение из каталога").nullable();

export const submissionWizardSchema = z.object({
  type: z.enum(submissionTypes),
  relatedEntityId: optionalUuid,
  settlementId: optionalUuid,
  title: requiredText("Укажите заголовок", 300),
  description: requiredText("Опишите материал", 20_000),
  sourceDescription: requiredText("Укажите происхождение сведений", 5_000),
  authorName: requiredText("Укажите имя автора", 300),
  contact: requiredText("Укажите способ связи", 500),
  consent: z.boolean().refine(Boolean, "Подтвердите согласие перед отправкой"),
});

export type SubmissionWizardValues = z.infer<typeof submissionWizardSchema>;

export const submissionWizardDefaults: SubmissionWizardValues = {
  type: "new_entity",
  relatedEntityId: null,
  settlementId: null,
  title: "",
  description: "",
  sourceDescription: "",
  authorName: "",
  contact: "",
  consent: false,
};

export interface SubmissionTypePresentation {
  title: string;
  description: string;
  materialTitle: string;
  materialDescription: string;
}

export const submissionTypePresentation: Record<
  SubmissionType,
  SubmissionTypePresentation
> = {
  new_entity: {
    title: "Новый объект",
    description:
      "Предложить место, человека, событие или другой объект истории.",
    materialTitle: "Название материала",
    materialDescription: "Расскажите, что должно появиться в каталоге.",
  },
  update_entity: {
    title: "Дополнить объект",
    description: "Добавить сведения к уже опубликованной карточке.",
    materialTitle: "Заголовок дополнения",
    materialDescription: "Опишите новые или уточняющие сведения.",
  },
  new_relation: {
    title: "Новая связь",
    description: "Сообщить о связи между историческими объектами.",
    materialTitle: "Название связи",
    materialDescription: "Опишите известную связь и подтверждающие сведения.",
  },
  new_source: {
    title: "Новый источник",
    description: "Добавить документ, книгу, свидетельство или веб-ресурс.",
    materialTitle: "Название источника",
    materialDescription: "Опишите содержание и значение источника.",
  },
  new_media: {
    title: "Фото или изображение",
    description: "Передать визуальный материал для существующей карточки.",
    materialTitle: "Название подборки",
    materialDescription: "Кратко опишите передаваемые изображения.",
  },
  report_error: {
    title: "Сообщить об ошибке",
    description: "Указать неточность в опубликованном материале.",
    materialTitle: "Краткий заголовок",
    materialDescription: "Опишите ошибку и предлагаемое исправление.",
  },
};

const submissionTargets: Record<
  SubmissionType,
  { entity: boolean; settlement: boolean }
> = {
  new_entity: { entity: false, settlement: true },
  update_entity: { entity: true, settlement: false },
  new_relation: { entity: true, settlement: true },
  new_source: { entity: true, settlement: false },
  new_media: { entity: true, settlement: false },
  report_error: { entity: true, settlement: false },
};

export function submissionTargetFields(type: SubmissionType) {
  return submissionTargets[type];
}

export function submissionRequiresMedia(type: SubmissionType) {
  return type === "new_media";
}

export function toCreateSubmissionInput(
  values: SubmissionWizardValues,
): CreateSubmissionInput {
  const parsed = submissionWizardSchema.parse(values);
  const targets = submissionTargetFields(parsed.type);
  return {
    ...parsed,
    relatedEntityId: targets.entity ? parsed.relatedEntityId : null,
    settlementId: targets.settlement ? parsed.settlementId : null,
  };
}

export function toPatchSubmissionInput(
  values: SubmissionWizardValues,
): PatchSubmissionInput {
  const input = toCreateSubmissionInput(values);
  return {
    relatedEntityId: input.relatedEntityId,
    settlementId: input.settlementId,
    title: input.title,
    description: input.description,
    sourceDescription: input.sourceDescription,
    authorName: input.authorName,
    contact: input.contact,
    consent: input.consent,
  };
}
