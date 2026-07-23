import type { AddCameraPayload, Analytics, CameraStatus } from "../types";

// In dev, requests go through the Vite proxy (/api). In prod set VITE_API_BASE.
const API_BASE = import.meta.env.VITE_API_BASE ?? "";
const PREFIX = `${API_BASE}/api/v1`;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${PREFIX}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
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

  history: (camera_id: string, minutes = 30) =>
    request<Analytics[]>(
      `/analytics/history?camera_id=${encodeURIComponent(camera_id)}&minutes=${minutes}`
    ),

  mjpegUrl: (camera_id: string, kind: "overlay" | "raw" = "overlay") =>
    `${PREFIX}/stream/mjpeg?camera_id=${encodeURIComponent(camera_id)}&kind=${kind}`,
};

export function wsUrl(camera_id: string): string {
  const base = API_BASE || window.location.origin;
  const url = new URL(`${base}/api/v1/stream/live`);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.searchParams.set("camera_id", camera_id);
  // Stream the original camera preview over the same socket as the heatmap so
  // both panes share one reliable transport (MJPEG <img> never auto-reconnects).
  url.searchParams.set("include_raw", "1");
  return url.toString();
}
