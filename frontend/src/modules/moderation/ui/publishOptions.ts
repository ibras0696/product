import type { RelationType, SourceType } from "../domain/types";

export const sourceOptions: Array<{ value: SourceType; label: string }> = [
  { value: "archive_document", label: "Архивный документ" },
  { value: "book", label: "Книга" },
  { value: "scientific_article", label: "Научная статья" },
  { value: "museum_material", label: "Музейный материал" },
  { value: "official_publication", label: "Официальная публикация" },
  { value: "photo", label: "Фотография" },
  { value: "audio", label: "Аудиозапись" },
  { value: "video", label: "Видеозапись" },
  { value: "oral_testimony", label: "Устное свидетельство" },
  { value: "web_resource", label: "Веб-ресурс" },
];

export const relationOptions: Array<{ value: RelationType; label: string }> = [
  { value: "born_in", label: "Родился в" },
  { value: "lived_in", label: "Жил в" },
  { value: "worked_in", label: "Работал в" },
  { value: "studied_in", label: "Учился в" },
  { value: "taught_at", label: "Преподавал в" },
  { value: "participated_in", label: "Участвовал в" },
  { value: "located_in", label: "Расположен в" },
  { value: "part_of", label: "Часть объекта" },
  { value: "created_by", label: "Создан автором" },
  { value: "described_in", label: "Описан в" },
  { value: "connected_with", label: "Связан с" },
  { value: "connected_with_chgu", label: "Связан с ЧГУ" },
];

export const sourceTypeValues = sourceOptions.map((option) => option.value) as [
  SourceType,
  ...SourceType[],
];
export const relationTypeValues = relationOptions.map(
  (option) => option.value,
) as [RelationType, ...RelationType[]];
