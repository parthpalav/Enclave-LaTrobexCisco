import { useCallback, useEffect, useState } from "react";
import type { AddCameraPayload, CameraStatus } from "../types";
import { api } from "../services/api";
import { useLiveStream } from "../hooks/useLiveStream";
import CameraSidebar from "../components/CameraSidebar";
import HeatmapView from "../components/HeatmapView";
import AnalyticsPanel from "../components/AnalyticsPanel";

export default function Dashboard() {
  const [cameras, setCameras] = useState<CameraStatus[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [apiOnline, setApiOnline] = useState(false);
  const [geo, setGeo] = useState<{
    lat?: number;
    lon?: number;
    accuracy?: number;
    status: "requesting" | "ok" | "error";
    error?: string;
  }>({ status: "requesting" });

  const live = useLiveStream(selected);

  const refresh = useCallback(async () => {
    try {
      const list = await api.listCameras();
      setCameras(list);
      setApiOnline(true);
      setSelected((cur) => cur ?? (list[0]?.camera_id ?? null));
    } catch {
      setApiOnline(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 4000);
    return () => clearInterval(t);
  }, [refresh]);

  // Request high-precision HTML5 device geolocation and sync to backend.
  // watchPosition keeps refining as the browser gets a better fix, and reports
  // the exact coordinates + accuracy so you can confirm what was captured.
  useEffect(() => {
    if (!("geolocation" in navigator)) {
      setGeo({ status: "error", error: "Geolocation not supported by this browser" });
      return;
    }
    if (!window.isSecureContext) {
      setGeo({
        status: "error",
        error: "Blocked: open the app at http://localhost:5173 (not the 192.168… IP)",
      });
      return;
    }

    const id = navigator.geolocation.watchPosition(
      async (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        const accuracy = position.coords.accuracy;
        setGeo({ lat, lon, accuracy, status: "ok" });
        try {
          await fetch("http://localhost:8000/api/v1/location/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              latitude: lat,
              longitude: lon,
              location: `GPS (${lat.toFixed(5)}, ${lon.toFixed(5)})`,
            }),
          });
        } catch {
          // Ignore API offline during location sync
        }
      },
      (err) => {
        const reasons: Record<number, string> = {
          1: "Permission denied — allow location for this site",
          2: "Position unavailable — enable OS Location Services",
          3: "Timed out getting a fix",
        };
        setGeo({ status: "error", error: reasons[err.code] ?? err.message });
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );
    return () => navigator.geolocation.clearWatch(id);
  }, []);

  const handleAdd = async (payload: AddCameraPayload) => {
    await api.addCamera(payload);
    setSelected(payload.camera_id);
    await refresh();
  };

  const handleRemove = async (id: string) => {
    await api.removeCamera(id);
    if (selected === id) setSelected(null);
    await refresh();
  };

  return (
    <div className="min-h-screen p-4 md:p-6">
      <header className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold tracking-tight">
            CrowdVision <span className="text-accent">Heatmap Engine</span>
          </h1>
          <p className="text-xs text-white/40">
            YOLOv11 · ByteTrack · Gaussian KDE · real-time crowd analytics
          </p>
        </div>
        <div className="flex items-center gap-4">
          <span
            className="flex items-center gap-2 text-xs text-white/60"
            title={geo.error ?? ""}
          >
            {geo.status === "ok" ? (
              <>
                📍 {geo.lat!.toFixed(5)}, {geo.lon!.toFixed(5)}
                {geo.accuracy != null && (
                  <span className="text-white/35">±{Math.round(geo.accuracy)}m</span>
                )}
              </>
            ) : geo.status === "requesting" ? (
              <span className="text-white/40">📍 locating…</span>
            ) : (
              <span className="text-yellow-400">📍 {geo.error}</span>
            )}
          </span>
          <span className="flex items-center gap-2 text-xs text-white/50">
            <span
              className={`h-2 w-2 rounded-full ${apiOnline ? "bg-green-400" : "bg-red-500"}`}
            />
            API {apiOnline ? "online" : "offline"}
          </span>
        </div>
      </header>

      <div className="flex flex-col md:flex-row gap-6">
        <CameraSidebar
          cameras={cameras}
          selected={selected}
          onSelect={setSelected}
          onAdd={handleAdd}
          onRemove={handleRemove}
        />

        <main className="flex-1 flex flex-col gap-4">
          {selected ? (
            <>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Original camera (raw MJPEG preview) */}
                <HeatmapView
                  title="Original Camera"
                  connected={live.connected}
                  image={live.rawImage ?? api.mjpegUrl(selected, "raw")}
                />
                {/* Heatmap overlay (WebSocket base64 frames) */}
                <HeatmapView
                  title="Crowd Heatmap"
                  connected={live.connected}
                  image={live.image}
                />
              </div>
              <AnalyticsPanel analytics={live.analytics} fps={live.status?.fps} />
            </>
          ) : (
            <div className="card p-10 text-center text-white/40">
              Add or select a camera to view the live heatmap.
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
