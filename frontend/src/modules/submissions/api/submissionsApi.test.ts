import { SubmissionApplicationError } from "../domain/errors";
import { submissionsApi } from "./submissionsApi";

const signal = new AbortController().signal;
const submissionId = "10000000-0000-4000-8000-000000000001";
const mediaId = "20000000-0000-4000-8000-000000000001";
const trackingCode = "t".repeat(43);

const createInput = {
  type: "new_entity",
  relatedEntityId: null,
  settlementId: null,
  title: "История башни",
  description: "Описание",
  sourceDescription: "Семейный архив",
  authorName: "Автор",
  contact: "author@example.test",
  consent: true,
} as const;

const draftDto = {
  id: submissionId,
  type: "new_entity",
  related_entity_id: null,
  settlement_id: null,
  title: "История башни",
  description: "Описание",
  source_description: "Семейный архив",
  author_name: "Автор",
  contact: "author@example.test",
  consent: true,
  status: "draft",
  version: 1,
  tracking_code: trackingCode,
  created_at: "2026-07-19T08:00:00Z",
  updated_at: "2026-07-19T08:00:00Z",
} as const;

const statusDto = {
  id: submissionId,
  tracking_code: trackingCode,
  type: "new_entity",
  title: "Уточнённая история",
  status: "pending",
  public_comment: null,
  submitted_at: "2026-07-19T08:05:00Z",
  updated_at: "2026-07-19T08:05:00Z",
} as const;

const mediaDto = {
  id: mediaId,
  submission_id: submissionId,
  original_name: "tower.jpg",
  mime_type: "image/jpeg",
  size_bytes: 5,
  width: 1200,
  height: 800,
  preview_url: `/api/v1/submissions/${submissionId}/media/${mediaId}/preview`,
  caption: "Башня",
  author: "Автор фото",
  approximate_date: null,
  source_description: "Архив",
  related_entity_id: null,
  status: "pending",
} as const;

function response(data: unknown, status = 200) {
  return new Response(
    JSON.stringify({
      ok: status >= 200 && status < 300,
      data: status >= 200 && status < 300 ? data : null,
      error: status >= 400 ? data : null,
      meta: { request_id: "request-1" },
    }),
    { status, headers: { "Content-Type": "application/json" } },
  );
}

function fetchMock(...responses: Response[]) {
  const mock = vi.fn<typeof fetch>();
  responses.forEach((item) => mock.mockResolvedValueOnce(item));
  vi.stubGlobal("fetch", mock);
  return mock;
}

function requestJson(fetch: ReturnType<typeof fetchMock>, index: number) {
  const body = fetch.mock.calls[index]?.[1]?.body;
  if (typeof body !== "string") throw new Error("Expected a JSON request body");
  return JSON.parse(body) as unknown;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

it("maps create, versioned patch, submit and private status lookup to the generated contract", async () => {
  const patchedDto = { ...draftDto, title: "Уточнённая история", version: 2 };
  const fetch = fetchMock(
    response(draftDto, 201),
    response(patchedDto),
    response(statusDto),
    response(statusDto),
  );

  const created = await submissionsApi.createSubmission(createInput, signal);
  const patched = await submissionsApi.patchSubmission(
    created.id,
    created.version,
    { title: "Уточнённая история" },
    signal,
  );
  const submitted = await submissionsApi.submitSubmission(
    patched.id,
    patched.version,
    signal,
  );
  const tracked = await submissionsApi.getSubmissionStatus(
    trackingCode,
    signal,
  );

  expect(created).toMatchObject({ trackingCode, version: 1 });
  expect(patched).toMatchObject({ title: "Уточнённая история", version: 2 });
  expect(submitted).toEqual(tracked);
  expect(fetch.mock.calls.map(([path]) => path)).toEqual([
    "/api/v1/submissions",
    `/api/v1/submissions/${submissionId}`,
    `/api/v1/submissions/${submissionId}/submit`,
    "/api/v1/submissions/status",
  ]);
  expect(requestJson(fetch, 1)).toEqual({
    expected_version: 1,
    title: "Уточнённая история",
  });
  expect(requestJson(fetch, 2)).toEqual({
    expected_version: 2,
  });
  expect(requestJson(fetch, 3)).toEqual({
    tracking_code: trackingCode,
  });
  fetch.mock.calls.forEach(([, init]) => {
    expect(init?.credentials).toBe("same-origin");
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  });
});

it("uploads, lists, edits and deletes owned media with one explicit idempotency key", async () => {
  const updatedDto = { ...mediaDto, caption: "Сторожевая башня" };
  const fetch = fetchMock(
    response(mediaDto, 201),
    response([mediaDto]),
    response(updatedDto),
    response(null),
  );
  const file = new File(["image"], "tower.jpg", { type: "image/jpeg" });

  const uploaded = await submissionsApi.uploadSubmissionMedia(
    submissionId,
    {
      file,
      caption: "Башня",
      author: "Автор фото",
      approximateDate: null,
      sourceDescription: "Архив",
      relatedEntityId: null,
    },
    "30000000-0000-4000-8000-000000000001",
    signal,
  );
  const listed = await submissionsApi.getSubmissionMedia(submissionId, signal);
  const updated = await submissionsApi.patchSubmissionMedia(
    submissionId,
    mediaId,
    { caption: "Сторожевая башня" },
    signal,
  );
  await submissionsApi.deleteSubmissionMedia(submissionId, mediaId, signal);

  expect(uploaded.originalName).toBe("tower.jpg");
  expect(listed).toHaveLength(1);
  expect(updated.caption).toBe("Сторожевая башня");
  const uploadInit = fetch.mock.calls[0]?.[1];
  expect(new Headers(uploadInit?.headers).get("Idempotency-Key")).toBe(
    "30000000-0000-4000-8000-000000000001",
  );
  const form = uploadInit?.body as FormData;
  expect(form.get("file")).toBe(file);
  expect(form.get("source_description")).toBe("Архив");
  expect(form.has("related_entity_id")).toBe(false);
  expect(fetch.mock.calls[3]?.[1]?.method).toBe("DELETE");
});

it.each([
  [409, "conflict", "conflict"],
  [404, "not_found", "not_found"],
  [422, undefined, "validation_error"],
] as const)(
  "maps backend ownership and lifecycle failure %s without trusting its message",
  async (status, backendCode, expectedCode) => {
    fetchMock(
      response(
        backendCode
          ? { code: backendCode, message: "Do not expose backend wording" }
          : { detail: [] },
        status,
      ),
    );

    const call = submissionsApi.patchSubmission(
      submissionId,
      1,
      { title: "Новая версия" },
      signal,
    );
    await expect(call).rejects.toBeInstanceOf(SubmissionApplicationError);
    await expect(call).rejects.toMatchObject({ code: expectedCode });
    await expect(call).rejects.not.toMatchObject({
      message: "Do not expose backend wording",
    });
  },
);
