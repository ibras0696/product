import { act, renderHook, waitFor } from "@testing-library/react";

import type { SubmissionsPort } from "../api/submissionsPort";
import { submissionError } from "../domain/errors";
import type {
  PatchSubmissionMediaInput,
  SubmissionMedia,
  UploadSubmissionMediaInput,
} from "../domain/media";
import { useUploadQueue } from "./uploadQueue";

function image(name: string) {
  return new File([name], name, { type: "image/jpeg" });
}

function media(id: string, input: UploadSubmissionMediaInput): SubmissionMedia {
  return {
    id,
    submissionId: "submission-1",
    originalName: input.file.name,
    mimeType: input.file.type,
    sizeBytes: input.file.size,
    width: 1200,
    height: 800,
    previewUrl: `/preview/${id}`,
    ...input,
    status: "pending",
  };
}

function createLifecyclePort() {
  const calls = new Map<string, string[]>();
  const stored = new Map<string, SubmissionMedia>();
  const attempts = new Map<string, number>();
  const upload = async (
    _submissionId: string,
    input: UploadSubmissionMediaInput,
    key: string,
    signal: AbortSignal,
  ) => {
    calls.set(input.file.name, [...(calls.get(input.file.name) ?? []), key]);
    const attempt = (attempts.get(input.file.name) ?? 0) + 1;
    attempts.set(input.file.name, attempt);
    if (input.file.name === "hold.jpg") {
      return new Promise<SubmissionMedia>((_resolve, reject) => {
        signal.addEventListener("abort", () => {
          reject(new DOMException("cancelled", "AbortError"));
        });
      });
    }
    if (input.file.name === "failed.jpg" && attempt === 1) {
      throw submissionError("media_rejected", "Файл отклонён");
    }
    const existing = stored.get(key);
    if (existing) return existing;
    const uploaded = media(`media-${String(stored.size + 1)}`, input);
    stored.set(key, uploaded);
    if (input.file.name === "lost.jpg" && attempt === 1) {
      throw submissionError("service_unavailable", "Ответ потерян");
    }
    return uploaded;
  };
  const patch = (
    _submissionId: string,
    mediaId: string,
    update: PatchSubmissionMediaInput,
  ) => {
    const entry = [...stored.entries()].find(
      ([, value]) => value.id === mediaId,
    );
    if (!entry) throw submissionError("not_found", "Медиа не найдено");
    const updated = { ...entry[1], ...update };
    stored.set(entry[0], updated);
    return Promise.resolve(updated);
  };
  const port: SubmissionsPort = {
    createSubmission: () => Promise.reject(new Error("unused")),
    patchSubmission: () => Promise.reject(new Error("unused")),
    submitSubmission: () => Promise.reject(new Error("unused")),
    getSubmissionStatus: () => Promise.reject(new Error("unused")),
    getSubmissionMedia: () => Promise.resolve([...stored.values()]),
    uploadSubmissionMedia: upload,
    patchSubmissionMedia: patch,
    deleteSubmissionMedia: (_submissionId, mediaId) => {
      const entry = [...stored.entries()].find(
        ([, value]) => value.id === mediaId,
      );
      if (entry) stored.delete(entry[0]);
      return Promise.resolve(null);
    },
  };
  return { port, calls, stored };
}

beforeEach(() => {
  Object.defineProperty(URL, "createObjectURL", {
    configurable: true,
    value: vi.fn((file: File) => `blob:${file.name}`),
  });
  Object.defineProperty(URL, "revokeObjectURL", {
    configurable: true,
    value: vi.fn(),
  });
});

it("handles a partial parallel upload, same-key replay, cancellation and media edits", async () => {
  const { port, calls, stored } = createLifecyclePort();
  const { result } = renderHook(() => useUploadQueue(port, "submission-1"));
  let ids: string[] = [];
  act(() => {
    ids = result.current.queueFiles([
      image("ok.jpg"),
      image("failed.jpg"),
      image("lost.jpg"),
      image("hold.jpg"),
    ]);
    result.current.upload(ids);
  });

  await waitFor(() => {
    expect(result.current.items.map((item) => item.status)).toEqual([
      "uploaded",
      "failed",
      "ambiguous",
      "uploading",
    ]);
  });
  const okKey = calls.get("ok.jpg")?.[0];
  const lostKey = calls.get("lost.jpg")?.[0];

  act(() => {
    result.current.retry(ids[1] ?? "");
    result.current.retry(ids[2] ?? "");
    result.current.cancel(ids[3] ?? "");
  });
  await waitFor(() => {
    expect(result.current.items.map((item) => item.status)).toEqual([
      "uploaded",
      "uploaded",
      "uploaded",
      "cancelled",
    ]);
  });
  expect(calls.get("ok.jpg")).toEqual([okKey]);
  expect(calls.get("lost.jpg")).toEqual([lostKey, lostKey]);
  expect(stored).toHaveLength(3);

  act(() => {
    result.current.updateMetadata(ids[2] ?? "", { caption: "Башня" });
  });
  await waitFor(() => {
    expect(result.current.items[2]?.media?.caption).toBe("Башня");
  });
  act(() => {
    result.current.remove(ids[0] ?? "");
    const queued = result.current.queueFiles([image("queued.jpg")]);
    result.current.remove(queued[0] ?? "");
  });
  await waitFor(() => {
    expect(stored).toHaveLength(2);
    expect(
      result.current.items.some((item) => item.file.name === "queued.jpg"),
    ).toBe(false);
  });
});
