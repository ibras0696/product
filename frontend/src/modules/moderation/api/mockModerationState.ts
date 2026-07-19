import type { ModerationSubmission, PublishResult } from "../domain/types";
import { moderationError } from "../domain/errors";
import { mockModerationSubmissions } from "./mockSeeds";

export type MockModerationCapability = "none" | "read" | "decide" | "publish";

export interface PublishReplay {
  signature: string;
  result: PublishResult;
}

export interface MockModerationState {
  capability: MockModerationCapability;
  submissions: Map<string, ModerationSubmission>;
  publishReplays: Map<string, PublishReplay>;
}

const rank: Record<MockModerationCapability, number> = {
  none: 0,
  read: 1,
  decide: 2,
  publish: 3,
};

export function copySubmission(
  value: ModerationSubmission,
): ModerationSubmission {
  return { ...value, media: value.media.map((item) => ({ ...item })) };
}

export function createMockModerationState(
  capability: MockModerationCapability,
): MockModerationState {
  return {
    capability,
    submissions: new Map(
      mockModerationSubmissions.map((item) => [item.id, copySubmission(item)]),
    ),
    publishReplays: new Map(),
  };
}

export function requireCapability(
  state: MockModerationState,
  required: MockModerationCapability,
): void {
  if (rank[state.capability] < rank[required]) {
    throw moderationError("forbidden", "Недостаточно прав для операции");
  }
}

export function getStored(
  state: MockModerationState,
  id: string,
): ModerationSubmission {
  const submission = state.submissions.get(id);
  if (!submission) throw moderationError("not_found", "Заявка не найдена");
  return submission;
}
