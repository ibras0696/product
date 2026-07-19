import { zodResolver } from "@hookform/resolvers/zod";
import { useRef } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import type { ModerationSubmission, PublishCommand } from "../domain/types";
import { MediaSelection } from "./SubmissionMedia";
import { sourceOptions, sourceTypeValues } from "./publishOptions";

const schema = z.object({
  entityId: z.uuid("Укажите UUID сущности"),
  fullDescription: z.string().trim().min(20, "Минимум 20 символов"),
  sourceTitle: z.string().trim().min(2, "Укажите источник"),
  sourceType: z.enum(sourceTypeValues),
  approvedMediaIds: z.array(z.uuid()),
  comment: z.string().trim().min(1, "Комментарий обязателен"),
});

type Values = z.infer<typeof schema>;

interface Props {
  submission: ModerationSubmission;
  pending: boolean;
  errorMessage: string | null;
  onPublish: (input: PublishCommand) => Promise<unknown>;
}

function UpdateEntityFields({
  form,
  submission,
}: {
  form: ReturnType<typeof useForm<Values>>;
  submission: ModerationSubmission;
}) {
  return (
    <>
      <label>
        <span>UUID изменяемой сущности</span>
        <input
          aria-invalid={Boolean(form.formState.errors.entityId)}
          {...form.register("entityId")}
        />
        <small role="alert">{form.formState.errors.entityId?.message}</small>
      </label>
      <label>
        <span>Новое полное описание</span>
        <textarea
          rows={5}
          aria-invalid={Boolean(form.formState.errors.fullDescription)}
          {...form.register("fullDescription")}
        />
        <small role="alert">
          {form.formState.errors.fullDescription?.message}
        </small>
      </label>
      <label>
        <span>Проверенный источник</span>
        <input {...form.register("sourceTitle")} />
      </label>
      <label>
        <span>Тип источника</span>
        <select {...form.register("sourceType")}>
          {sourceOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <MediaSelection media={submission.media} register={form.register} />
    </>
  );
}

export function PublishUpdateEntityForm({
  submission,
  pending,
  errorMessage,
  onPublish,
}: Props) {
  const key = useRef(crypto.randomUUID());
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      entityId: submission.relatedEntityId ?? "",
      fullDescription: submission.description,
      sourceTitle: submission.sourceDescription,
      sourceType: "archive_document",
      approvedMediaIds: [],
      comment: "Изменения и источник проверены",
    },
  });
  async function submit(values: Values) {
    if (!window.confirm("Опубликовать изменения сущности?")) return;
    try {
      await onPublish({
        action: "update_entity",
        expectedVersion: submission.version,
        idempotencyKey: key.current,
        comment: values.comment,
        payload: {
          entityId: values.entityId,
          entityPatch: {
            fullDescription: { ru: values.fullDescription, ce: null },
          },
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
      });
    } catch {
      /* typed error is rendered without resetting the stable key */
    }
  }
  return (
    <form
      className="mod-publish-form"
      onSubmit={(event) => void form.handleSubmit(submit)(event)}
      noValidate
    >
      <h3>Опубликовать обновление сущности</h3>
      <UpdateEntityFields form={form} submission={submission} />
      <label>
        <span>Комментарий решения</span>
        <input {...form.register("comment")} />
      </label>
      {errorMessage ? <p role="alert">{errorMessage}</p> : null}
      <button type="submit" disabled={pending}>
        {pending ? "Публикуем…" : "Опубликовать обновление"}
      </button>
    </form>
  );
}
