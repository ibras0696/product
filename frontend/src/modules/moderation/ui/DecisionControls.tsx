import type {
  ModerationDecisionInput,
  ModerationSubmission,
  PublishCommand,
} from "../domain/types";
import { DecisionForm } from "./DecisionForm";
import { PublishSubmissionForm } from "./PublishSubmissionForm";

interface Props {
  submission: ModerationSubmission;
  pending: {
    claim: boolean;
    revision: boolean;
    reject: boolean;
    publish: boolean;
  };
  errors: {
    claim: string | null;
    revision: string | null;
    reject: string | null;
    publish: string | null;
  };
  onClaim: () => Promise<unknown>;
  onRevision: (input: ModerationDecisionInput) => Promise<unknown>;
  onReject: (input: ModerationDecisionInput) => Promise<unknown>;
  onPublish: (input: PublishCommand) => Promise<unknown>;
}

export function DecisionControls({
  submission,
  pending,
  errors,
  onClaim,
  onRevision,
  onReject,
  onPublish,
}: Props) {
  if (submission.status === "pending") {
    return (
      <section className="mod-actions">
        <button
          type="button"
          disabled={pending.claim}
          onClick={() => {
            void onClaim();
          }}
        >
          {pending.claim ? "Берём…" : "Взять в работу"}
        </button>
        {errors.claim ? <p role="alert">{errors.claim}</p> : null}
      </section>
    );
  }
  if (submission.status !== "in_review") return null;
  return (
    <>
      <div className="mod-decision-grid">
        <DecisionForm
          mode="revision"
          expectedVersion={submission.version}
          pending={pending.revision}
          errorMessage={errors.revision}
          onDecision={onRevision}
        />
        <DecisionForm
          mode="reject"
          expectedVersion={submission.version}
          pending={pending.reject}
          errorMessage={errors.reject}
          onDecision={onReject}
        />
      </div>
      <PublishSubmissionForm
        submission={submission}
        pending={pending.publish}
        errorMessage={errors.publish}
        onPublish={onPublish}
      />
    </>
  );
}
