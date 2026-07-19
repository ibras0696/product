import { zodResolver } from "@hookform/resolvers/zod";
import { useRef } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import type { ModerationSubmission, PublishCommand } from "../domain/types";
import {
  relationOptions,
  relationTypeValues,
  sourceOptions,
  sourceTypeValues,
} from "./publishOptions";

interface Props {
  submission: ModerationSubmission;
  pending: boolean;
  errorMessage: string | null;
  onPublish: (input: PublishCommand) => Promise<unknown>;
}

const relationSchema = z.object({
  sourceEntityId: z.uuid("Укажите UUID исходной сущности"),
  targetEntityId: z.uuid("Укажите UUID целевой сущности"),
  relationType: z.enum(relationTypeValues),
  title: z.string().trim().min(2, "Укажите название связи"),
  description: z.string().trim().min(10, "Минимум 10 символов"),
  sourceTitle: z.string().trim().min(2, "Укажите источник"),
  comment: z.string().trim().min(1, "Комментарий обязателен"),
});

type RelationValues = z.infer<typeof relationSchema>;

function RelationFields({
  form,
}: {
  form: ReturnType<typeof useForm<RelationValues>>;
}) {
  return (
    <>
      <label>
        <span>UUID исходной сущности</span>
        <input {...form.register("sourceEntityId")} />
        <small role="alert">
          {form.formState.errors.sourceEntityId?.message}
        </small>
      </label>
      <label>
        <span>UUID целевой сущности</span>
        <input {...form.register("targetEntityId")} />
        <small role="alert">
          {form.formState.errors.targetEntityId?.message}
        </small>
      </label>
      <label>
        <span>Тип связи</span>
        <select {...form.register("relationType")}>
          {relationOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Название связи</span>
        <input {...form.register("title")} />
      </label>
      <label>
        <span>Описание связи</span>
        <textarea rows={4} {...form.register("description")} />
      </label>
      <label>
        <span>Проверенный источник</span>
        <input {...form.register("sourceTitle")} />
      </label>
      <label>
        <span>Комментарий решения</span>
        <input {...form.register("comment")} />
      </label>
    </>
  );
}

export function PublishRelationForm(props: Props) {
  const { submission } = props;
  const key = useRef(crypto.randomUUID());
  const form = useForm<RelationValues>({
    resolver: zodResolver(relationSchema),
    defaultValues: {
      sourceEntityId: submission.relatedEntityId ?? "",
      targetEntityId: "",
      relationType: "connected_with",
      title: submission.title,
      description: submission.description,
      sourceTitle: submission.sourceDescription,
      comment: "Связь и источник проверены",
    },
  });
  async function submit(values: RelationValues) {
    if (!window.confirm("Опубликовать новую связь?")) return;
    const source = {
      title: values.sourceTitle,
      type: "archive_document" as const,
      author: submission.authorName,
      publisher: null,
      publicationYear: null,
      url: null,
      archiveReference: null,
      description: submission.sourceDescription,
    };
    try {
      await props.onPublish({
        action: "create_relation",
        expectedVersion: submission.version,
        idempotencyKey: key.current,
        comment: values.comment,
        payload: {
          relation: {
            sourceEntityId: values.sourceEntityId,
            targetEntityId: values.targetEntityId,
            type: values.relationType,
            title: { ru: values.title, ce: null },
            description: { ru: values.description, ce: null },
            periodFrom: null,
            periodTo: null,
          },
          sources: [source],
        },
      });
    } catch {
      /* preserve values and idempotency key */
    }
  }
  return (
    <form
      className="mod-publish-form"
      onSubmit={(event) => void form.handleSubmit(submit)(event)}
      noValidate
    >
      <h3>Опубликовать новую связь</h3>
      <RelationFields form={form} />
      {props.errorMessage ? <p role="alert">{props.errorMessage}</p> : null}
      <button type="submit" disabled={props.pending}>
        {props.pending ? "Публикуем…" : "Опубликовать связь"}
      </button>
    </form>
  );
}

const sourceSchema = z.object({
  targetType: z.enum(["entity", "relation"]),
  targetId: z.uuid("Укажите UUID объекта"),
  title: z.string().trim().min(2, "Укажите название источника"),
  sourceType: z.enum(sourceTypeValues),
  description: z.string().trim().min(5, "Опишите источник"),
  comment: z.string().trim().min(1, "Комментарий обязателен"),
});

type SourceValues = z.infer<typeof sourceSchema>;

function SourceFields({
  form,
}: {
  form: ReturnType<typeof useForm<SourceValues>>;
}) {
  return (
    <>
      <label>
        <span>Тип объекта</span>
        <select {...form.register("targetType")}>
          <option value="entity">Сущность</option>
          <option value="relation">Связь</option>
        </select>
      </label>
      <label>
        <span>UUID объекта</span>
        <input {...form.register("targetId")} />
        <small role="alert">{form.formState.errors.targetId?.message}</small>
      </label>
      <label>
        <span>Название источника</span>
        <input {...form.register("title")} />
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
      <label>
        <span>Описание источника</span>
        <textarea rows={4} {...form.register("description")} />
      </label>
      <label>
        <span>Комментарий решения</span>
        <input {...form.register("comment")} />
      </label>
    </>
  );
}

export function PublishSourceForm(props: Props) {
  const { submission } = props;
  const key = useRef(crypto.randomUUID());
  const form = useForm<SourceValues>({
    resolver: zodResolver(sourceSchema),
    defaultValues: {
      targetType: "entity",
      targetId: submission.relatedEntityId ?? "",
      title: submission.title,
      sourceType: "archive_document",
      description: submission.sourceDescription,
      comment: "Источник проверен",
    },
  });
  async function submit(values: SourceValues) {
    if (!window.confirm("Добавить проверенный источник?")) return;
    try {
      await props.onPublish({
        action: "add_source",
        expectedVersion: submission.version,
        idempotencyKey: key.current,
        comment: values.comment,
        payload: {
          targetType: values.targetType,
          targetId: values.targetId,
          source: {
            title: values.title,
            type: values.sourceType,
            author: submission.authorName,
            publisher: null,
            publicationYear: null,
            url: null,
            archiveReference: null,
            description: values.description,
          },
        },
      });
    } catch {
      /* preserve values and idempotency key */
    }
  }
  return (
    <form
      className="mod-publish-form"
      onSubmit={(event) => void form.handleSubmit(submit)(event)}
      noValidate
    >
      <h3>Добавить проверенный источник</h3>
      <SourceFields form={form} />
      {props.errorMessage ? <p role="alert">{props.errorMessage}</p> : null}
      <button type="submit" disabled={props.pending}>
        {props.pending ? "Публикуем…" : "Добавить источник"}
      </button>
    </form>
  );
}
