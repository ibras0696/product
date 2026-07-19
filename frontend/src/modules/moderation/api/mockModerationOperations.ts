import { moderationError } from "../domain/errors";
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
import {
  copySubmission,
  getStored,
  requireCapability,
  type MockModerationState,
} from "./mockModerationState";

function optionalMatch(
  actual: string | null,
  expected: string | null,
): boolean {
  return expected === null || actual === expected;
}

function matchesFilters(
  item: ModerationSubmission,
  filters: ModerationFilters,
): boolean {
  const matchesStatus = optionalMatch(item.status, filters.status);
  const matchesType = optionalMatch(item.type, filters.type);
  const matchesSettlement = optionalMatch(
    item.settlementId,
    filters.settlementId,
  );
  const afterStart =
    filters.createdFrom === null || item.createdAt >= filters.createdFrom;
  const beforeEnd =
    filters.createdTo === null || item.createdAt <= filters.createdTo;
  return (
    matchesStatus && matchesType && matchesSettlement && afterStart && beforeEnd
  );
}

function toQueueItem(value: ModerationSubmission): ModerationQueueItem {
  return {
    id: value.id,
    type: value.type,
    title: value.title,
    status: value.status,
    settlementId: value.settlementId,
    submittedAt: value.submittedAt,
    createdAt: value.createdAt,
    claimedBy: value.claimedBy,
    version: value.version,
  };
}

export function getQueue(
  state: MockModerationState,
  filters: ModerationFilters,
  signal: AbortSignal,
): Promise<ModerationPage<ModerationQueueItem>> {
  return Promise.resolve().then(() => {
    signal.throwIfAborted();
    requireCapability(state, "read");
    const limit = Math.min(Math.max(filters.limit, 1), 50);
    const offset = Math.min(Math.max(filters.offset, 0), 1000);
    const filtered = [...state.submissions.values()]
      .filter((item) => matchesFilters(item, filters))
      .sort((left, right) => right.createdAt.localeCompare(left.createdAt));
    return {
      items: filtered.slice(offset, offset + limit).map(toQueueItem),
      meta: { limit, offset, total: filtered.length },
    };
  });
}

export function getSubmission(
  state: MockModerationState,
  id: string,
  signal: AbortSignal,
): Promise<ModerationSubmission> {
  return Promise.resolve().then(() => {
    signal.throwIfAborted();
    requireCapability(state, "read");
    return copySubmission(getStored(state, id));
  });
}

export function claimSubmission(
  state: MockModerationState,
  id: string,
  input: ModerationClaimInput,
  signal: AbortSignal,
): Promise<ModerationSubmission> {
  return Promise.resolve().then(() => {
    signal.throwIfAborted();
    requireCapability(state, "decide");
    const current = getStored(state, id);
    assertVersion(current, input.expectedVersion);
    if (current.status !== "pending") {
      throw moderationError("invalid_transition", "Заявка уже взята в работу");
    }
    const claimed = {
      ...current,
      status: "in_review",
      version: current.version + 1,
      claimedBy: "mock-current-moderator",
    } satisfies ModerationSubmission;
    state.submissions.set(id, claimed);
    return copySubmission(claimed);
  });
}

function assertVersion(
  submission: ModerationSubmission,
  expectedVersion: number,
): void {
  if (submission.version !== expectedVersion) {
    throw moderationError("conflict", "Заявка была изменена в другой вкладке");
  }
}

export function decideSubmission(
  state: MockModerationState,
  id: string,
  input: ModerationDecisionInput,
  status: "needs_revision" | "rejected",
  signal: AbortSignal,
): Promise<ModerationSubmission> {
  return Promise.resolve().then(() => {
    signal.throwIfAborted();
    requireCapability(state, "decide");
    const current = getStored(state, id);
    assertVersion(current, input.expectedVersion);
    if (current.status !== "in_review") {
      throw moderationError("invalid_transition", "Заявка не взята в работу");
    }
    if (input.comment.trim().length === 0) {
      throw moderationError("validation_error", "Комментарий обязателен");
    }
    const updated = {
      ...current,
      status,
      version: current.version + 1,
      claimedBy: null,
    } satisfies ModerationSubmission;
    state.submissions.set(id, updated);
    return copySubmission(updated);
  });
}

function replayPublish(
  state: MockModerationState,
  key: string,
  signature: string,
): PublishResult | null {
  const replay = state.publishReplays.get(key);
  if (!replay) return null;
  if (replay.signature !== signature) {
    throw moderationError(
      "idempotency_conflict",
      "Ключ уже использован с другим решением",
    );
  }
  return replay.result;
}

function assertPublishable(
  submission: ModerationSubmission,
  input: PublishCommand,
): void {
  const expectedActions: Record<
    ModerationSubmission["type"],
    PublishCommand["action"]
  > = {
    new_entity: "create_entity",
    update_entity: "update_entity",
    new_relation: "create_relation",
    new_source: "add_source",
    new_media: "publish_media",
    report_error: "resolve_report",
  };
  if (
    expectedActions[submission.type] !== input.action ||
    submission.status !== "in_review"
  ) {
    throw moderationError(
      "invalid_transition",
      "Заявка не готова к публикации",
    );
  }
  if ("sources" in input.payload && input.payload.sources.length === 0) {
    throw moderationError("source_required", "Нужен проверенный источник");
  }
  if (input.comment.trim().length === 0) {
    throw moderationError("validation_error", "Комментарий обязателен");
  }
}

function publishResult(id: string, input: PublishCommand): PublishResult {
  return {
    submissionId: id,
    status: "published",
    action: input.action,
    publishedEntityIds:
      input.action === "create_entity" ? [crypto.randomUUID()] : [],
    publishedRelationIds:
      input.action === "create_relation" ? [crypto.randomUUID()] : [],
    publishedSourceIds:
      input.action === "add_source" ? [crypto.randomUUID()] : [],
    publishedMediaIds:
      "approvedMediaIds" in input.payload
        ? [...input.payload.approvedMediaIds]
        : [],
    auditId: crypto.randomUUID(),
  };
}

export function publishSubmission(
  state: MockModerationState,
  id: string,
  input: PublishCommand,
  signal: AbortSignal,
): Promise<PublishResult> {
  return Promise.resolve().then(() => {
    signal.throwIfAborted();
    requireCapability(state, "publish");
    const signature = JSON.stringify({ id, ...input });
    const replay = replayPublish(state, input.idempotencyKey, signature);
    if (replay) return replay;
    const current = getStored(state, id);
    assertVersion(current, input.expectedVersion);
    assertPublishable(current, input);
    const result = publishResult(id, input);
    state.submissions.set(id, {
      ...current,
      status: "published",
      version: current.version + 1,
      claimedBy: null,
    });
    state.publishReplays.set(input.idempotencyKey, { signature, result });
    return result;
  });
}
