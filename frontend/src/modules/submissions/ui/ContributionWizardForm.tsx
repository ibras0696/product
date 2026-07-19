import type { RefObject } from "react";
import { FormProvider } from "react-hook-form";

import type { ContributionWizardController } from "../model/useContributionWizardController";
import { publicSubmissionError } from "../model/useContributionWizardController";
import { wizardSteps } from "../model/wizardSteps";
import { WizardErrorSummary } from "./wizard/WizardErrorSummary";
import { WizardFrame } from "./wizard/WizardFrame";
import { WizardNavigation } from "./wizard/WizardNavigation";
import { WizardStepContent } from "./wizard/WizardStepContent";

export function ContributionWizardForm({
  controller,
  headingRef,
  errorSummaryRef,
}: {
  controller: ContributionWizardController;
  headingRef: RefObject<HTMLHeadingElement | null>;
  errorSummaryRef: RefObject<HTMLDivElement | null>;
}) {
  const mutationError = publicSubmissionError(controller.mutationError);
  return (
    <FormProvider {...controller.methods}>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (controller.step === wizardSteps.length - 1) {
            void controller.submit();
          } else {
            void controller.next();
          }
        }}
        noValidate
      >
        <WizardFrame
          ref={headingRef}
          step={controller.step}
          navigation={
            <WizardNavigation
              step={controller.step}
              lastStep={wizardSteps.length - 1}
              pending={controller.pending}
              blocked={controller.blocked}
              onBack={() => {
                controller.back();
              }}
            />
          }
        >
          <WizardErrorSummary
            ref={errorSummaryRef}
            errors={controller.errors}
            onFieldFocus={(field) => {
              controller.methods.setFocus(field);
            }}
          />
          {mutationError ? (
            <p className="submission-form-error" role="alert">
              {mutationError}
            </p>
          ) : null}
          <WizardStepContent
            step={controller.step}
            entities={controller.entities}
            settlements={controller.settlements}
            queue={controller.queue}
            offline={!controller.online}
            draftCreated={controller.workflow.draft !== null}
            blockedReason={controller.blockedReason}
            type={controller.type}
          />
        </WizardFrame>
      </form>
    </FormProvider>
  );
}
