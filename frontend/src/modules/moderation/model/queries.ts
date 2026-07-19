import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { ModerationPort } from "../api/moderationPort";
import type {
  ModerationClaimInput,
  ModerationDecisionInput,
  ModerationFilters,
  PublishCommand,
} from "../domain/types";

export const moderationKeys = {
  queue: (filters: ModerationFilters) =>
    ["moderation", "queue", filters] as const,
  detail: (id: string) => ["moderation", "detail", id] as const,
};

export function useModerationQueue(
  port: ModerationPort,
  filters: ModerationFilters,
) {
  return useQuery({
    queryKey: moderationKeys.queue(filters),
    queryFn: ({ signal }) => port.getQueue(filters, signal),
    retry: false,
  });
}

export function useModerationDetail(
  port: ModerationPort,
  submissionId: string | null,
) {
  return useQuery({
    queryKey: moderationKeys.detail(submissionId ?? "none"),
    queryFn: ({ signal }) => port.getSubmission(submissionId ?? "", signal),
    enabled: submissionId !== null,
    retry: false,
  });
}

export function useModerationActions(
  port: ModerationPort,
  submissionId: string | null,
) {
  const client = useQueryClient();
  const refresh = async () => {
    await client.invalidateQueries({ queryKey: ["moderation", "queue"] });
    if (submissionId) {
      await client.invalidateQueries({
        queryKey: moderationKeys.detail(submissionId),
      });
    }
  };

  const claim = useMutation({
    mutationFn: ({ id, input }: { id: string; input: ModerationClaimInput }) =>
      port.claimSubmission(id, input, new AbortController().signal),
    onSuccess: refresh,
    retry: false,
  });
  const revision = useMutation({
    mutationFn: (input: ModerationDecisionInput) =>
      port.requestRevision(
        submissionId ?? "",
        input,
        new AbortController().signal,
      ),
    onSuccess: refresh,
    retry: false,
  });
  const reject = useMutation({
    mutationFn: (input: ModerationDecisionInput) =>
      port.rejectSubmission(
        submissionId ?? "",
        input,
        new AbortController().signal,
      ),
    onSuccess: refresh,
    retry: false,
  });
  const publish = useMutation({
    mutationFn: (input: PublishCommand) =>
      port.publishSubmission(
        submissionId ?? "",
        input,
        new AbortController().signal,
      ),
    onSuccess: refresh,
    retry: false,
  });

  return { claim, revision, reject, publish };
}
