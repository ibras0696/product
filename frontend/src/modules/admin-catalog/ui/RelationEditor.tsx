import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import type { AdminRelationView, RelationInput } from "../domain/catalog";
import {
  relationDefaults,
  relationInput,
  relationSchema,
  relationTypes,
  type RelationFormValues,
} from "./relationForm";
import { resourceError } from "./resourceMessages";

interface Props {
  relation: AdminRelationView | null;
  onSave: (input: RelationInput) => Promise<unknown>;
  onCancel: () => void;
}

function Field({
  form,
  name,
  label,
}: {
  form: ReturnType<typeof useForm<RelationFormValues>>;
  name: keyof RelationFormValues;
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

export function RelationEditor({ relation, onSave, onCancel }: Props) {
  const form = useForm<RelationFormValues>({
    resolver: zodResolver(relationSchema),
    defaultValues: relationDefaults(relation),
  });
  const submit = form.handleSubmit(async (values) => {
    form.clearErrors("root");
    try {
      await onSave(relationInput(values));
    } catch (error) {
      form.setError("root", {
        message: resourceError(error, "Не удалось сохранить связь."),
      });
    }
  });
  return (
    <form
      className="catalog-editor"
      aria-label="Редактор связи"
      onSubmit={(event) => void submit(event)}
    >
      <div className="catalog-heading">
        <h3>{relation ? "Изменение связи" : "Новая связь"}</h3>
        <span>Ожидаемая версия {relation?.version ?? 0}</span>
      </div>
      {form.formState.errors.root?.message ? (
        <p role="alert">{form.formState.errors.root.message}</p>
      ) : null}
      <div className="catalog-editor__fields">
        <Field
          form={form}
          name="sourceEntityId"
          label="UUID исходной сущности"
        />
        <Field
          form={form}
          name="targetEntityId"
          label="UUID целевой сущности"
        />
        <label>
          Тип связи
          <select {...form.register("type")}>
            {relationTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </label>
        <Field form={form} name="titleRu" label="Название (русский)" />
        <Field form={form} name="titleCe" label="Название (чеченский)" />
        <Field form={form} name="descriptionRu" label="Описание (русский)" />
        <Field form={form} name="descriptionCe" label="Описание (чеченский)" />
        <Field form={form} name="periodFrom" label="Период с" />
        <Field form={form} name="periodTo" label="Период по" />
        <label>
          Статус
          <select {...form.register("status")}>
            <option value="draft">Черновик</option>
            <option value="published">Опубликовано</option>
          </select>
        </label>
      </div>
      {relation ? (
        <p>Исходную и целевую сущности backend PATCH не изменяет.</p>
      ) : null}
      <div className="catalog-actions">
        <button type="submit" disabled={form.formState.isSubmitting}>
          Сохранить связь
        </button>
        <button type="button" onClick={onCancel}>
          Отмена
        </button>
      </div>
    </form>
  );
}
