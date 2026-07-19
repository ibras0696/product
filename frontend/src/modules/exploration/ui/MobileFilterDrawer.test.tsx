import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import { mockCatalogOptions } from "../api/mockCatalogData";
import type { CatalogEntityType, ResearchStatus } from "../api/viewModels";
import type { ExplorerDateRange } from "../model/dateRange";
import { ExplorerSidebar } from "./ExplorerSidebar";

function FilterHarness() {
  const [activeTypes, setActiveTypes] = useState<Set<CatalogEntityType>>(
    () => new Set(["settlement"]),
  );
  const [districtId, setDistrictId] = useState<string | null>(null);
  const [activeResearchStatuses, setActiveResearchStatuses] = useState<
    Set<ResearchStatus>
  >(() => new Set());
  const [dateRange, setDateRange] = useState<ExplorerDateRange>({
    from: null,
    to: null,
  });

  return (
    <ExplorerSidebar
      activeTypes={activeTypes}
      activeResearchStatuses={activeResearchStatuses}
      activeView="map"
      districtId={districtId}
      periodId={null}
      dateRange={dateRange}
      options={mockCatalogOptions}
      onTypeToggle={(type) => {
        setActiveTypes((current) => {
          const next = new Set(current);
          if (next.has(type)) next.delete(type);
          else next.add(type);
          return next;
        });
      }}
      onResearchStatusToggle={(status) => {
        setActiveResearchStatuses((current) => {
          if (current.size === 0) return new Set([status]);
          const next = new Set(current);
          if (next.has(status)) next.delete(status);
          else next.add(status);
          return next.size === mockCatalogOptions.researchStatuses.length
            ? new Set()
            : next;
        });
      }}
      onViewChange={() => undefined}
      onDistrictChange={setDistrictId}
      onDateRangeChange={setDateRange}
      onReset={() => {
        setActiveTypes(new Set());
        setDistrictId(null);
        setActiveResearchStatuses(new Set());
        setDateRange({ from: null, to: null });
      }}
    />
  );
}

it("edits and resets active filters inside the mobile sheet", async () => {
  const user = userEvent.setup();
  render(<FilterHarness />);

  const trigger = screen.getByRole("button", { name: "Фильтры · 1" });
  await user.click(trigger);
  const dialog = screen.getByRole("dialog", { name: "Фильтры" });
  const controls = within(dialog);

  expect(document.body).toHaveStyle({ overflow: "hidden" });
  expect(
    controls.getByRole("button", { name: "Населённые пункты" }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(controls.getByRole("button", { name: "Личности" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );

  await user.click(controls.getByRole("button", { name: "Личности" }));
  await user.selectOptions(
    controls.getByRole("combobox", { name: "Район" }),
    mockCatalogOptions.districts[1].id,
  );
  fireEvent.change(controls.getByRole("slider", { name: "Начало периода" }), {
    target: { value: "1800" },
  });
  fireEvent.change(controls.getByRole("slider", { name: "Конец периода" }), {
    target: { value: "1950" },
  });
  await user.click(controls.getByRole("button", { name: "Требует проверки" }));
  expect(controls.getByRole("combobox", { name: "Район" })).toHaveValue(
    mockCatalogOptions.districts[1].id,
  );
  expect(controls.getByText("1800-1950")).toBeVisible();
  expect(
    controls.getByRole("button", { name: "Требует проверки" }),
  ).toHaveAttribute("aria-pressed", "true");

  await user.click(controls.getByRole("button", { name: "Сбросить" }));
  expect(controls.getByRole("combobox", { name: "Район" })).toHaveValue("");
  expect(controls.getByText("Весь период")).toBeVisible();
  expect(
    controls.getByRole("slider", { name: "Начало периода" }),
  ).toHaveAttribute("aria-valuetext", "Без нижней границы");
  expect(
    controls.getByRole("button", { name: "Требует проверки" }),
  ).toHaveAttribute("aria-pressed", "false");
  expect(controls.getByRole("button", { name: "Личности" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );

  fireEvent.pointerDown(dialog.parentElement as HTMLElement);
  expect(
    screen.queryByRole("dialog", { name: "Фильтры" }),
  ).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
  expect(document.body).not.toHaveStyle({ overflow: "hidden" });
});

it("traps keyboard focus and restores the trigger after Escape", async () => {
  const user = userEvent.setup();
  render(<FilterHarness />);

  const trigger = screen.getByRole("button", { name: "Фильтры · 1" });
  await user.click(trigger);
  const dialog = screen.getByRole("dialog", { name: "Фильтры" });
  const close = within(dialog).getByRole("button", { name: "Закрыть" });
  const apply = within(dialog).getByRole("button", {
    name: "Показать результаты",
  });

  expect(close).toHaveFocus();
  await user.tab({ shift: true });
  expect(apply).toHaveFocus();
  await user.tab();
  expect(close).toHaveFocus();

  await user.keyboard("{Escape}");
  expect(
    screen.queryByRole("dialog", { name: "Фильтры" }),
  ).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
});
