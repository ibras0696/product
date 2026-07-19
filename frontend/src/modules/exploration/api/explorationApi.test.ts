import { afterEach, vi } from "vitest";

import { chechnyaRequestBbox } from "../model/chechnyaBoundary";
import { MAP_LIMIT } from "./filtering";
import { explorationApi } from "./explorationApi";

const signal = new AbortController().signal;

function apiResponse(data: unknown): Response {
  return new Response(
    JSON.stringify({
      ok: true,
      data,
      error: null,
      meta: { request_id: "exploration-test" },
    }),
    { status: 200, headers: { "Content-Type": "application/json" } },
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

it("requests the bounded full research layer across the northern boundary", async () => {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
    apiResponse({
      items: [],
      relations: [],
      truncated: false,
      relations_truncated: false,
    }),
  );
  vi.stubGlobal("fetch", fetchMock);

  await explorationApi.getMapEntities({}, signal);

  const request = fetchMock.mock.calls[0][0];
  if (typeof request !== "string") throw new Error("Expected URL request");
  const requestUrl = new URL(request, "http://localhost");
  expect(requestUrl.searchParams.get("bbox")).toBe(chechnyaRequestBbox);
  expect(requestUrl.searchParams.get("limit")).toBe(String(MAP_LIMIT));
  expect(requestUrl.searchParams.get("zoom")).toBe("6");
  expect(Number(chechnyaRequestBbox.split(",")[3])).toBeGreaterThan(44.01);
});

it("forwards the selected research statuses and open date range to the map", async () => {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
    apiResponse({
      items: [],
      relations: [],
      truncated: false,
      relations_truncated: false,
    }),
  );
  vi.stubGlobal("fetch", fetchMock);

  await explorationApi.getMapEntities(
    {
      researchStatuses: ["needs_review"],
      periodFrom: 1800,
      periodTo: 1950,
    },
    signal,
  );

  const request = fetchMock.mock.calls[0][0];
  if (typeof request !== "string") throw new Error("Expected URL request");
  const params = new URL(request, "http://localhost").searchParams;
  expect(params.getAll("research_statuses")).toEqual(["needs_review"]);
  expect(params.get("period_from")).toBe("1800");
  expect(params.get("period_to")).toBe("1950");
});

it("keeps natural objects distinct from settlements in the map view model", async () => {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
    apiResponse({
      items: [
        {
          id: "54dbef9b-048a-5508-8512-dd51a8a8e714",
          type: "natural_object",
          title: { ru: "Нефтянка", ce: null },
          coordinates: { latitude: 43.4106, longitude: 45.4771 },
          relations_count: 2,
          cover_url: null,
          district_id: null,
          research_status: "needs_review",
        },
      ],
      relations: [],
      truncated: false,
      relations_truncated: false,
    }),
  );
  vi.stubGlobal("fetch", fetchMock);

  const result = await explorationApi.getMapEntities({}, signal);

  expect(result.items[0]).toMatchObject({
    entityType: "natural_object",
    kind: "landmark",
    name: "Нефтянка",
  });
});

it("maps backend map relations into the runtime relation layer", async () => {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
    apiResponse({
      items: [],
      relations: [
        {
          id: "30000000-0000-4000-8000-000000000001",
          source_id: "10000000-0000-4000-8000-000000000001",
          target_id: "10000000-0000-4000-8000-000000000002",
          type: "connected_with",
          source_type: "person",
          source_title: "Историческая личность",
          target_type: "settlement",
          target_title: "Грозный",
        },
      ],
      truncated: false,
      relations_truncated: true,
    }),
  );
  vi.stubGlobal("fetch", fetchMock);

  const result = await explorationApi.getMapEntities({}, signal);

  expect(result.relations).toEqual([
    {
      from: "10000000-0000-4000-8000-000000000001",
      to: "10000000-0000-4000-8000-000000000002",
      fromKind: "person",
      fromName: "Историческая личность",
      toKind: "place",
      toName: "Грозный",
    },
  ]);
  expect(result.relationsTruncated).toBe(true);
});

it("places relation-only entities around a geographic endpoint", async () => {
  const targetId = "10000000-0000-4000-8000-000000000002";
  const sourceId = "10000000-0000-4000-8000-000000000001";
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
    apiResponse({
      items: [
        {
          id: targetId,
          type: "settlement",
          title: { ru: "Грозный", ce: null },
          coordinates: { latitude: 43.318, longitude: 45.698 },
          relations_count: 1,
          cover_url: null,
          district_id: null,
          research_status: "verified",
        },
      ],
      relations: [
        {
          id: "30000000-0000-4000-8000-000000000001",
          source_id: sourceId,
          target_id: targetId,
          type: "connected_with",
          source_type: "person",
          source_title: "Историческая личность",
          target_type: "settlement",
          target_title: "Грозный",
        },
      ],
      truncated: false,
      relations_truncated: false,
    }),
  );
  vi.stubGlobal("fetch", fetchMock);

  const result = await explorationApi.getMapEntities({}, signal);
  expect(result.items).toHaveLength(2);
  expect(result.items.find((item) => item.id === sourceId)).toMatchObject({
    kind: "person",
    name: "Историческая личность",
    virtualAnchorId: targetId,
    coordinates: [45.698, 43.318],
  });
});

it("loads the selected production graph at depth two", async () => {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
    apiResponse({
      center: {
        id: "10000000-0000-4000-8000-000000000001",
        type: "settlement",
        title: { ru: "Грозный", ce: null },
      },
      nodes: [],
      edges: [],
      hidden_nodes_count: 0,
    }),
  );
  vi.stubGlobal("fetch", fetchMock);

  await explorationApi.getGraph(
    "10000000-0000-4000-8000-000000000001",
    { periodFrom: 1800, periodTo: 1950, researchStatuses: ["needs_review"] },
    signal,
  );

  expect(fetchMock.mock.calls[0][0]).toBe(
    "/api/v1/entities/10000000-0000-4000-8000-000000000001/graph?depth=2&limit=40&period_from=1800&period_to=1950",
  );
});
