import type { UploadQueueController } from "../../model/uploadQueue";
import type { SubmissionType } from "../../domain/submission";
import { submissionRequiresMedia } from "../../model/submissionWizardSchema";
import { SubmissionMediaStep } from "../media/SubmissionMediaStep";
import { SubmissionContactStep } from "./steps/SubmissionContactStep";
import { SubmissionMaterialStep } from "./steps/SubmissionMaterialStep";
import { SubmissionReviewStep } from "./steps/SubmissionReviewStep";
import {
  SubmissionTargetStep,
  type SubmissionTargetOption,
} from "./steps/SubmissionTargetStep";
import { SubmissionTypeStep } from "./steps/SubmissionTypeStep";

interface WizardStepContentProps {
  step: number;
  entities: SubmissionTargetOption[];
  settlements: SubmissionTargetOption[];
  queue: UploadQueueController;
  offline: boolean;
  draftCreated: boolean;
  blockedReason: string | null;
  type: SubmissionType;
}

export function WizardStepContent(props: WizardStepContentProps) {
  if (props.step === 0) {
    return <SubmissionTypeStep locked={props.draftCreated} />;
  }
  if (props.step === 1) {
    return (
      <SubmissionTargetStep
        entities={props.entities}
        settlements={props.settlements}
      />
    );
  }
  if (props.step === 2) return <SubmissionMaterialStep />;
  if (props.step === 3) return <SubmissionContactStep />;
  if (props.step === 4) {
    return (
      <SubmissionMediaStep
        queue={props.queue}
        disabled={props.offline}
        required={submissionRequiresMedia(props.type)}
      />
    );
  }
  return (
    <SubmissionReviewStep
      entities={props.entities}
      settlements={props.settlements}
      uploadedMediaCount={
        props.queue.items.filter((item) => item.status === "uploaded").length
      }
      blockedReason={props.blockedReason}
    />
  );
}
