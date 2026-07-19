import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { ExplorerHeader } from "./ExplorerHeader";

it("keeps the public map header free of an admin entry point", () => {
  render(
    <ExplorerHeader
      accountSlot={<a href="/admin">Администрирование</a>}
      query=""
      suggestions={[]}
      searchPending={false}
      onQueryChange={vi.fn()}
      onSuggestionSelect={vi.fn()}
    />,
  );

  expect(
    screen.queryByRole("link", { name: "Профиль" }),
  ).not.toBeInTheDocument();
  expect(document.querySelector('a[href="/admin"]')).not.toBeInTheDocument();
  expect(screen.queryByText("Администрирование")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Добавить источник" })).toBeVisible();
});
