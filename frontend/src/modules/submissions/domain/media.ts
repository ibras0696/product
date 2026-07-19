export interface UploadSubmissionMediaInput {
  file: File;
  caption: string;
  author: string;
  approximateDate: string | null;
  sourceDescription: string;
  relatedEntityId: string | null;
}

export type PatchSubmissionMediaInput = Partial<
  Omit<UploadSubmissionMediaInput, "file">
>;

export interface SubmissionMedia {
  id: string;
  submissionId: string;
  originalName: string;
  mimeType: string;
  sizeBytes: number;
  width: number;
  height: number;
  previewUrl: string;
  caption: string;
  author: string;
  approximateDate: string | null;
  sourceDescription: string;
  relatedEntityId: string | null;
  status: "pending";
}
