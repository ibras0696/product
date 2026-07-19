import { useFormContext, useWatch } from "react-hook-form";

import {
  submissionRequiresMedia,
  submissionTargetFields,
  submissionTypePresentation,
  type SubmissionWizardValues,
} from "../../../model/submissionWizardSchema";
import type { SubmissionTargetOption } from "./SubmissionTargetStep";

function findTitle(options: SubmissionTargetOption[], id: string | null) {
  return options.find((option) => option.id === id)?.title ?? "Не выбрано";
}

function displayText(value: string | undefined) {
  return value === "" || value === undefined ? "Не заполнено" : value;
}

function ReviewList(props: {
  values: Partial<SubmissionWizardValues>;
  entities: SubmissionTargetOption[];
  settlements: SubmissionTargetOption[];
}) {
  const type = props.values.type ?? "new_entity";
  const copy = submissionTypePresentation[type];
  const targets = submissionTargetFields(type);
  const showsSettlement = targets.settlement;
  const showsEntity = targets.entity;
  return (
    <dl className="submission-review-list">
      <div>
        <dt>Тип заявки</dt>
        <dd>{copy.title}</dd>
      </div>
      {showsEntity ? (
        <div>
          <dt>Связанный объект</dt>
          <dd>
            {findTitle(props.entities, props.values.relatedEntityId ?? null)}
          </dd>
        </div>
      ) : null}
      {showsSettlement ? (
        <div>
          <dt>Населённый пункт</dt>
          <dd>
            {findTitle(props.settlements, props.values.settlementId ?? null)}
          </dd>
        </div>
      ) : null}
      <div>
        <dt>Заголовок</dt>
        <dd>{displayText(props.values.title)}</dd>
      </div>
      <div className="submission-review-wide">
        <dt>Описание</dt>
        <dd>{displayText(props.values.description)}</dd>
      </div>
      <div className="submission-review-wide">
        <dt>Происхождение сведений</dt>
        <dd>{displayText(props.values.sourceDescription)}</dd>
      </div>
      <div>
        <dt>Автор</dt>
        <dd>{displayText(props.values.authorName)}</dd>
      </div>
      <div>
        <dt>Контакт</dt>
        <dd>{displayText(props.values.contact)}</dd>
      </div>
    </dl>
  );
}

export function SubmissionReviewStep(props: {
  entities: SubmissionTargetOption[];
  settlements: SubmissionTargetOption[];
  uploadedMediaCount: number;
  blockedReason: string | null;
}) {
  const { control } = useFormContext<SubmissionWizardValues>();
  const values = useWatch({ control });
  const type = values.type ?? "new_entity";

  return (
    <section
      className="submission-step"
      aria-labelledby="submission-review-title"
    >
      <h3 id="submission-review-title">Проверка заявки</h3>
      <p className="submission-step-lead">
        Проверьте данные перед отправкой в редакцию.
      </p>

      <ReviewList
        values={values}
        entities={props.entities}
        settlements={props.settlements}
      />

      <div className="submission-review-state" role="status">
        <strong>
          {props.blockedReason ? "Заявка ещё не готова" : "Можно отправлять"}
        </strong>
        <p>
          {props.blockedReason ??
            (submissionRequiresMedia(type)
              ? `Загружено файлов: ${String(props.uploadedMediaCount)}.`
              : props.uploadedMediaCount > 0
                ? `Загружено файлов: ${String(props.uploadedMediaCount)}.`
                : "Файлы не добавлены — для этого типа заявки они необязательны.")}
        </p>
      </div>
    </section>
  );
}
