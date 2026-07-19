import { MagnifyingGlassIcon } from "@phosphor-icons/react";
import type { ReactNode } from "react";

import type { SearchItemViewModel } from "../api/viewModels";

interface ExplorerHeaderProps {
  accountSlot?: ReactNode;
  query: string;
  suggestions: SearchItemViewModel[];
  searchPending: boolean;
  onQueryChange: (value: string) => void;
  onSuggestionSelect: (id: string) => void;
}

export function ExplorerHeader({
  query,
  suggestions,
  searchPending,
  onQueryChange,
  onSuggestionSelect,
}: ExplorerHeaderProps) {
  const suggestionsVisible = query.trim().length >= 2;
  return (
    <header className="hx-header">
      <a
        className="hx-brand"
        href="#atlas"
        aria-label="Паутина истории Чечни, к карте"
      >
        Паутина истории Чечни
      </a>
      <div className="hx-search">
        <MagnifyingGlassIcon size={14} aria-hidden="true" />
        <label className="hx-visually-hidden" htmlFor="atlas-search">
          Поиск по атласу
        </label>
        <input
          id="atlas-search"
          type="search"
          name="atlas-search"
          autoComplete="off"
          value={query}
          onChange={(event) => {
            onQueryChange(event.target.value);
          }}
          placeholder="Поиск по местам, героям, событиям…"
        />
        {suggestionsVisible ? (
          <div className="hx-search-results" id="atlas-search-results">
            {searchPending ? <span role="status">Ищем…</span> : null}
            {!searchPending && suggestions.length === 0 ? (
              <span role="status">Совпадений не найдено</span>
            ) : null}
            {suggestions.length > 0 ? (
              <ul aria-label="Результаты поиска">
                {suggestions.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => {
                        onSuggestionSelect(item.id);
                      }}
                    >
                      <strong>{item.title.ru}</strong>
                      <span>{item.subtitle}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
      </div>
      <nav className="hx-header-actions" aria-label="Действия проекта">
        <a className="hx-project-action" href="#about">
          <MagnifyingGlassIcon size={14} aria-hidden="true" /> О проекте
        </a>
        <a className="hx-source-action" href="/contribute">
          Добавить источник
        </a>
      </nav>
    </header>
  );
}
