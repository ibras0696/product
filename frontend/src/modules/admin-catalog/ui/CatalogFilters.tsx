import { useSearchParams } from "react-router-dom";
import type { SyntheticEvent } from "react";

import type { EntityListFilters } from "../domain/catalog";
import { updateCatalogUrl } from "../model/urlFilters";

function formValue(data: FormData, key: string) {
  const value = data.get(key);
  return typeof value === "string" ? value : "";
}

export function CatalogFilters({ filters }: { filters: EntityListFilters }) {
  const [, setParams] = useSearchParams();
  function apply(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setParams(
      (current) =>
        updateCatalogUrl(current, {
          query: formValue(data, "query"),
          type: formValue(data, "type"),
          status: formValue(data, "status"),
        }),
      { replace: true },
    );
  }
  return (
    <form
      className="catalog-filters"
      aria-label="Фильтры каталога"
      onSubmit={apply}
    >
      <label>
        Поиск
        <input name="query" defaultValue={filters.query} />
      </label>
      <label>
        Тип
        <select name="type" defaultValue={filters.type ?? ""}>
          <option value="">Все</option>
          <option value="settlement">Места</option>
          <option value="person">Личности</option>
          <option value="event">События</option>
          <option value="landmark">Объекты</option>
          <option value="natural_object">Природные объекты</option>
          <option value="cultural_object">Культурные объекты</option>
          <option value="organization">Организации</option>
          <option value="university_object">Объекты университета</option>
          <option value="artifact">Артефакты</option>
        </select>
      </label>
      <label>
        Статус
        <select name="status" defaultValue={filters.status ?? ""}>
          <option value="">Все</option>
          <option value="draft">Черновик</option>
          <option value="published">Опубликовано</option>
          <option value="archived">Архив</option>
        </select>
      </label>
      <button type="submit">Применить</button>
    </form>
  );
}
