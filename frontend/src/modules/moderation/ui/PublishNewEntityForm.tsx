import { zodResolver } from "@hookform/resolvers/zod";
import { useRef } from "react";
import { useForm, type UseFormReturn } from "react-hook-form";
import { z } from "zod";

import type { ModerationSubmission, PublishCommand } from "../domain/types";
import { MediaSelection } from "./SubmissionMedia";

const publishSchema = z.object({
  entityType: z.enum([
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
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, "Только a-z, 0-9 и дефисы"),
  title: z.string().trim().min(2, "Укажите название"),
  shortDescription: z.string().trim().min(10, "Минимум 10 символов"),
  fullDescription: z.string().trim().min(20, "Минимум 20 символов"),
  sourceTitle: z.string().trim().min(2, "Укажите источник"),
  sourceType: z.enum([
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
  ]),
  approvedMediaIds: z.array(z.uuid()),
  comment: z.string().trim().min(1, "Комментарий обязателен"),
});

type PublishValues = z.infer<typeof publishSchema>;

function SourceTypeSelect({ form }: { form: UseFormReturn<PublishValues> }) {
  return (
    <label>
      <span>Тип источника</span>
      <select {...form.register("sourceType")}>
        <option value="archive_document">Архивный документ</option>
        <option value="book">Книга</option>
        <option value="scientific_article">Научная статья</option>
        <option value="museum_material">Музейный материал</option>
        <option value="official_publication">Официальная публикация</option>
        <option value="photo">Фотография</option>
        <option value="audio">Аудиозапись</option>
        <option value="video">Видеозапись</option>
        <option value="oral_testimony">Устное свидетельство</option>
        <option value="web_resource">Веб-ресурс</option>
      </select>
    </label>
  );
}

function buildPublishInput(
  submission: ModerationSubmission,
  values: PublishValues,
  key: string,
): PublishCommand {
  return {
    expectedVersion: submission.version,
    idempotencyKey: key,
    action: "create_entity",
    payload: {
      entity: {
        type: values.entityType,
        slug: values.slug,
        title: { ru: values.title, ce: null },
        shortDescription: { ru: values.shortDescription, ce: null },
        fullDescription: { ru: values.fullDescription, ce: null },
        coordinates: null,
        periodFrom: null,
        periodTo: null,
        districtId: null,
      },
      relations: [],
      sources: [
        {
          title: values.sourceTitle,
          type: values.sourceType,
          author: submission.authorName,
          publisher: null,
          publicationYear: null,
          url: null,
          archiveReference: null,
          description: submission.sourceDescription,
        },
      ],
      approvedMediaIds: values.approvedMediaIds,
    },
    comment: values.comment,
  };
}

function PublishFields({ form }: { form: UseFormReturn<PublishValues> }) {
  const fields = [
    ["slug", "Slug"],
    ["title", "Название"],
    ["shortDescription", "Краткое описание"],
    ["sourceTitle", "Проверенный источник"],
    ["comment", "Комментарий решения"],
  ] as const;
  return (
    <>
      <label>
        <span>Тип сущности</span>
        <select {...form.register("entityType")}>
          <option value="settlement">Населённый пункт</option>
          <option value="person">Персона</option>
          <option value="event">Событие</option>
          <option value="landmark">Достопримечательность</option>
          <option value="natural_object">Природный объект</option>
          <option value="cultural_object">Культурный объект</option>
          <option value="organization">Организация</option>
          <option value="university_object">Университетский объект</option>
          <option value="artifact">Артефакт</option>
        </select>
      </label>
      <SourceTypeSelect form={form} />
      {fields.map(([name, label]) => (
        <label key={name}>
          <span>{label}</span>
          <input
            aria-invalid={Boolean(form.formState.errors[name])}
            {...form.register(name)}
          />
          <small role="alert">{form.formState.errors[name]?.message}</small>
        </label>
      ))}
      <label>
        <span>Полное описание</span>
        <textarea
          rows={5}
          aria-invalid={Boolean(form.formState.errors.fullDescription)}
          {...form.register("fullDescription")}
        />
        <small role="alert">
          {form.formState.errors.fullDescription?.message}
        </small>
      </label>
    </>
  );
}

interface Props {
  submission: ModerationSubmission;
  pending: boolean;
  errorMessage: string | null;
  onPublish: (input: PublishCommand) => Promise<unknown>;
}

export function PublishNewEntityForm({
  submission,
  pending,
  errorMessage,
  onPublish,
}: Props) {
  const idempotencyKey = useRef(crypto.randomUUID());
  const form = useForm<PublishValues>({
    resolver: zodResolver(publishSchema),
    defaultValues: {
      entityType: "landmark",
      slug: "new-history-entity",
      title: submission.title,
      shortDescription: submission.description.slice(0, 120),
      fullDescription: submission.description,
      sourceTitle: submission.sourceDescription,
      sourceType: "archive_document",
      approvedMediaIds: [],
      comment: "Материал и источник проверены",
    },
  });
  async function submit(values: PublishValues) {
    if (!window.confirm("Опубликовать материал и изменить публичный каталог?"))
      return;
    try {
      await onPublish(
        buildPublishInput(submission, values, idempotencyKey.current),
      );
    } catch {
      /* visible typed error keeps values/key */
    }
  }
  return (
    <form
      className="mod-publish-form"
      onSubmit={(event) => void form.handleSubmit(submit)(event)}
      noValidate
    >
      <div className="mod-section-heading">
        <h3>Опубликовать новую сущность</h3>
        <span>create_entity</span>
      </div>
      <PublishFields form={form} />
      <MediaSelection media={submission.media} register={form.register} />
      {errorMessage ? <p role="alert">{errorMessage}</p> : null}
      <button type="submit" disabled={pending}>
        {pending ? "Публикуем…" : "Опубликовать атомарно"}
      </button>
    </form>
  );
}
