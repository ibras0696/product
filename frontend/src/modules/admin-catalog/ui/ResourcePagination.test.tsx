import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { ResourcePagination } from "./ResourcePagination";

it("navigates a bounded server page and reports the visible record range", async () => {
  const onOffsetChange = vi.fn();
  render(
    <ResourcePagination
      label="Страницы источников"
      meta={{ limit: 20, offset: 20, total: 55 }}
      onOffsetChange={onOffsetChange}
    />,
  );

  expect(screen.getByText("21–40 из 55")).toBeVisible();
  expect(screen.getByText("2 / 3")).toBeVisible();
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Назад" }));
  await user.click(screen.getByRole("button", { name: "Дальше" }));
  expect(onOffsetChange).toHaveBeenNthCalledWith(1, 0);
  expect(onOffsetChange).toHaveBeenNthCalledWith(2, 40);
});
