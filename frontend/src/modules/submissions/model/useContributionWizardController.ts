import { zodResolver } from "@hookform/resolvers/zod";
import {
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type RefObject,
  type SetStateAction,
} from "react";
import { useForm, useWatch, type UseFormReturn } from "react-hook-form";

import { useOnlineStatus } from "@/shared/browser/useOnlineStatus";

import type { SubmissionsPort } from "../api/submissionsPort";
import { SubmissionApplicationError } from "../domain/errors";
import type { SubmissionTargetOption } from "../ui/wizard/steps/SubmissionTargetStep";
import {
  submissionRequiresMedia,
  submissionWizardDefaults,
  submissionWizardSchema,
  toCreateSubmissionInput,
  toPatchSubmissionInput,
  type SubmissionWizardValues,
} from "./submissionWizardSchema";
import {
  useSubmissionWorkflow,
  type SubmissionWorkflow,
} from "./useSubmissionWorkflow";
import { useUploadQueue, type UploadQueueController } from "./uploadQueue";
import {
  firstInvalidStep,
  visibleWizardErrors,
  wizardFields,
} from "./wizardValidation";
import { wizardSteps } from "./wizardSteps";

export interface ContributionWizardOptions {
  port: SubmissionsPort;
  entities: SubmissionTargetOption[];
  settlements: SubmissionTargetOption[];
}

interface WizardContext extends ContributionWizardOptions {
  methods: UseFormReturn<SubmissionWizardValues>;
  workflow: SubmissionWorkflow;
  queue: UploadQueueController;
  online: boolean;
  step: number;
  setStep: Dispatch<SetStateAction<number>>;
  errorSummaryRef: RefObject<HTMLDivElement | null>;
}

function focusSoon(element: HTMLElement | null) {
  requestAnimationFrame(() => element?.focus());
}

async function persistDraft(context: WizardContext) {
  if (context.workflow.draft) {
    return context.workflow.patchMutation.mutateAsync(
      toPatchSubmissionInput(context.methods.getValues()),
    );
  }
  return context.workflow.createMutation.mutateAsync(
    toCreateSubmissionInput(context.methods.getValues()),
  );
}

async function nextWizardStep(context: WizardContext) {
  const valid = await context.methods.trigger(wizardFields[context.step]);
  if (!valid) {
    focusSoon(context.errorSummaryRef.current);
    return;
  }
  if (context.step === 3) {
    if (!context.online) return;
    try {
      await persistDraft(context);
    } catch {
      return;
    }
  }
  context.setStep((current) => Math.min(current + 1, wizardSteps.length - 1));
}

async function submitWizard(context: WizardContext, blocked: boolean) {
  const valid = await context.methods.trigger();
  if (!valid) {
    const invalidStep = firstInvalidStep(context.methods.formState.errors);
    if (invalidStep >= 0) context.setStep(invalidStep);
    focusSoon(context.errorSummaryRef.current);
    return;
  }
  if (blocked) return;
  try {
    const draft = await persistDraft(context);
    await context.workflow.submitMutation.mutateAsync(draft);
  } catch {
    focusSoon(context.errorSummaryRef.current);
  }
}

export function publicSubmissionError(error: Error | null) {
  if (!error) return null;
  if (error instanceof SubmissionApplicationError) {
    if (error.code === "source_required") return "Укажите источник материала.";
    if (error.code === "media_rejected")
      return "Проверьте описание загруженных файлов.";
    if (error.code === "draft_not_editable")
      return "Заявка уже недоступна для изменений.";
    if (error.code === "conflict")
      return "Черновик изменился. Обновите страницу перед повторной отправкой.";
  }
  return "Не удалось сохранить заявку. Данные формы не потеряны — повторите попытку.";
}

function submissionBlockReason(
  online: boolean,
  type: SubmissionWizardValues["type"],
  queue: UploadQueueController,
) {
  const busy = queue.items.some((item) =>
    ["uploading", "ambiguous", "saving", "deleting"].includes(item.status),
  );
  const uploaded = queue.items.filter(
    (item) => item.status === "uploaded",
  ).length;
  if (!online) return "Восстановите соединение, чтобы отправить заявку.";
  if (busy) return "Дождитесь завершения операций с файлами.";
  if (submissionRequiresMedia(type) && uploaded === 0) {
    return "Для фото или изображения загрузите хотя бы один файл.";
  }
  return null;
}

interface ContributionWizardRefs {
  headingRef: RefObject<HTMLHeadingElement | null>;
  errorSummaryRef: RefObject<HTMLDivElement | null>;
}

export function useContributionWizardController(
  options: ContributionWizardOptions,
  refs: ContributionWizardRefs,
) {
  const methods = useForm<SubmissionWizardValues>({
    resolver: zodResolver(submissionWizardSchema),
    defaultValues: submissionWizardDefaults,
    mode: "onTouched",
    shouldUnregister: false,
  });
  const workflow = useSubmissionWorkflow(options.port);
  const queue = useUploadQueue(options.port, workflow.draft?.id ?? "");
  const online = useOnlineStatus();
  const [step, setStep] = useState(0);
  const previousStep = useRef(step);
  useEffect(() => {
    if (previousStep.current !== step) {
      refs.headingRef.current?.focus();
      previousStep.current = step;
    }
  }, [refs.headingRef, step]);
  const type = useWatch({ control: methods.control, name: "type" });
  const pending =
    workflow.createMutation.isPending ||
    workflow.patchMutation.isPending ||
    workflow.submitMutation.isPending;
  const blockedReason = submissionBlockReason(online, type, queue);
  const blocked = blockedReason !== null;
  const context: WizardContext = {
    ...options,
    methods,
    workflow,
    queue,
    online,
    step,
    setStep,
    errorSummaryRef: refs.errorSummaryRef,
  };
  return {
    ...options,
    methods,
    workflow,
    queue,
    online,
    step,
    type,
    pending,
    blocked,
    blockedReason,
    errors: visibleWizardErrors(methods.formState.errors, step),
    mutationError:
      workflow.createMutation.error ??
      workflow.patchMutation.error ??
      workflow.submitMutation.error,
    next: () => nextWizardStep(context),
    submit: () => submitWizard(context, blocked),
    back() {
      setStep((current) => Math.max(0, current - 1));
    },
  };
}

export type ContributionWizardController = ReturnType<
  typeof useContributionWizardController
>;
