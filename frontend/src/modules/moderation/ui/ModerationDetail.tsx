import type {
  ModerationDecisionInput,
  ModerationSubmission,
  PublishCommand,
} from "../domain/types";
import { DecisionControls } from "./DecisionControls";
import { moderationTypeLabels } from "./labels";
import { SubmissionEvidence } from "./SubmissionEvidence";

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

export function ModerationDetail(props: Props) {
  const { submission } = props;
  return (
    <article className="mod-detail" aria-labelledby="mod-detail-title">
      <header>
        <div>
          <p className="mod-eyebrow">{moderationTypeLabels[submission.type]}</p>
          <h2 id="mod-detail-title">{submission.title}</h2>
        </div>
        <span className="mod-status">
          {submission.status} · v{submission.version}
        </span>
      </header>
      <SubmissionEvidence submission={submission} />
      <DecisionControls {...props} />
    </article>
  );
}
