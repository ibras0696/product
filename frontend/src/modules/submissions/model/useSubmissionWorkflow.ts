import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { submissionError } from "../domain/errors";
import type {
  CreateSubmissionInput,
  PatchSubmissionInput,
  SubmissionDraft,
  SubmissionStatusView,
} from "../domain/submission";
import type { SubmissionsPort } from "../api/submissionsPort";

function signal() {
  return new AbortController().signal;
}

export function useSubmissionWorkflow(port: SubmissionsPort) {
  const [draft, setDraft] = useState<SubmissionDraft | null>(null);
  const [receipt, setReceipt] = useState<SubmissionStatusView | null>(null);

  const createMutation = useMutation({
    mutationFn: (input: CreateSubmissionInput) =>
      port.createSubmission(input, signal()),
    onSuccess: setDraft,
  });
  const patchMutation = useMutation({
    mutationFn: (patch: PatchSubmissionInput) => {
      if (!draft) {
        return Promise.reject(
          submissionError("bad_request", "Сначала создайте черновик"),
        );
      }
      return port.patchSubmission(draft.id, draft.version, patch, signal());
    },
    onSuccess: setDraft,
  });
  const submitMutation = useMutation({
    mutationFn: (persistedDraft?: SubmissionDraft) => {
      const current = persistedDraft ?? draft;
      if (!current) {
        return Promise.reject(
          submissionError("bad_request", "Черновик не найден"),
        );
      }
      return port.submitSubmission(current.id, current.version, signal());
    },
    onSuccess: setReceipt,
  });
  const statusMutation = useMutation({
    mutationFn: (trackingCode: string) =>
      port.getSubmissionStatus(trackingCode, signal()),
  });

  return {
    draft,
    receipt,
    createMutation,
    patchMutation,
    submitMutation,
    statusMutation,
    setDraft,
    reset() {
      setDraft(null);
      setReceipt(null);
      createMutation.reset();
      patchMutation.reset();
      submitMutation.reset();
      statusMutation.reset();
    },
  };
}

export type SubmissionWorkflow = ReturnType<typeof useSubmissionWorkflow>;
