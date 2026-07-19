import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { createMockAdminCatalogPort } from "../api/createMockAdminCatalogPort";
import type { AdminCatalogPermissions } from "../domain/catalog";
import { AdminCatalogPage } from "./AdminCatalogPage";

const permissions: AdminCatalogPermissions = {
  read: true,
  write: true,
  export: true,
  auditRead: true,
};

it("preserves unsaved entity input when expected version conflicts", async () => {
  const port = createMockAdminCatalogPort();
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const user = userEvent.setup();
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        initialEntries={["/admin/catalog/entities?status=published"]}
      >
        <AdminCatalogPage port={port} permissions={permissions} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  await user.click(
    await screen.findByRole("button", { name: "Изменить Грозный" }),
  );
  const title = screen.getByLabelText("Название (русский)");
  await user.clear(title);
  await user.type(title, "Моя несохранённая версия");
  port.mockOnlyBumpVersion("60000000-0000-4000-8000-000000000001");
  await user.click(screen.getByRole("button", { name: "Сохранить" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Ваши данные сохранены в форме",
  );
  expect(title).toHaveValue("Моя несохранённая версия");
});
