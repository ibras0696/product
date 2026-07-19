import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";

import type {
  SubmissionMedia,
  UploadSubmissionMediaInput,
} from "../domain/media";

export type UploadQueueStatus =
  | "queued"
  | "uploading"
  | "ambiguous"
  | "failed"
  | "cancelled"
  | "uploaded"
  | "saving"
  | "deleting";

export interface UploadQueueItem {
  clientId: string;
  idempotencyKey: string;
  file: File;
  previewUrl: string | null;
  metadata: Omit<UploadSubmissionMediaInput, "file">;
  media: SubmissionMedia | null;
  status: UploadQueueStatus;
  error: string | null;
}

export interface QueueRuntime {
  items: UploadQueueItem[];
  itemsRef: React.RefObject<UploadQueueItem[]>;
  controllers: React.RefObject<Map<string, AbortController>>;
  previews: React.RefObject<Map<string, string>>;
  notice: string | null;
  setNotice: Dispatch<SetStateAction<string | null>>;
  setItems(update: (current: UploadQueueItem[]) => UploadQueueItem[]): void;
  replaceItems(items: UploadQueueItem[]): void;
  patchItem(clientId: string, patch: Partial<UploadQueueItem>): void;
  revokePreview(clientId: string): void;
}

export function useQueueRuntime(): QueueRuntime {
  const [items, setItemsState] = useState<UploadQueueItem[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const itemsRef = useRef(items);
  const controllers = useRef(new Map<string, AbortController>());
  const previews = useRef(new Map<string, string>());
  const mounted = useRef(true);
  const setItems = useCallback(
    (update: (current: UploadQueueItem[]) => UploadQueueItem[]) => {
      if (!mounted.current) return;
      setItemsState((current) => {
        const next = update(current);
        itemsRef.current = next;
        return next;
      });
    },
    [],
  );
  const replaceItems = useCallback((next: UploadQueueItem[]) => {
    itemsRef.current = next;
    setItemsState(next);
  }, []);
  const patchItem = useCallback(
    (clientId: string, patch: Partial<UploadQueueItem>) => {
      setItems((current) =>
        current.map((item) =>
          item.clientId === clientId ? { ...item, ...patch } : item,
        ),
      );
    },
    [setItems],
  );
  const revokePreview = useCallback((clientId: string) => {
    const preview = previews.current.get(clientId);
    if (!preview) return;
    URL.revokeObjectURL(preview);
    previews.current.delete(clientId);
  }, []);
  useEffect(() => {
    mounted.current = true;
    const activeControllers = controllers.current;
    const activePreviews = previews.current;
    return () => {
      mounted.current = false;
      activeControllers.forEach((controller) => {
        controller.abort();
      });
      activePreviews.forEach((preview) => {
        URL.revokeObjectURL(preview);
      });
      activeControllers.clear();
      activePreviews.clear();
    };
  }, []);
  return {
    items,
    itemsRef,
    controllers,
    previews,
    notice,
    setNotice,
    setItems,
    replaceItems,
    patchItem,
    revokePreview,
  };
}
