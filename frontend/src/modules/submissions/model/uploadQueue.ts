import { useCallback } from "react";

import {
  MAX_SUBMISSION_MEDIA,
  precheckSubmissionMedia,
} from "../api/mediaPrecheck";
import type { SubmissionsPort } from "../api/submissionsPort";
import { SubmissionApplicationError } from "../domain/errors";
import type { PatchSubmissionMediaInput } from "../domain/media";
import {
  useQueueRuntime,
  type QueueRuntime,
  type UploadQueueItem,
  type UploadQueueStatus,
} from "./uploadQueueRuntime";

export type { UploadQueueItem, UploadQueueStatus } from "./uploadQueueRuntime";

export interface UploadQueueController {
  items: UploadQueueItem[];
  notice: string | null;
  queueFiles(files: readonly File[]): string[];
  upload(clientIds: readonly string[]): void;
  retry(clientId: string): void;
  cancel(clientId: string): void;
  remove(clientId: string): void;
  updateMetadata(clientId: string, patch: PatchSubmissionMediaInput): void;
  isMetadataLocked(item: UploadQueueItem): boolean;
}

const defaultMetadata: UploadQueueItem["metadata"] = {
  caption: "",
  author: "",
  approximateDate: null,
  sourceDescription: "",
  relatedEntityId: null,
};

const precheckMessages = {
  unsupported_media_type: "Поддерживаются только JPEG, PNG и WebP.",
  payload_too_large: "Размер файла не должен превышать 10 МиБ.",
  media_rejected: "Пустой или повреждённый файл нельзя загрузить.",
} as const;

function failureMessage(error: unknown) {
  if (error instanceof SubmissionApplicationError) return error.message;
  return "Не удалось выполнить операцию. Попробуйте ещё раз.";
}

function failedStatus(error: unknown): UploadQueueStatus {
  if (error instanceof DOMException && error.name === "AbortError")
    return "cancelled";
  if (
    error instanceof SubmissionApplicationError &&
    error.code === "service_unavailable"
  ) {
    return "ambiguous";
  }
  return "failed";
}

export function isUploadMetadataLocked(item: UploadQueueItem) {
  return ["uploading", "ambiguous", "saving", "deleting"].includes(item.status);
}

function useUploadRunner(
  runtime: QueueRuntime,
  port: SubmissionsPort,
  submissionId: string,
) {
  return useCallback(
    async (item: UploadQueueItem) => {
      const controller = new AbortController();
      runtime.controllers.current.set(item.clientId, controller);
      runtime.patchItem(item.clientId, { status: "uploading", error: null });
      try {
        const media = await port.uploadSubmissionMedia(
          submissionId,
          { file: item.file, ...item.metadata },
          item.idempotencyKey,
          controller.signal,
        );
        runtime.revokePreview(item.clientId);
        runtime.patchItem(item.clientId, {
          media,
          previewUrl: null,
          metadata: {
            caption: media.caption,
            author: media.author,
            approximateDate: media.approximateDate,
            sourceDescription: media.sourceDescription,
            relatedEntityId: media.relatedEntityId,
          },
          status: "uploaded",
        });
      } catch (error) {
        runtime.patchItem(item.clientId, {
          status: failedStatus(error),
          error: failureMessage(error),
        });
      } finally {
        runtime.controllers.current.delete(item.clientId);
      }
    },
    [port, runtime, submissionId],
  );
}

function queueFiles(runtime: QueueRuntime, files: readonly File[]) {
  runtime.setNotice(null);
  const available = Math.max(
    MAX_SUBMISSION_MEDIA - runtime.itemsRef.current.length,
    0,
  );
  const accepted: UploadQueueItem[] = [];
  for (const file of files) {
    if (accepted.length >= available) break;
    const result = precheckSubmissionMedia(file);
    if (!result.ok) {
      runtime.setNotice(precheckMessages[result.code]);
      continue;
    }
    const clientId = crypto.randomUUID();
    const previewUrl = URL.createObjectURL(file);
    runtime.previews.current.set(clientId, previewUrl);
    accepted.push({
      clientId,
      idempotencyKey: crypto.randomUUID(),
      file,
      previewUrl,
      metadata: { ...defaultMetadata },
      media: null,
      status: "queued",
      error: null,
    });
  }
  if (files.length > available)
    runtime.setNotice("К заявке можно добавить не более 10 файлов.");
  runtime.replaceItems([...runtime.itemsRef.current, ...accepted]);
  return accepted.map((item) => item.clientId);
}

