import { zodResolver } from "@hookform/resolvers/zod";
import { useRef } from "react";
import { useForm, useWatch, type UseFormReturn } from "react-hook-form";
import { z } from "zod";

import type { ModerationSubmission, PublishCommand } from "../domain/types";
import { MediaSelection } from "./SubmissionMedia";

interface Props {
  submission: ModerationSubmission;
  pending: boolean;
  errorMessage: string | null;
  onPublish: (input: PublishCommand) => Promise<unknown>;
}

const mediaSchema = z.object({
  targetEntityId: z.uuid("Укажите UUID сущности"),
  approvedMediaIds: z
    .array(z.uuid())
    .min(1, "Выберите хотя бы одну фотографию"),
  comment: z.string().trim().min(1, "Комментарий обязателен"),
});

export function PublishMediaForm(props: Props) {
  const { submission } = props;
  const key = useRef(crypto.randomUUID());
  const form = useForm<z.infer<typeof mediaSchema>>({
    resolver: zodResolver(mediaSchema),
    defaultValues: {
      targetEntityId: submission.relatedEntityId ?? "",
      approvedMediaIds: [],
      comment: "Фотографии проверены",
    },
  });
  async function submit(values: z.infer<typeof mediaSchema>) {
    if (!window.confirm("Опубликовать выбранные фотографии?")) return;
    try {
      await props.onPublish({
        action: "publish_media",
        expectedVersion: submission.version,
        idempotencyKey: key.current,
        comment: values.comment,
        payload: {
          targetEntityId: values.targetEntityId,
          approvedMediaIds: values.approvedMediaIds,
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
      <h3>Опубликовать фотографии</h3>
      <label>
        <span>UUID целевой сущности</span>
        <input {...form.register("targetEntityId")} />
        <small role="alert">
          {form.formState.errors.targetEntityId?.message}
        </small>
      </label>
      <MediaSelection media={submission.media} register={form.register} />
      <small role="alert">
        {form.formState.errors.approvedMediaIds?.message}
      </small>
      {submission.media.length === 0 ? (
        <p className="mod-empty">
          В заявке нет фотографий, доступных для публикации.
        </p>
      ) : null}
      <label>
        <span>Комментарий решения</span>
        <input {...form.register("comment")} />
      </label>
      {props.errorMessage ? <p role="alert">{props.errorMessage}</p> : null}
      <button
        type="submit"
        disabled={props.pending || submission.media.length === 0}
      >
        {props.pending ? "Публикуем…" : "Опубликовать фотографии"}
      </button>
    </form>
  );
}

const reportSchema = z
  .object({
    mode: z.enum(["resolution_only", "patch_description", "archive"]),
    resolution: z.string().trim().min(5, "Опишите результат проверки"),
    patchDescription: z.string(),
    archiveEntityId: z.string(),
    comment: z.string().trim().min(1, "Комментарий обязателен"),
  })
  .superRefine((values, context) => {
    if (
      values.mode === "patch_description" &&
      values.patchDescription.trim().length < 20
    ) {
      context.addIssue({
        code: "custom",
        path: ["patchDescription"],
        message: "Минимум 20 символов",
      });
    }
    if (
      values.mode === "archive" &&
      !z.uuid().safeParse(values.archiveEntityId).success
    ) {
      context.addIssue({
        code: "custom",
        path: ["archiveEntityId"],
        message: "Укажите UUID архивируемой сущности",
      });
    }
  });

type ReportValues = z.infer<typeof reportSchema>;

function ReportModeOptions({ form }: { form: UseFormReturn<ReportValues> }) {
  return (
    <fieldset className="mod-publish-choice">
      <legend>Действие с каталогом</legend>
      <label>
        <input
          type="radio"
          value="resolution_only"
          {...form.register("mode")}
        />
        Только зафиксировать результат
      </label>
      <label>
        <input
          type="radio"
          value="patch_description"
          {...form.register("mode")}
        />
        Обновить полное описание
      </label>
      <label>
        <input type="radio" value="archive" {...form.register("mode")} />
        Архивировать сущность
      </label>
    </fieldset>
  );
}

function ReportModeField({
  form,
  mode,
}: {
  form: UseFormReturn<ReportValues>;
  mode: ReportValues["mode"];
}) {
  if (mode === "patch_description") {
    return (
      <label>
        <span>Новое полное описание</span>
        <textarea rows={5} {...form.register("patchDescription")} />
        <small role="alert">
          {form.formState.errors.patchDescription?.message}
        </small>
      </label>
    );
  }
  if (mode === "archive") {
    return (
      <label>
        <span>UUID архивируемой сущности</span>
        <input {...form.register("archiveEntityId")} />
        <small role="alert">
          {form.formState.errors.archiveEntityId?.message}
        </small>
      </label>
    );
  }
  return null;
}

export function ResolveReportForm(props: Props) {
  const { submission } = props;
  const key = useRef(crypto.randomUUID());
  const form = useForm<ReportValues>({
    resolver: zodResolver(reportSchema),
    defaultValues: {
      mode: "resolution_only",
      resolution: submission.description,
      patchDescription: submission.description,
      archiveEntityId: submission.relatedEntityId ?? "",
      comment: "Сообщение проверено и разрешено",
    },
  });
  const mode = useWatch({ control: form.control, name: "mode" });
  async function submit(values: ReportValues) {
    if (!window.confirm("Завершить проверку сообщения об ошибке?")) return;
    try {
      await props.onPublish({
        action: "resolve_report",
        expectedVersion: submission.version,
        idempotencyKey: key.current,
        comment: values.comment,
        payload: {
          resolution: values.resolution,
          entityPatch:
            values.mode === "patch_description"
              ? { fullDescription: { ru: values.patchDescription, ce: null } }
              : undefined,
          archiveEntityId:
            values.mode === "archive" ? values.archiveEntityId : undefined,
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
      <h3>Разрешить сообщение об ошибке</h3>
      <label>
        <span>Результат проверки</span>
        <textarea rows={4} {...form.register("resolution")} />
      </label>
      <ReportModeOptions form={form} />
      <ReportModeField form={form} mode={mode} />
      <label>
        <span>Комментарий решения</span>
        <input {...form.register("comment")} />
      </label>
      {props.errorMessage ? <p role="alert">{props.errorMessage}</p> : null}
      <button type="submit" disabled={props.pending}>
        {props.pending ? "Публикуем…" : "Завершить проверку"}
      </button>
    </form>
  );
}
