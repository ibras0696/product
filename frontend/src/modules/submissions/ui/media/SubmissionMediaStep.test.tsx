import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { SubmissionsPort } from "../../api/submissionsPort";
import type {
  SubmissionMedia,
  UploadSubmissionMediaInput,
} from "../../domain/media";
import { useUploadQueue } from "../../model/uploadQueue";
import { SubmissionMediaStep } from "./SubmissionMediaStep";

function uploaded(input: UploadSubmissionMediaInput): SubmissionMedia {
  return {
    id: `media-${input.file.name}`,
    submissionId: "submission-1",
    originalName: input.file.name,
    mimeType: input.file.type,
    sizeBytes: input.file.size,
    width: 1200,
    height: 800,
    previewUrl: `/server/${input.file.name}`,
    caption: input.caption,
    author: input.author,
    approximateDate: input.approximateDate,
    sourceDescription: input.sourceDescription,
    relatedEntityId: input.relatedEntityId,
    status: "pending",
  };
}

function createPort(): SubmissionsPort {
  return {
    createSubmission: () => Promise.reject(new Error("unused")),
    patchSubmission: () => Promise.reject(new Error("unused")),
    submitSubmission: () => Promise.reject(new Error("unused")),
    getSubmissionStatus: () => Promise.reject(new Error("unused")),
    getSubmissionMedia: () => Promise.resolve([]),
    uploadSubmissionMedia: async (_submissionId, input, _key, signal) => {
      if (input.file.name !== "pending.jpg") return uploaded(input);
      return new Promise<SubmissionMedia>((_resolve, reject) => {
        signal.addEventListener("abort", () => {
          reject(new DOMException("cancelled", "AbortError"));
        });
      });
    },
    patchSubmissionMedia: () => Promise.reject(new Error("unused")),
    deleteSubmissionMedia: () => Promise.resolve(null),
  };
}

function MediaHarness() {
  const queue = useUploadQueue(createPort(), "submission-1");
  return <SubmissionMediaStep queue={queue} />;
}

it("announces upload state and revokes every local object URL at its lifecycle boundary", async () => {
  const createUrl = vi.fn((file: File) => `blob:${file.name}`);
  const revokeUrl = vi.fn<(url: string) => void>();
  Object.defineProperty(URL, "createObjectURL", {
    configurable: true,
    value: createUrl,
  });
  Object.defineProperty(URL, "revokeObjectURL", {
    configurable: true,
    value: revokeUrl,
  });
  const user = userEvent.setup();
  const { unmount } = render(<MediaHarness />);
  const input = screen.getByLabelText("Выбрать файлы");

  await user.upload(input, [
    new File(["ok"], "success.jpg", { type: "image/jpeg" }),
    new File(["wait"], "pending.jpg", { type: "image/jpeg" }),
  ]);
  await waitFor(() => {
    expect(screen.getByText("Загружен")).toBeVisible();
    expect(screen.getByText("Загружается")).toBeVisible();
  });
  expect(
    screen.getByRole("progressbar", { name: "Загрузка pending.jpg" }),
  ).toBeVisible();
  expect(revokeUrl).toHaveBeenCalledWith("blob:success.jpg");

  unmount();
  expect(revokeUrl.mock.calls.map(([url]) => url)).toEqual([
    "blob:success.jpg",
    "blob:pending.jpg",
  ]);
});