function removeItem(
  runtime: QueueRuntime,
  port: SubmissionsPort,
  submissionId: string,
  clientId: string,
) {
  const item = runtime.itemsRef.current.find(
    (candidate) => candidate.clientId === clientId,
  );
  if (!item || isUploadMetadataLocked(item)) return;
  if (!item.media) {
    runtime.revokePreview(clientId);
    runtime.setItems((current) =>
      current.filter((candidate) => candidate.clientId !== clientId),
    );
    return;
  }
  runtime.patchItem(clientId, { status: "deleting", error: null });
  const controller = new AbortController();
  runtime.controllers.current.set(clientId, controller);
  void port
    .deleteSubmissionMedia(submissionId, item.media.id, controller.signal)
    .then(() => {
      runtime.revokePreview(clientId);
      runtime.setItems((current) =>
        current.filter((candidate) => candidate.clientId !== clientId),
      );
    })
    .catch((error: unknown) => {
      runtime.patchItem(clientId, {
        status: "uploaded",
        error: failureMessage(error),
      });
    })
    .finally(() => {
      runtime.controllers.current.delete(clientId);
    });
}

function updateMetadata(
  runtime: QueueRuntime,
  port: SubmissionsPort,
  submissionId: string,
  clientId: string,
  patch: PatchSubmissionMediaInput,
) {
  const item = runtime.itemsRef.current.find(
    (candidate) => candidate.clientId === clientId,
  );
  if (!item || isUploadMetadataLocked(item)) return;
  runtime.patchItem(clientId, {
    metadata: { ...item.metadata, ...patch },
    error: null,
  });
  if (!item.media) return;
  runtime.patchItem(clientId, { status: "saving" });
  const controller = new AbortController();
  runtime.controllers.current.set(clientId, controller);
  void port
    .patchSubmissionMedia(submissionId, item.media.id, patch, controller.signal)
    .then((media) => {
      runtime.patchItem(clientId, { media, status: "uploaded" });
    })
    .catch((error: unknown) => {
      runtime.patchItem(clientId, {
        status: "uploaded",
        error: failureMessage(error),
      });
    })
    .finally(() => {
      runtime.controllers.current.delete(clientId);
    });
}

export function useUploadQueue(
  port: SubmissionsPort,
  submissionId: string,
): UploadQueueController {
  const runtime = useQueueRuntime();
  const runUpload = useUploadRunner(runtime, port, submissionId);
  return {
    items: runtime.items,
    notice: runtime.notice,
    queueFiles: (files) => queueFiles(runtime, files),
    upload: (clientIds) => {
      const requested = new Set(clientIds);
      runtime.itemsRef.current
        .filter(
          (item) => requested.has(item.clientId) && item.status === "queued",
        )
        .forEach((item) => {
          void runUpload(item);
        });
    },
    retry: (clientId) => {
      const item = runtime.itemsRef.current.find(
        (candidate) => candidate.clientId === clientId,
      );
      if (item && ["failed", "ambiguous", "cancelled"].includes(item.status))
        void runUpload(item);
    },
    cancel: (clientId) => {
      runtime.controllers.current.get(clientId)?.abort();
    },
    remove: (clientId) => {
      removeItem(runtime, port, submissionId, clientId);
    },
    updateMetadata: (clientId, patch) => {
      updateMetadata(runtime, port, submissionId, clientId, patch);
    },
    isMetadataLocked: isUploadMetadataLocked,
  };
}
