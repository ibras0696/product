import type {
  ModerationDecisionInput,
  ModerationClaimInput,
  ModerationFilters,
  ModerationPage,
  ModerationQueueItem,
  ModerationSubmission,
  PublishCommand,
  PublishResult,
} from "../domain/types";

export interface ModerationPort {
  getQueue(
    filters: ModerationFilters,
    signal: AbortSignal,
  ): Promise<ModerationPage<ModerationQueueItem>>;
  getSubmission(
    submissionId: string,
    signal: AbortSignal,
  ): Promise<ModerationSubmission>;
  claimSubmission(
    submissionId: string,
    input: ModerationClaimInput,
    signal: AbortSignal,
  ): Promise<ModerationSubmission>;
  requestRevision(
    submissionId: string,
    input: ModerationDecisionInput,
    signal: AbortSignal,
  ): Promise<ModerationSubmission>;
  rejectSubmission(
    submissionId: string,
    input: ModerationDecisionInput,
    signal: AbortSignal,
  ): Promise<ModerationSubmission>;
  publishSubmission(
    submissionId: string,
    input: PublishCommand,
    signal: AbortSignal,
  ): Promise<PublishResult>;
}
