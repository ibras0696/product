import type { ModerationSubmission, PublishCommand } from "../domain/types";
import { PublishNewEntityForm } from "./PublishNewEntityForm";
import { PublishUpdateEntityForm } from "./PublishUpdateEntityForm";
import {
  PublishRelationForm,
  PublishSourceForm,
} from "./PublishRelationSourceForms";
import { PublishMediaForm, ResolveReportForm } from "./PublishMediaReportForms";

interface Props {
  submission: ModerationSubmission;
  pending: boolean;
  errorMessage: string | null;
  onPublish: (input: PublishCommand) => Promise<unknown>;
}

export function PublishSubmissionForm(props: Props) {
  if (props.submission.type === "new_entity") {
    return <PublishNewEntityForm {...props} />;
  }
  if (props.submission.type === "update_entity") {
    return <PublishUpdateEntityForm {...props} />;
  }
  if (props.submission.type === "new_relation") {
    return <PublishRelationForm {...props} />;
  }
  if (props.submission.type === "new_source") {
    return <PublishSourceForm {...props} />;
  }
  if (props.submission.type === "new_media") {
    return <PublishMediaForm {...props} />;
  }
  return <ResolveReportForm {...props} />;
}
