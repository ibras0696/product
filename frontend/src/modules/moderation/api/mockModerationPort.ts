import type { ModerationPort } from "./moderationPort";
import {
  claimSubmission,
  decideSubmission,
  getQueue,
  getSubmission,
  publishSubmission,
} from "./mockModerationOperations";
import {
  createMockModerationState,
  type MockModerationCapability,
} from "./mockModerationState";

export { MODERATION_MOCK_IDS } from "./mockSeeds";
export type { MockModerationCapability } from "./mockModerationState";

export function createMockModerationPort(
  capability: MockModerationCapability = "publish",
): ModerationPort {
  const state = createMockModerationState(capability);
  return {
    getQueue: (filters, signal) => getQueue(state, filters, signal),
    getSubmission: (id, signal) => getSubmission(state, id, signal),
    claimSubmission: (id, input, signal) =>
      claimSubmission(state, id, input, signal),
    requestRevision: (id, input, signal) =>
      decideSubmission(state, id, input, "needs_revision", signal),
    rejectSubmission: (id, input, signal) =>
      decideSubmission(state, id, input, "rejected", signal),
    publishSubmission: (id, input, signal) =>
      publishSubmission(state, id, input, signal),
  };
}
