import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch, ApiError } from "./client";
import { getAccessToken, setAccessToken } from "./tokenStore";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("apiFetch", () => {
  beforeEach(() => {
    setAccessToken(null);
    document.cookie = "csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns parsed JSON on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(200, { status: "ok" })),
    );

    const result = await apiFetch<{ status: string }>("/health/live");

    expect(result).toEqual({ status: "ok" });
  });

  it("attaches the bearer token when one is set", async () => {
    setAccessToken("my-token");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, {}));
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/tasks");

    const headers = fetchMock.mock.calls[0][1].headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer my-token");
  });

  it("throws an ApiError with the backend's structured error body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(404, {
          error: { code: "TASK_NOT_FOUND", message: "Task not found", request_id: "abc" },
        }),
      ),
    );

    await expect(apiFetch("/tasks/missing")).rejects.toMatchObject({
      status: 404,
      code: "TASK_NOT_FOUND",
      message: "Task not found",
    } satisfies Partial<ApiError>);
  });

  it("returns undefined for 204 No Content", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));

    const result = await apiFetch("/tasks/1");

    expect(result).toBeUndefined();
  });

  it("retries once after a silent refresh on 401, then gives up on repeated 401s", async () => {
    document.cookie = "csrf_token=test-csrf";
    const fetchMock = vi
      .fn()
      // 1. original request -> 401
      .mockResolvedValueOnce(
        jsonResponse(401, { error: { code: "NOT_AUTHENTICATED", message: "nope", request_id: null } }),
      )
      // 2. refresh -> success
      .mockResolvedValueOnce(jsonResponse(200, { access_token: "new-token" }))
      // 3. retried request -> success
      .mockResolvedValueOnce(jsonResponse(200, { data: "secret" }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await apiFetch<{ data: string }>("/tasks");

    expect(result).toEqual({ data: "secret" });
    expect(getAccessToken()).toBe("new-token");
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});
