// Empty by default: the API serves the built site from the same origin, so the
// browser calls "/api/v1/...". In `npm run dev` (port 3000) .env.development points
// it at the API on port 8000.
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

async function request(path: string, init?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...init,
  });
  let body: any = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  if (!res.ok) {
    const msg =
      body?.error?.message || body?.detail?.message || body?.detail || res.statusText;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return body;
}

export const api = {
  region: () => request("/api/v1/meta/region"),
  sources: () => request("/api/v1/meta/sources"),
  createFarm: (payload: any) =>
    request("/api/v1/farms", { method: "POST", body: JSON.stringify(payload) }),
  context: (farmId: string) => request(`/api/v1/farms/${farmId}/context`),
  optimize: (farmId: string, payload: any = {}) =>
    request(`/api/v1/farms/${farmId}/rotation:optimize`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  job: (jobId: string) => request(`/api/v1/jobs/${jobId}`),
  diseases: (farmId: string, cropIds?: string[]) => {
    const qs = (cropIds || []).map((c) => `crop_id=${encodeURIComponent(c)}`).join("&");
    return request(`/api/v1/farms/${farmId}/diseases${qs ? `?${qs}` : ""}`);
  },
  hazards: (farmId: string) => request(`/api/v1/farms/${farmId}/hazards`),
  irrigation: (farmId: string, payload: any = {}) =>
    request(`/api/v1/farms/${farmId}/irrigation`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  timeline: (farmId: string, layer: string) =>
    request(`/api/v1/farms/${farmId}/timeline?layer=${layer}`),
  imageryLayers: () => request("/api/v1/imagery/layers"),
  catalogCrops: () => request("/api/v1/catalog/crops"),
  updateRotation: (farmId: string, rotationId: string, sequence: string[]) =>
    request(`/api/v1/farms/${farmId}/rotations/${rotationId}`, {
      method: "PUT",
      body: JSON.stringify({ sequence }),
    }),
};

export function reportUrl(farmId: string, kind: "pdf" | "csv", rotationId: string, locale: string) {
  const params = new URLSearchParams({ rotation_id: rotationId, locale });
  return `${API_BASE}/api/v1/farms/${farmId}/report.${kind}?${params.toString()}`;
}

export async function downloadFile(url: string, filename: string) {
  const res = await fetch(url, { credentials: "include" });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.error?.message || `download failed (${res.status})`);
  }
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

export async function waitForJob(jobId: string, onProgress?: (j: any) => void, timeoutMs = 120000) {  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const j = await api.job(jobId);
    const data = j.data;
    if (onProgress) onProgress(data);
    if (data.status === "done") return data.result;
    if (data.status === "failed") throw new Error(data.error || "job failed");
    await new Promise((r) => setTimeout(r, 350));
  }
  throw new Error("job timed out");
}
