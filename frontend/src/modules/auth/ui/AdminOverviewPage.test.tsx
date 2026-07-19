import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AdminOverviewPage } from "./AdminOverviewPage";

describe("AdminOverviewPage", () => {
  it("provides direct navigation to every editorial workspace", () => {
    render(
      <MemoryRouter>
        <AdminOverviewPage />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: "Рабочее пространство редакции" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Заявки/ })).toHaveAttribute(
      "href",
      "/admin/submissions",
    );
    expect(screen.getByRole("link", { name: /Каталог/ })).toHaveAttribute(
      "href",
      "/admin/catalog/entities",
    );
    expect(screen.getByRole("link", { name: /Аудит/ })).toHaveAttribute(
      "href",
      "/admin/audit",
    );
  });
});
