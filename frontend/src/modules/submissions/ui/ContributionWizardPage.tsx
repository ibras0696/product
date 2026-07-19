import { useRef } from "react";

import type { SubmissionsPort } from "../api/submissionsPort";
import { useContributionWizardController } from "../model/useContributionWizardController";
import "./submission-fields.css";
import "./submission-media.css";
import "./submission-shell.css";
import "./submission-status.css";
import { ContributionPageIntro } from "./ContributionPageIntro";
import { ContributionWizardForm } from "./ContributionWizardForm";
import { SubmissionReceipt } from "./status/SubmissionReceipt";
import { SubmissionStatusLookup } from "./status/SubmissionStatusLookup";
import type { SubmissionTargetOption } from "./wizard/steps/SubmissionTargetStep";

interface ContributionWizardPageProps {
  port: SubmissionsPort;
  entities: SubmissionTargetOption[];
  settlements: SubmissionTargetOption[];
}

export function ContributionWizardPage(props: ContributionWizardPageProps) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  const errorSummaryRef = useRef<HTMLDivElement>(null);
  const controller = useContributionWizardController(props, {
    headingRef,
    errorSummaryRef,
  });
  if (controller.workflow.receipt) {
    return (
      <main className="submission-page">
        <SubmissionReceipt receipt={controller.workflow.receipt} />
      </main>
    );
  }
  return (
    <main className="submission-page">
      <ContributionPageIntro
        online={controller.online}
        needsRevision={controller.workflow.draft?.status === "needs_revision"}
      />
      <ContributionWizardForm
        controller={controller}
        headingRef={headingRef}
        errorSummaryRef={errorSummaryRef}
      />
      <SubmissionStatusLookup
        pending={controller.workflow.statusMutation.isPending}
        error={controller.workflow.statusMutation.error}
        result={controller.workflow.statusMutation.data}
        onLookup={(code) => {
          controller.workflow.statusMutation.mutate(code);
        }}
      />
    </main>
  );
}
