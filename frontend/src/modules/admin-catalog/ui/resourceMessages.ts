import { AdminCatalogError } from "../domain/catalog";

export function resourceError(error: unknown, fallback: string) {
  if (!(error instanceof AdminCatalogError)) return fallback;
  const messages: Partial<Record<AdminCatalogError["code"], string>> = {
    conflict: "Запись уже изменена. Обновите список перед повтором.",
    unauthorized: "Сессия завершилась. Войдите снова.",
    forbidden: "Недостаточно прав для этой операции.",
    source_required: error.message,
    validation_error: "Проверьте обязательные поля.",
    not_found: "Запись больше недоступна.",
  };
  return messages[error.code] ?? fallback;
}
