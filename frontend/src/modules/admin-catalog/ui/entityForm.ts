import { z } from "zod";

import type { AdminEntityView, EntityInput } from "../domain/catalog";

const optionalNumber = z
  .string()
  .trim()
  .refine(
    (value) => value === "" || Number.isFinite(Number(value)),
    "Укажите число",
  );
const optionalInteger = optionalNumber.refine(
  (value) => value === "" || Number.isInteger(Number(value)),
  "Укажите целый год",
);

export const entityFormSchema = z
  .object({
    type: z.enum([
      "settlement",
      "person",
      "event",
      "landmark",
      "natural_object",
      "cultural_object",
      "organization",
      "university_object",
      "artifact",
    ]),
    slug: z
      .string()
      .trim()
      .min(1, "Укажите slug")
      .max(160)
      .regex(
        /^[a-z0-9]+(?:-[a-z0-9]+)*$/,
        "Латиница, цифры и одиночные дефисы",
      ),
    titleRu: z.string().trim().min(1, "Укажите название").max(300),
    titleCe: z.string().trim().max(300),
    shortDescriptionRu: z
      .string()
      .trim()
      .min(1, "Укажите краткое описание")
      .max(300),
    shortDescriptionCe: z.string().trim().max(300),
    fullDescriptionRu: z
      .string()
      .trim()
      .min(1, "Укажите полное описание")
      .max(300),
    fullDescriptionCe: z.string().trim().max(300),
    latitude: optionalNumber,
    longitude: optionalNumber,
    periodFrom: optionalInteger,
    periodTo: optionalInteger,
    districtId: z
      .string()
      .trim()
      .pipe(z.uuid("Укажите UUID района").or(z.literal(""))),
    status: z.enum(["draft", "published"]),
  })
  .refine(
    ({ latitude, longitude }) => (latitude === "") === (longitude === ""),
    { message: "Укажите обе координаты", path: ["longitude"] },
  )
  .refine(
    ({ latitude }) => latitude === "" || Math.abs(Number(latitude)) <= 90,
    { message: "Широта должна быть от −90 до 90", path: ["latitude"] },
  )
  .refine(
    ({ longitude }) => longitude === "" || Math.abs(Number(longitude)) <= 180,
    { message: "Долгота должна быть от −180 до 180", path: ["longitude"] },
  )
  .refine(
    ({ periodFrom, periodTo }) =>
      periodFrom === "" ||
      periodTo === "" ||
      Number(periodFrom) <= Number(periodTo),
    { message: "Начало периода не может быть позже конца", path: ["periodTo"] },
  );

export type EntityFormValues = z.infer<typeof entityFormSchema>;

function text(ru: string, ce: string) {
  return { ru: ru.trim(), ce: ce.trim() || null };
}

function nullableNumber(value: string) {
  return value.trim() === "" ? null : Number(value);
}

function numberText(value: number | null | undefined) {
  return value == null ? "" : String(value);
}

export function toEntityInput(values: EntityFormValues): EntityInput {
  const latitude = nullableNumber(values.latitude);
  const longitude = nullableNumber(values.longitude);
  return {
    type: values.type,
    slug: values.slug.trim(),
    title: text(values.titleRu, values.titleCe),
    shortDescription: text(
      values.shortDescriptionRu,
      values.shortDescriptionCe,
    ),
    fullDescription: text(values.fullDescriptionRu, values.fullDescriptionCe),
    coordinates:
      latitude === null || longitude === null ? null : { latitude, longitude },
    periodFrom: nullableNumber(values.periodFrom),
    periodTo: nullableNumber(values.periodTo),
    districtId: values.districtId.trim() || null,
    status: values.status,
  };
}

export function entityDefaults(
  entity: AdminEntityView | null,
): EntityFormValues {
  if (!entity) return emptyEntityDefaults();
  return {
    type: entity.type,
    slug: entity.slug,
    titleRu: entity.title.ru,
    titleCe: entity.title.ce ?? "",
    shortDescriptionRu: entity.shortDescription.ru,
    shortDescriptionCe: entity.shortDescription.ce ?? "",
    fullDescriptionRu: entity.fullDescription.ru,
    fullDescriptionCe: entity.fullDescription.ce ?? "",
    latitude: numberText(entity.coordinates?.latitude),
    longitude: numberText(entity.coordinates?.longitude),
    periodFrom: numberText(entity.periodFrom),
    periodTo: numberText(entity.periodTo),
    districtId: entity.districtId ?? "",
    status: entity.status === "published" ? "published" : "draft",
  };
}

function emptyEntityDefaults(): EntityFormValues {
  return {
    type: "settlement",
    slug: "",
    titleRu: "",
    titleCe: "",
    shortDescriptionRu: "",
    shortDescriptionCe: "",
    fullDescriptionRu: "",
    fullDescriptionCe: "",
    latitude: "",
    longitude: "",
    periodFrom: "",
    periodTo: "",
    districtId: "",
    status: "draft",
  };
}
