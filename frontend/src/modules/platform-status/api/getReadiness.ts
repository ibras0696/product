export interface ComponentStatus {
  name: string;
  healthy: boolean;
}

interface ApiResponse<T> {
  ok: boolean;
  data: T | null;
  error: { message: string } | null;
}

export interface Readiness {
  status: "ready" | "not_ready";
  components: ComponentStatus[];
}

export async function getReadiness(signal?: AbortSignal): Promise<Readiness> {
  const response = await fetch("/api/health/ready", { signal });
  const payload = (await response.json()) as ApiResponse<Readiness>;
  if (!response.ok || !payload.ok || !payload.data) {
    throw new Error(
      payload.error?.message ?? "Platform dependencies are unavailable",
    );
  }
  return payload.data;
}
