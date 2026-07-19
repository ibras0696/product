import { z } from "zod";

import type { AdminRelationView, RelationInput } from "../domain/catalog";

export const relationTypes = [
  "born_in",
  "lived_in",
  "worked_in",
  "studied_in",
  "taught_at",
  "participated_in",
  "located_in",
  "part_of",
  "created_by",
  "described_in",
  "connected_with",
  "connected_with_chgu",
] as const;

const year = z
  .string()
  .trim()
  .refine(
    (value) => value === "" || Number.isInteger(Number(value)),
    "Укажите целый год",
  );
export const relationSchema = z
  .object({
    sourceEntityId: z.uuid("Укажите UUID исходной сущности"),
    targetEntityId: z.uuid("Укажите UUID целевой сущности"),
    type: z.enum(relationTypes),
    titleRu: z.string().trim().min(1, "Укажите название").max(300),
    titleCe: z.string().trim().max(300),
    descriptionRu: z.string().trim().min(1, "Укажите описание").max(300),
    descriptionCe: z.string().trim().max(300),
    periodFrom: year,
    periodTo: year,
    status: z.enum(["draft", "published"]),
  })
  .refine(
    ({ sourceEntityId, targetEntityId }) => sourceEntityId !== targetEntityId,
    {
      message: "Нельзя связать сущность с самой собой",
      path: ["targetEntityId"],
    },
  )
  .refine(
    ({ periodFrom, periodTo }) =>
      periodFrom === "" ||
      periodTo === "" ||
      Number(periodFrom) <= Number(periodTo),
    {
      message: "Начало периода не может быть позже конца",
      path: ["periodTo"],
    },
  );

export type RelationFormValues = z.infer<typeof relationSchema>;
const nullableYear = (value: string) => (value === "" ? null : Number(value));

export function relationInput(values: RelationFormValues): RelationInput {
  return {
    sourceEntityId: values.sourceEntityId,
    targetEntityId: values.targetEntityId,
    type: values.type,
    title: { ru: values.titleRu, ce: values.titleCe || null },
    description: { ru: values.descriptionRu, ce: values.descriptionCe || null },
    periodFrom: nullableYear(values.periodFrom),
    periodTo: nullableYear(values.periodTo),
    status: values.status,
  };
}

export function relationDefaults(
  item: AdminRelationView | null,
): RelationFormValues {
  if (!item)
    return {
      sourceEntityId: "",
      targetEntityId: "",
      type: "connected_with",
      titleRu: "",
      titleCe: "",
      descriptionRu: "",
      descriptionCe: "",
      periodFrom: "",
      periodTo: "",
      status: "draft",
    };
  return {
    sourceEntityId: item.sourceEntityId,
    targetEntityId: item.targetEntityId,
    type: item.type,
    titleRu: item.title.ru,
    titleCe: item.title.ce ?? "",
    descriptionRu: item.description.ru,
    descriptionCe: item.description.ce ?? "",
    periodFrom: item.periodFrom == null ? "" : String(item.periodFrom),
    periodTo: item.periodTo == null ? "" : String(item.periodTo),
    status: item.status === "published" ? "published" : "draft",
  };
}
