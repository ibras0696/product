import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import {
  AdminCatalogError,
  type AdminEntityView,
  type EntityInput,
} from "../domain/catalog";
import { EntityFields } from "./EntityFields";
import {
  entityDefaults,
  entityFormSchema,
  type EntityFormValues,
  toEntityInput,
} from "./entityForm";

interface EntityEditorProps {
  entity: AdminEntityView | null;
  onSave: (input: EntityInput) => Promise<unknown>;
  onCancel: () => void;
}

export function EntityEditor(props: EntityEditorProps) {
  const { entity } = props;
  const form = useForm<EntityFormValues>({
    resolver: zodResolver(entityFormSchema),
    defaultValues: entityDefaults(entity),
  });
  const submit = form.handleSubmit(async (values) => {
    form.clearErrors("root");
    try {
      await props.onSave(toEntityInput(values));
    } catch (error) {
      const message =
        error instanceof AdminCatalogError && error.code === "conflict"
          ? "Запись уже изменена. Ваши данные сохранены в форме — обновите список перед повтором."
          : error instanceof AdminCatalogError && error.code === "unauthorized"
            ? "Сессия завершилась. Войдите снова, данные останутся в форме."
            : error instanceof AdminCatalogError && error.code === "forbidden"
              ? "Недостаточно прав для сохранения записи."
              : error instanceof AdminCatalogError &&
                  error.code === "source_required"
                ? error.message
                : "Не удалось сохранить запись.";
      form.setError("root", { message });
    }
  });
  return (
    <form
      className="catalog-editor"
      onSubmit={(event) => {
        void submit(event);
      }}
    >
      <div className="catalog-heading">
        <h2>{entity ? "Редактирование" : "Новая сущность"}</h2>
        <span>Ожидаемая версия {entity?.version ?? 0}</span>
      </div>
      {form.formState.errors.root?.message ? (
        <div role="alert">
          <p>{form.formState.errors.root.message}</p>
          <button
            type="button"
            onClick={() => {
              props.onCancel();
            }}
          >
            Закрыть форму и обновить список
          </button>
        </div>
      ) : null}
      <EntityFields form={form} entity={entity} />
      <div className="catalog-actions">
        <button type="submit" disabled={form.formState.isSubmitting}>
          Сохранить
        </button>
        <button
          type="button"
          onClick={() => {
            props.onCancel();
          }}
        >
          Отмена
        </button>
      </div>
    </form>
  );
}
