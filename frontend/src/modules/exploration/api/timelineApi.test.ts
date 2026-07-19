import { afterEach, vi } from "vitest";

import { explorationApi } from "./explorationApi";

const signal = new AbortController().signal;

afterEach(() => {
  vi.unstubAllGlobals();
});

it("requests published events with normalized filters and maps the API page", async () => {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
    apiResponse({
      items: [
        {
          id: "c7325552-1119-59d7-9dfc-b28337d04b49",
          title: { ru: "Восстание шейха Мансура", ce: null },
          short_description: { ru: "Историческое событие", ce: null },
          period_from: 1785,
          period_to: 1791,
          coordinates: null,
        },
      ],
      meta: { limit: 100, offset: 0, total: 1 },
    }),
  );
  vi.stubGlobal("fetch", fetchMock);

  const result = await explorationApi.getTimelineEvents(
    {
      query: "  восстание  ",
      districtId: "20000000-0000-4000-8000-000000000003",
      periodFrom: 1700,
      periodTo: 1800,
      limit: 500,
    },
    signal,
  );

  const [input, init] = fetchMock.mock.calls[0];
  const url = new URL(requestUrl(input), "https://example.test");
  expect(url.pathname).toBe("/api/v1/timeline/events");
  expect(Object.fromEntries(url.searchParams)).toEqual({
    q: "восстание",
    district_id: "20000000-0000-4000-8000-000000000003",
    period_from: "1700",
    period_to: "1800",
    limit: "100",
    offset: "0",
  });
  expect(init).toMatchObject({
    method: "GET",
    credentials: "same-origin",
    signal,
  });
  expect(result).toEqual({
    items: [
      {
        id: "c7325552-1119-59d7-9dfc-b28337d04b49",
        title: "Восстание шейха Мансура",
        shortDescription: "Историческое событие",
        periodFrom: 1785,
        periodTo: 1791,
        coordinates: null,
      },
    ],
    meta: { limit: 100, offset: 0, total: 1 },
  });
});

it("omits a query that is too short for the transport contract", async () => {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
    apiResponse({
      items: [],
      meta: { limit: 100, offset: 0, total: 0 },
    }),
  );
  vi.stubGlobal("fetch", fetchMock);

  await explorationApi.getTimelineEvents({ query: " я " }, signal);

  const url = new URL(
    requestUrl(fetchMock.mock.calls[0][0]),
    "https://example.test",
  );
  expect(url.searchParams.has("q")).toBe(false);
});

function apiResponse(data: unknown): Response {
  return new Response(
    JSON.stringify({
      ok: true,
      data,
      error: null,
      meta: { request_id: "timeline-test" },
    }),
    { status: 200, headers: { "Content-Type": "application/json" } },
  );
}

function requestUrl(input: string | URL | Request): string {
  if (typeof input === "string") return input;
  return input instanceof URL ? input.href : input.url;
}
