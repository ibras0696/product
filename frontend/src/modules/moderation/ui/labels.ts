import type { ModerationSubmissionType } from "../domain/types";

export const moderationTypeLabels: Record<ModerationSubmissionType, string> = {
  new_entity: "Новая сущность",
  update_entity: "Изменение сущности",
  new_relation: "Новая связь",
  new_source: "Новый источник",
  new_media: "Новое медиа",
  report_error: "Сообщение об ошибке",
};
