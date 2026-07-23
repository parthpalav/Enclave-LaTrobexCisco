import React, { useState, useEffect, useCallback } from "react";
import {
  Video,
  Eye,
  Settings,
  Plus,
  Trash2,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Copy,
  Loader2,
} from "lucide-react";
import type { AddCameraPayload, CameraStatus } from "../../types/heatmap";
import { heatmapApi } from "../../services/heatmapApi";
import { useHeatmapStream } from "../../hooks/useHeatmapStream";

const SAMPLE_VIDEO_PATH = "/Users/parthspalav/Downloads/video.mp4";

export const HeatmapPanel: React.FC = () => {
  const [cameras, setCameras] = useState<CameraStatus[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState<string | null>(null);
  const [apiOnline, setApiOnline] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<"overlay" | "raw" | "split">("overlay");
  const [isControlsOpen, setIsControlsOpen] = useState<boolean>(false);

  // Form state
  const [form, setForm] = useState<AddCameraPayload>({
    camera_id: "",
    name: "",
    source: "",
    crowd_moderate_threshold: 3,
    crowd_crowded_threshold: 6,
    crowd_overcrowded_threshold: 12,
  });
  const [busy, setBusy] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  // WebSocket Live Stream Hook
  const live = useHeatmapStream(selectedCameraId);

  // Poll camera list periodically
  const refreshCameras = useCallback(async () => {
    try {
      const list = await heatmapApi.listCameras();
      setCameras(list);
      setApiOnline(true);
      setSelectedCameraId((cur) => cur ?? (list[0]?.camera_id ?? null));
    } catch {
      setApiOnline(false);
    }
  }, []);

  useEffect(() => {
    refreshCameras();
    const interval = setInterval(refreshCameras, 3000);
    return () => clearInterval(interval);
  }, [refreshCameras]);

  // Handle Fill Sample Path
  const handleFillSamplePath = () => {
    setForm((prev) => ({
      ...prev,
      source: SAMPLE_VIDEO_PATH,
      camera_id: prev.camera_id || "cam-video",
      name: prev.name || "Demo Video Stream",
    }));

    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(SAMPLE_VIDEO_PATH).catch(() => {});
    }

    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Handle Add Camera Submit
  const handleAddCamera = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const payload = {
      camera_id: form.camera_id || "cam-video",
      name: form.name || "Demo Video Stream",
      source: form.source || SAMPLE_VIDEO_PATH,
      crowd_moderate_threshold: form.crowd_moderate_threshold || 3,
      crowd_crowded_threshold: form.crowd_crowded_threshold || 6,
      crowd_overcrowded_threshold: form.crowd_overcrowded_threshold || 12,
    };

    setBusy(true);
    setFormError(null);
    try {
      await heatmapApi.addCamera(payload);
      setSelectedCameraId(payload.camera_id);
      setForm({
        camera_id: "",
        name: "",
        source: "",
        crowd_moderate_threshold: 3,
        crowd_crowded_threshold: 6,
        crowd_overcrowded_threshold: 12,
      });
      await refreshCameras();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to add camera");
    } finally {
      setBusy(false);
    }
  };

  // Handle Remove Camera
  const handleRemoveCamera = async (id: string) => {
    try {
      await heatmapApi.removeCamera(id);
      if (selectedCameraId === id) {
        setSelectedCameraId(null);
      }
      await refreshCameras();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to remove camera");
    }
  };

  const currentAnalytics = live.analytics;
  const currentCount = currentAnalytics?.people_count ?? (live.status?.people_count ?? 0);
  const crowdLevel = currentAnalytics?.crowd_level ?? "low";

  const getCrowdBadgeColor = (level: string) => {
    switch (level) {
      case "overcrowded":
        return "bg-rose-950/80 border-rose-500/50 text-rose-400";
      case "crowded":
        return "bg-amber-950/80 border-amber-500/50 text-amber-400";
      case "moderate":
        return "bg-yellow-950/80 border-yellow-500/50 text-yellow-300";
      default:
        return "bg-emerald-950/80 border-emerald-500/50 text-emerald-400";
    }
  };

  const currentOverlaySrc = selectedCameraId
    ? live.image || heatmapApi.mjpegUrl(selectedCameraId, "overlay")
    : undefined;

  const currentRawSrc = selectedCameraId
    ? live.rawImage || heatmapApi.mjpegUrl(selectedCameraId, "raw")
    : undefined;

  return (
    <div className="relative w-full h-full bg-slate-900/90 border border-slate-800/80 rounded-2xl flex flex-col min-h-0 shadow-2xl overflow-hidden group">
      {/* 1. Header Toolbar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800/80 bg-slate-950/80 shrink-0 z-20">
        {/* Left: Feed Info & Status */}
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-cyan-950/80 border border-cyan-500/40 rounded-xl text-cyan-400 shadow-inner">
            <Video className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-sm font-bold text-white tracking-tight">
                Crowd Density & Spatial Heatmap
              </h2>
              {selectedCameraId && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-cyan-300 border border-slate-700">
                  {selectedCameraId}
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-400 font-medium">
              YOLOv11 Medium · ByteTrack · Gaussian Density KDE
            </p>
          </div>
        </div>

        {/* Right: Controls & Viewport Switcher */}
        <div className="flex items-center space-x-2">
          {/* View Mode Buttons */}
          <div className="bg-slate-900 border border-slate-800 p-1 rounded-xl flex items-center space-x-1">
            <button
              type="button"
              onClick={() => setViewMode("overlay")}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                viewMode === "overlay"
                  ? "bg-cyan-600 text-white shadow-md"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Heatmap
            </button>
            <button
              type="button"
              onClick={() => setViewMode("raw")}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                viewMode === "raw"
                  ? "bg-cyan-600 text-white shadow-md"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Raw Feed
            </button>
            <button
              type="button"
              onClick={() => setViewMode("split")}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                viewMode === "split"
                  ? "bg-cyan-600 text-white shadow-md"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Split View
            </button>
          </div>

          {/* Toggle Camera Drawer */}
          <button
            type="button"
            onClick={() => setIsControlsOpen(!isControlsOpen)}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all cursor-pointer ${
              isControlsOpen
                ? "bg-slate-800 border-cyan-500/50 text-cyan-300"
                : "bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700"
            }`}
          >
            <Settings className="w-3.5 h-3.5" />
            <span>Controls</span>
            {isControlsOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>

          {/* Backend Status Pill */}
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-xl bg-slate-900 border border-slate-800 text-xs font-mono">
            <span
              className={`w-2 h-2 rounded-full ${
                apiOnline ? "bg-emerald-400 animate-pulse" : "bg-rose-500"
              }`}
            />
            <span className="text-slate-300">
              {apiOnline ? "ENGINE ONLINE" : "DISCONNECTED"}
            </span>
          </div>
        </div>
      </div>

      {/* 2. Main Viewport Container */}
      <div className="relative flex-1 bg-slate-950 flex flex-col justify-center items-center overflow-hidden min-h-0">
        {/* Subtle Surveillance Canvas Grid */}
        <div
          className="absolute inset-0 opacity-10 pointer-events-none bg-[radial-gradient(#334155_1px,transparent_1px)] [background-size:24px_24px]"
          aria-hidden="true"
        />

        {/* Live Overlay / Feed Rendering */}
        {selectedCameraId ? (
          <div className="relative w-full h-full flex items-center justify-center p-2">
            {viewMode === "split" ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 w-full h-full">
                {/* Left: Raw Camera Feed */}
                <div className="relative bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex items-center justify-center">
                  <div className="absolute top-2 left-2 bg-slate-950/80 px-2 py-0.5 rounded text-[10px] font-mono text-cyan-300 border border-slate-800 z-10">
                    RAW CCTV PREVIEW
                  </div>
                  <img
                    src={currentRawSrc}
                    alt="Raw Camera Feed"
                    className="w-full h-full object-contain"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = "none";
                    }}
                  />
                </div>

                {/* Right: Heatmap Density Overlay */}
                <div className="relative bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex items-center justify-center">
                  <div className="absolute top-2 left-2 bg-slate-950/80 px-2 py-0.5 rounded text-[10px] font-mono text-amber-300 border border-slate-800 z-10">
                    GAUSSIAN DENSITY HEATMAP
                  </div>
                  <img
                    src={currentOverlaySrc}
                    alt="Heatmap Overlay"
                    className="w-full h-full object-contain"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = "none";
                    }}
                  />
                </div>
              </div>
            ) : viewMode === "raw" ? (
              <img
                src={currentRawSrc}
                alt="Raw Feed"
                className="w-full h-full object-contain"
              />
            ) : (
              <img
                src={currentOverlaySrc}
                alt="Heatmap Stream"
                className="w-full h-full object-contain"
              />
            )}

            {/* Floating Live Headcount Overlay Badge */}
            <div className="absolute top-4 left-4 bg-slate-950/85 border border-cyan-500/50 backdrop-blur-md px-3.5 py-1.5 rounded-xl text-xs font-mono text-cyan-300 flex items-center space-x-2.5 shadow-xl z-10">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
              <span className="font-bold">HEADCOUNT: {currentCount} PPL</span>
              <span className="text-slate-500">|</span>
              <span className="uppercase text-white font-semibold">
                {crowdLevel}
              </span>
            </div>
          </div>
        ) : (
          /* Standby / No Camera Selected State */
          <div className="relative z-10 max-w-lg mx-auto p-6 text-center flex flex-col items-center justify-center space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-400 shadow-inner">
              <Eye className="w-8 h-8 text-cyan-400" />
            </div>

            <div>
              <h3 className="text-lg font-bold text-white">YOLO Heatmap Engine Standby</h3>
              <p className="text-xs text-slate-400 mt-1 max-w-sm">
                {!apiOnline
                  ? "Backend service offline. Run `uvicorn app.main:app --reload` on port 8000."
                  : cameras.length === 0
                  ? "No active camera feeds. Click below to start the demo video stream."
                  : "Select a camera stream from the Controls panel."}
              </p>
            </div>

            {/* Quick Start 1-Click Sample Button */}
            {apiOnline && (
              <button
                type="button"
                onClick={async () => {
                  handleFillSamplePath();
                  await handleAddCamera();
                }}
                disabled={busy}
                className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold text-xs rounded-xl shadow-lg border border-cyan-400/40 transition-all active:scale-95 cursor-pointer flex items-center space-x-2 disabled:opacity-50"
              >
                {busy ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Plus className="w-4 h-4" />
                )}
                <span>{busy ? "Starting Demo Stream..." : "Start Demo Video Stream"}</span>
              </button>
            )}
          </div>
        )}

        {/* Corner Reticle Markers */}
        <div className="absolute top-3 left-3 w-4 h-4 border-t-2 border-l-2 border-slate-700 pointer-events-none" />
        <div className="absolute top-3 right-3 w-4 h-4 border-t-2 border-r-2 border-slate-700 pointer-events-none" />
        <div className="absolute bottom-3 left-3 w-4 h-4 border-b-2 border-l-2 border-slate-700 pointer-events-none" />
        <div className="absolute bottom-3 right-3 w-4 h-4 border-b-2 border-r-2 border-slate-700 pointer-events-none" />
      </div>

      {/* 3. Collapsible Camera Controls & Configuration Drawer */}
      {isControlsOpen && (
        <div className="border-t border-slate-800 bg-slate-900/95 p-4 shrink-0 z-30 animate-fadeIn">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-6xl mx-auto">
            {/* Column 1: Camera Selector & Active List */}
            <div className="bg-slate-950 border border-slate-800 rounded-xl p-3 flex flex-col justify-between">
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2 flex items-center justify-between">
                  <span>Active Cameras ({cameras.length})</span>
                  <button
                    type="button"
                    onClick={refreshCameras}
                    className="text-slate-400 hover:text-white transition-colors cursor-pointer"
                  >
                    <RefreshCw className="w-3 h-3" />
                  </button>
                </h4>

                <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                  {cameras.map((c) => (
                    <div
                      key={c.camera_id}
                      onClick={() => setSelectedCameraId(c.camera_id)}
                      className={`px-3 py-2 rounded-lg text-xs flex items-center justify-between cursor-pointer border transition-all ${
                        selectedCameraId === c.camera_id
                          ? "bg-slate-800 border-cyan-500/60 text-white font-semibold shadow"
                          : "bg-slate-900/60 border-slate-800 text-slate-300 hover:border-slate-700"
                      }`}
                    >
                      <div className="flex items-center space-x-2 truncate">
                        <span
                          className={`w-2 h-2 rounded-full ${
                            c.connected ? "bg-emerald-400" : "bg-amber-400"
                          }`}
                        />
                        <span className="truncate">{c.camera_id}</span>
                      </div>

                      <div className="flex items-center space-x-2">
                        <span className="text-[10px] font-mono text-slate-400">
                          {c.people_count} ppl
                        </span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRemoveCamera(c.camera_id);
                          }}
                          className="text-slate-500 hover:text-rose-400 transition-colors p-1"
                          title="Remove Camera"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}

                  {cameras.length === 0 && (
                    <p className="text-xs text-slate-500 italic p-2">No cameras added yet.</p>
                  )}
                </div>
              </div>
            </div>

            {/* Column 2: Add Camera Form */}
            <div className="bg-slate-950 border border-slate-800 rounded-xl p-3 col-span-2">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Register Camera Stream
                </h4>
                <button
                  type="button"
                  onClick={handleFillSamplePath}
                  className="text-[11px] text-cyan-400 hover:text-cyan-300 hover:underline flex items-center space-x-1 font-mono cursor-pointer"
                >
                  <Copy className="w-3 h-3" />
                  <span>{copied ? "Copied & Filled! ✓" : "Fill Sample Path"}</span>
                </button>
              </div>

              <form onSubmit={handleAddCamera} className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <input
                  type="text"
                  placeholder="Camera ID (e.g. cam-video)"
                  value={form.camera_id}
                  onChange={(e) => setForm({ ...form, camera_id: e.target.value })}
                  className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 outline-none focus:border-cyan-500"
                  required
                />
                <input
                  type="text"
                  placeholder="Name (e.g. Demo Stream)"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 outline-none focus:border-cyan-500"
                  required
                />
                <div className="relative flex items-center">
                  <input
                    type="text"
                    placeholder="Source: /path/video.mp4 or 0"
                    value={form.source}
                    onChange={(e) => setForm({ ...form, source: e.target.value })}
                    className="bg-slate-900 border border-slate-800 rounded-lg pl-3 pr-14 py-1.5 text-xs text-white placeholder-slate-500 outline-none focus:border-cyan-500 w-full"
                    required
                  />
                  <button
                    type="button"
                    onClick={handleFillSamplePath}
                    className="absolute right-1 px-1.5 py-0.5 text-[10px] font-bold bg-cyan-950 border border-cyan-500/40 text-cyan-300 rounded hover:bg-cyan-900 transition-colors"
                  >
                    Path
                  </button>
                </div>

                <div className="sm:col-span-3 flex items-center justify-between pt-1">
                  {formError ? (
                    <p className="text-[11px] text-rose-400 font-mono truncate">{formError}</p>
                  ) : (
                    <span className="text-[10px] text-slate-500 font-mono">
                      Target: /Users/parthspalav/Downloads/video.mp4
                    </span>
                  )}

                  <button
                    type="submit"
                    disabled={busy}
                    className="px-4 py-1.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-bold text-xs rounded-lg shadow transition-all cursor-pointer ml-auto flex items-center space-x-1"
                  >
                    {busy && <Loader2 className="w-3 h-3 animate-spin" />}
                    <span>{busy ? "Starting..." : "Add & Start Stream"}</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* 4. Live Telemetry & Analytics Footer Bar */}
      <div className="px-4 py-2.5 border-t border-slate-800/80 bg-slate-950/90 grid grid-cols-2 sm:grid-cols-6 gap-2 shrink-0 text-xs font-mono">
        <div className="bg-slate-900/80 border border-slate-800/80 p-2 rounded-xl">
          <p className="text-[10px] text-slate-400 uppercase">Headcount</p>
          <p className="text-sm font-black text-white">{currentCount} Ppl</p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800/80 p-2 rounded-xl">
          <p className="text-[10px] text-slate-400 uppercase">Density Score</p>
          <p className="text-sm font-black text-cyan-400">
            {currentAnalytics?.density_score ?? "0.00"}
          </p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800/80 p-2 rounded-xl">
          <p className="text-[10px] text-slate-400 uppercase">Peak Density</p>
          <p className="text-sm font-black text-indigo-400">
            {currentAnalytics?.max_density ?? "0.00"}
          </p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800/80 p-2 rounded-xl">
          <p className="text-[10px] text-slate-400 uppercase">Movement Index</p>
          <p className="text-sm font-black text-emerald-400">
            {currentAnalytics?.movement_index ?? "0.00"}
          </p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800/80 p-2 rounded-xl">
          <p className="text-[10px] text-slate-400 uppercase">Pipeline FPS</p>
          <p className="text-sm font-black text-amber-400">
            {live.status?.fps ? `${live.status.fps} FPS` : "--"}
          </p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800/80 p-2 rounded-xl flex flex-col justify-center">
          <p className="text-[10px] text-slate-400 uppercase">Crowd Status</p>
          <span
            className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase border mt-0.5 text-center ${getCrowdBadgeColor(
              crowdLevel
            )}`}
          >
            {crowdLevel}
          </span>
        </div>
      </div>
    </div>
  );
};
