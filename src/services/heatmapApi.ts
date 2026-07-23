import type { AddCameraPayload, Analytics, CameraStatus } from "../types/heatmap";

const PREFIX = "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${PREFIX}${path}`;
  try {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(`${res.status}: ${detail}`);
    }
    return res.json() as Promise<T>;
  } catch {
    // Direct fallback if proxy is bypassed
    const host = typeof window !== "undefined" && window.location.hostname ? window.location.hostname : "localhost";
    const directUrl = `http://${host}:8000/api/v1${path}`;
    const res = await fetch(directUrl, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(`${res.status}: ${detail}`);
    }
    return res.json() as Promise<T>;
  }
}

export const heatmapApi = {
  health: () => request<Record<string, unknown>>("/health"),

  listCameras: () => request<CameraStatus[]>("/camera/list"),

  addCamera: (payload: AddCameraPayload) =>
    request<CameraStatus>("/camera/add", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  removeCamera: (camera_id: string) =>
    request<{ status: string }>("/camera/remove", {
      method: "POST",
      body: JSON.stringify({ camera_id }),
    }),

  currentAnalytics: (camera_id: string) =>
    request<Analytics>(`/analytics/current?camera_id=${encodeURIComponent(camera_id)}`),

  mjpegUrl: (camera_id: string, kind: "overlay" | "raw" = "overlay") => {
    return `/api/v1/stream/mjpeg?camera_id=${encodeURIComponent(camera_id)}&kind=${kind}`;
  },
};

export function heatmapWsUrl(camera_id: string): string {
  const protocol = typeof window !== "undefined" && window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = typeof window !== "undefined" && window.location.host ? window.location.host : "localhost:5173";
  return `${protocol}//${host}/api/v1/stream/live?camera_id=${encodeURIComponent(camera_id)}&include_raw=1`;
}
