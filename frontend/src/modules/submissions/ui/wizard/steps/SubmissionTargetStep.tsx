import { useFormContext, useWatch } from "react-hook-form";

import {
  submissionTargetFields,
  submissionTypePresentation,
  type SubmissionWizardValues,
} from "../../../model/submissionWizardSchema";
import { StepFieldError } from "./StepFieldError";

export interface SubmissionTargetOption {
  id: string;
  title: string;
}

type TargetField = "relatedEntityId" | "settlementId";

function TargetSelect(props: {
  name: TargetField;
  label: string;
  emptyLabel: string;
  options: SubmissionTargetOption[];
}) {
  const {
    register,
    formState: { errors },
  } = useFormContext<SubmissionWizardValues>();
  const error = errors[props.name];
  const errorId = `${props.name}-error`;
  return (
    <label className="submission-field">
      <span>{props.label}</span>
      <select
        {...register(props.name, {
          setValueAs: (value: string) => value || null,
        })}
        aria-describedby={error ? errorId : undefined}
      >
        <option value="">{props.emptyLabel}</option>
        {props.options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.title}
          </option>
        ))}
      </select>
      <StepFieldError id={errorId} error={error} />
    </label>
  );
}

export function SubmissionTargetStep(props: {
  entities: SubmissionTargetOption[];
  settlements: SubmissionTargetOption[];
}) {
  const { control } = useFormContext<SubmissionWizardValues>();
  const type = useWatch({ control, name: "type" });
  const targets = submissionTargetFields(type);
  const copy = submissionTypePresentation[type];
  const showsSettlement = targets.settlement;
  const showsEntity = targets.entity;
  const hasMissingOptions =
    (showsSettlement && props.settlements.length === 0) ||
    (showsEntity && props.entities.length === 0);
  return (
    <section
      className="submission-step"
      aria-labelledby="submission-target-title"
    >
      <h3 id="submission-target-title">Привязка к каталогу</h3>
      <p className="submission-step-lead">
        Для заявки «{copy.title}» привязка помогает редакции быстрее найти
        нужную карточку. Поле можно оставить пустым.
      </p>
      {hasMissingOptions ? (
        <div className="submission-contract-block" role="status">
          <strong>Справочник объектов пока недоступен</strong>
          <p>
            Можно продолжить без привязки. Не выбирайте идентификаторы из
            сторонних источников.
          </p>
        </div>
      ) : null}
      {showsEntity ? (
        <TargetSelect
          name="relatedEntityId"
          label="Связанный объект"
          emptyLabel="Объект не выбран"
          options={props.entities}
        />
      ) : null}
      {showsSettlement ? (
        <TargetSelect
          name="settlementId"
          label="Населённый пункт"
          emptyLabel="Населённый пункт не выбран"
          options={props.settlements}
        />
      ) : null}
    </section>
  );
}
