import { z } from "zod";

import type { AdminSourceView, SourceInput } from "../domain/catalog";

export const sourceTypes = [
  "archive_document",
  "book",
  "scientific_article",
  "museum_material",
  "official_publication",
  "photo",
  "audio",
  "video",
  "oral_testimony",
  "web_resource",
] as const;

export const sourceSchema = z.object({
  title: z.string().trim().min(1, "Укажите название").max(500),
  type: z.enum(sourceTypes),
  author: z.string().trim().max(300),
  publisher: z.string().trim().max(300),
  publicationYear: z
    .string()
    .trim()
    .refine(
      (value) => value === "" || Number.isInteger(Number(value)),
      "Укажите целый год",
    ),
  url: z.string().trim().max(2048),
  archiveReference: z.string().trim().max(500),
  description: z.string().trim().max(10_000),
  isVerified: z.boolean(),
  status: z.enum(["draft", "published"]),
});

export type SourceFormValues = z.infer<typeof sourceSchema>;
const nullable = (value: string) => (value === "" ? null : value);

export function sourceInput(values: SourceFormValues): SourceInput {
  return {
    title: values.title,
    type: values.type,
    author: nullable(values.author),
    publisher: nullable(values.publisher),
    publicationYear:
      values.publicationYear === "" ? null : Number(values.publicationYear),
    url: nullable(values.url),
    archiveReference: nullable(values.archiveReference),
    description: values.description,
    isVerified: values.isVerified,
    status: values.status,
  };
}

export function sourceDefaults(item: AdminSourceView | null): SourceFormValues {
  if (!item) return emptySourceValues();
  return {
    title: item.title,
    type: item.type,
    author: item.author ?? "",
    publisher: item.publisher ?? "",
    publicationYear:
      item.publicationYear === null ? "" : String(item.publicationYear),
    url: item.url ?? "",
    archiveReference: item.archiveReference ?? "",
    description: item.description,
    isVerified: item.isVerified,
    status: item.status === "published" ? "published" : "draft",
  };
}

function emptySourceValues(): SourceFormValues {
  return {
    title: "",
    type: "book",
    author: "",
    publisher: "",
    publicationYear: "",
    url: "",
    archiveReference: "",
    description: "",
    isVerified: false,
    status: "draft",
  };
}
