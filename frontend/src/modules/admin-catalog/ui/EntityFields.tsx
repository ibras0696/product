import type { FieldPath, UseFormReturn } from "react-hook-form";

import type { AdminEntityView } from "../domain/catalog";
import type { EntityFormValues } from "./entityForm";

const entityTypes = [
  ["settlement", "Населённый пункт"],
  ["person", "Личность"],
  ["event", "Событие"],
  ["landmark", "Достопримечательность"],
  ["natural_object", "Природный объект"],
  ["cultural_object", "Культурный объект"],
  ["organization", "Организация"],
  ["university_object", "Объект университета"],
  ["artifact", "Артефакт"],
] as const;

function TextField({
  form,
  name,
  label,
  multiline = false,
}: {
  form: UseFormReturn<EntityFormValues>;
  name: FieldPath<EntityFormValues>;
  label: string;
  multiline?: boolean;
}) {
  const error = form.formState.errors[name]?.message;
  const id = `catalog-${name}`;
  return (
    <label htmlFor={id}>
      {label}
      {multiline ? (
        <textarea
          id={id}
          {...form.register(name)}
          aria-invalid={Boolean(error)}
        />
      ) : (
        <input id={id} {...form.register(name)} aria-invalid={Boolean(error)} />
      )}
      {error ? <small role="alert">{error}</small> : null}
    </label>
  );
}

function EntityTypeField({
  form,
  disabled,
}: {
  form: UseFormReturn<EntityFormValues>;
  disabled: boolean;
}) {
  if (disabled) {
    const value = form.getValues("type");
    const label = entityTypes.find(([type]) => type === value)?.[1] ?? value;
    return (
      <label>
        Тип
        <input type="hidden" {...form.register("type")} />
        <span>{label} (тип нельзя изменить)</span>
      </label>
    );
  }
  return (
    <label>
      Тип
      <select {...form.register("type")} disabled={disabled}>
        {entityTypes.map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function EntityFields({
  form,
  entity,
}: {
  form: UseFormReturn<EntityFormValues>;
  entity: AdminEntityView | null;
}) {
  return (
    <div className="catalog-editor__fields">
      <TextField form={form} name="titleRu" label="Название (русский)" />
      <TextField
        form={form}
        name="titleCe"
        label="Название (чеченский, необязательно)"
      />
      <TextField form={form} name="slug" label="Slug" />
      <EntityTypeField form={form} disabled={Boolean(entity)} />
      <TextField
        form={form}
        name="shortDescriptionRu"
        label="Краткое описание (русский)"
        multiline
      />
      <TextField
        form={form}
        name="shortDescriptionCe"
        label="Краткое описание (чеченский)"
        multiline
      />
      <TextField
        form={form}
        name="fullDescriptionRu"
        label="Полное описание (русский)"
        multiline
      />
      <TextField
        form={form}
        name="fullDescriptionCe"
        label="Полное описание (чеченский)"
        multiline
      />
      <TextField form={form} name="latitude" label="Широта (необязательно)" />
      <TextField form={form} name="longitude" label="Долгота (необязательно)" />
      <TextField
        form={form}
        name="periodFrom"
        label="Период с (необязательно)"
      />
      <TextField
        form={form}
        name="periodTo"
        label="Период по (необязательно)"
      />
      <TextField
        form={form}
        name="districtId"
        label="UUID района (необязательно)"
      />
      <label>
        Статус
        <select {...form.register("status")}>
          <option value="draft">Черновик</option>
          <option
            value="published"
            disabled={!entity || entity.sourcesCount === 0}
          >
            Опубликовано
          </option>
        </select>
      </label>
    </div>
  );
}
