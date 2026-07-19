import type { EntitySource } from "../domain/entity";

export const sourceLabels: Record<EntitySource["type"], string> = {
  archive_document: "Архивный документ",
  book: "Книга",
  scientific_article: "Научная статья",
  museum_material: "Музейный материал",
  official_publication: "Официальная публикация",
  photo: "Фотография",
  audio: "Аудиозапись",
  video: "Видеозапись",
  oral_testimony: "Устное свидетельство",
  web_resource: "Веб-ресурс",
};
