import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import type { AdminSourceView, SourceInput } from "../domain/catalog";
import { resourceError } from "./resourceMessages";
import {
  sourceDefaults,
  sourceInput,
  sourceSchema,
  sourceTypes,
  type SourceFormValues,
} from "./sourceForm";

interface Props {
  source: AdminSourceView | null;
  onSave: (input: SourceInput) => Promise<unknown>;
  onCancel: () => void;
}

function Field({
  form,
  name,
  label,
}: {
  form: ReturnType<typeof useForm<SourceFormValues>>;
  name: keyof SourceFormValues;
  label: string;
}) {
  const error = form.formState.errors[name]?.message;
  return (
    <label>
      {label}
      <input {...form.register(name)} aria-invalid={Boolean(error)} />
      {error ? <small role="alert">{error}</small> : null}
    </label>
  );
}

export function SourceEditor({ source, onSave, onCancel }: Props) {
  const form = useForm<SourceFormValues>({
    resolver: zodResolver(sourceSchema),
    defaultValues: sourceDefaults(source),
  });
  const submit = form.handleSubmit(async (values) => {
    form.clearErrors("root");
    try {
      await onSave(sourceInput(values));
    } catch (error) {
      form.setError("root", {
        message: resourceError(error, "Не удалось сохранить источник."),
      });
    }
  });
  return (
    <form
      className="catalog-editor"
      aria-label="Редактор источника"
      onSubmit={(event) => void submit(event)}
    >
      <div className="catalog-heading">
        <h3>{source ? "Изменение источника" : "Новый источник"}</h3>
        <span>Ожидаемая версия {source?.version ?? 0}</span>
      </div>
      {form.formState.errors.root?.message ? (
        <p role="alert">{form.formState.errors.root.message}</p>
      ) : null}
      <div className="catalog-editor__fields">
        <Field form={form} name="title" label="Название источника" />
        <label>
          Тип источника
          <select {...form.register("type")}>
            {sourceTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </label>
        <Field form={form} name="author" label="Автор" />
        <Field form={form} name="publisher" label="Издатель" />
        <Field form={form} name="publicationYear" label="Год публикации" />
        <Field form={form} name="url" label="URL" />
        <Field form={form} name="archiveReference" label="Архивный шифр" />
        <label>
          Описание
          <textarea {...form.register("description")} />
        </label>
        <label className="catalog-check">
          <input type="checkbox" {...form.register("isVerified")} />
          Источник проверен
        </label>
        <label>
          Статус
          <select {...form.register("status")}>
            <option value="draft">Черновик</option>
            <option value="published">Опубликовано</option>
          </select>
        </label>
      </div>
      <div className="catalog-actions">
        <button type="submit" disabled={form.formState.isSubmitting}>
          Сохранить источник
        </button>
        <button type="button" onClick={onCancel}>
          Отмена
        </button>
      </div>
    </form>
  );
}
