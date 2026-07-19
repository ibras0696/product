import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FormProvider, useForm } from "react-hook-form";

import {
  submissionWizardDefaults,
  toCreateSubmissionInput,
  type SubmissionWizardValues,
} from "../../model/submissionWizardSchema";
import { WizardErrorSummary } from "./WizardErrorSummary";
import { SubmissionMaterialStep } from "./steps/SubmissionMaterialStep";
import { SubmissionTargetStep } from "./steps/SubmissionTargetStep";
import { SubmissionTypeStep } from "./steps/SubmissionTypeStep";

const entityId = "11111111-1111-4111-8111-111111111111";
const settlementId = "22222222-2222-4222-8222-222222222222";
const entities = [{ id: entityId, title: "Ахмат-Хаджи Кадыров" }];
const settlements = [{ id: settlementId, title: "Грозный" }];

function StepsHarness() {
  const methods = useForm<SubmissionWizardValues>({
    defaultValues: submissionWizardDefaults,
  });
  return (
    <FormProvider {...methods}>
      <SubmissionTypeStep />
      <SubmissionTargetStep entities={entities} settlements={settlements} />
    </FormProvider>
  );
}

function EmptyOptionsHarness() {
  const methods = useForm<SubmissionWizardValues>({
    defaultValues: submissionWizardDefaults,
  });
  return (
    <FormProvider {...methods}>
      <SubmissionTargetStep entities={[]} settlements={[]} />
    </FormProvider>
  );
}

function ErrorFocusHarness() {
  const methods = useForm<SubmissionWizardValues>({
    defaultValues: submissionWizardDefaults,
  });
  return (
    <FormProvider {...methods}>
      <SubmissionMaterialStep />
      <WizardErrorSummary
        errors={[
          { field: "title", label: "Заголовок", message: "Заполните поле" },
        ]}
        onFieldFocus={methods.setFocus}
      />
    </FormProvider>
  );
}

describe("submission wizard contract", () => {
  it("offers every documented type and shows the relevant relation targets", async () => {
    const user = userEvent.setup();
    render(<StepsHarness />);

    expect(screen.getAllByRole("radio")).toHaveLength(6);
    await user.click(screen.getByRole("radio", { name: /Новая связь/i }));

    expect(
      screen.getByRole("combobox", { name: "Связанный объект" }),
    ).toBeVisible();
    expect(
      screen.getByRole("combobox", { name: "Населённый пункт" }),
    ).toBeVisible();
    expect(
      screen.queryByText("Отправка связи пока недоступна"),
    ).not.toBeInTheDocument();
  });

  it("keeps only target identifiers allowed by the selected type", () => {
    const common = {
      ...submissionWizardDefaults,
      relatedEntityId: entityId,
      settlementId,
      title: "Заголовок",
      description: "Описание",
      sourceDescription: "Архив",
      authorName: "Автор",
      contact: "author@example.com",
      consent: true,
    };

    expect(
      toCreateSubmissionInput({ ...common, type: "new_entity" }),
    ).toMatchObject({
      relatedEntityId: null,
      settlementId,
    });
    expect(
      toCreateSubmissionInput({ ...common, type: "new_relation" }),
    ).toMatchObject({
      relatedEntityId: entityId,
      settlementId,
    });
    for (const type of [
      "update_entity",
      "new_source",
      "new_media",
      "report_error",
    ] as const) {
      expect(toCreateSubmissionInput({ ...common, type })).toMatchObject({
        relatedEntityId: entityId,
        settlementId: null,
      });
    }
  });

  it("keeps an unavailable selector explicit without fabricating catalog ids", () => {
    render(<EmptyOptionsHarness />);

    expect(
      screen.getByText("Справочник объектов пока недоступен"),
    ).toBeVisible();
    expect(
      screen.getByRole("combobox", { name: "Населённый пункт" }),
    ).toHaveValue("");
  });

  it("moves focus from the error summary to the invalid field", async () => {
    const user = userEvent.setup();
    render(<ErrorFocusHarness />);

    const summary = screen.getByRole("alert");
    expect(summary).toBeVisible();
    await user.click(screen.getByRole("button", { name: /Заголовок/i }));

    expect(
      screen.getByRole("textbox", { name: "Название материала" }),
    ).toHaveFocus();
  });
});
