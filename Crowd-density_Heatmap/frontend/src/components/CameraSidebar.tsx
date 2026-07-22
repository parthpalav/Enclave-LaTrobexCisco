import { useState } from "react";
import type { AddCameraPayload, CameraStatus } from "../types";

interface Props {
  cameras: CameraStatus[];
  selected: string | null;
  onSelect: (id: string) => void;
  onAdd: (payload: AddCameraPayload) => Promise<void>;
  onRemove: (id: string) => Promise<void>;
}

export default function CameraSidebar({
  cameras,
  selected,
  onSelect,
  onAdd,
  onRemove,
}: Props) {
  const [form, setForm] = useState<AddCameraPayload>({
    camera_id: "",
    name: "",
    source: "",
    crowd_moderate_threshold: 5,
    crowd_crowded_threshold: 10,
    crowd_overcrowded_threshold: 20,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onAdd(form);
      setForm({
        camera_id: "",
        name: "",
        source: "",
        crowd_moderate_threshold: form.crowd_moderate_threshold,
        crowd_crowded_threshold: form.crowd_crowded_threshold,
        crowd_overcrowded_threshold: form.crowd_overcrowded_threshold,
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside className="w-full md:w-72 shrink-0 flex flex-col gap-4">
      <div className="card p-4">
        <h2 className="text-sm font-semibold mb-3 text-white/80">Add Camera</h2>
        <form onSubmit={submit} className="flex flex-col gap-2">
          <input
            className="bg-panel2 rounded-md px-3 py-2 text-sm outline-none focus:ring-1 ring-accent"
            placeholder="Camera ID (e.g. cam-01)"
            value={form.camera_id}
            onChange={(e) => setForm({ ...form, camera_id: e.target.value })}
            required
          />
          <input
            className="bg-panel2 rounded-md px-3 py-2 text-sm outline-none focus:ring-1 ring-accent"
            placeholder="Name (e.g. Main Gate)"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
          />
          <input
            className="bg-panel2 rounded-md px-3 py-2 text-sm outline-none focus:ring-1 ring-accent"
            placeholder="Source: rtsp://…  /  video.mp4  /  0"
            value={form.source}
            onChange={(e) => setForm({ ...form, source: e.target.value })}
            required
          />

          <div className="mt-1">
            <span className="text-xs uppercase tracking-wide text-white/50">
              Crowd thresholds (people)
            </span>
            <div className="grid grid-cols-3 gap-2 mt-1">
              {(
                [
                  ["Moderate", "crowd_moderate_threshold", "#eab308"],
                  ["Crowded", "crowd_crowded_threshold", "#f97316"],
                  ["Over", "crowd_overcrowded_threshold", "#ef4444"],
                ] as const
              ).map(([label, key, color]) => (
                <label key={key} className="flex flex-col gap-1">
                  <span className="text-[10px]" style={{ color }}>
                    {label} ≥
                  </span>
                  <input
                    type="number"
                    min={1}
                    className="bg-panel2 rounded-md px-2 py-1.5 text-sm outline-none focus:ring-1 ring-accent w-full"
                    value={form[key] ?? ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        [key]: e.target.value ? Number(e.target.value) : undefined,
                      })
                    }
                  />
                </label>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={busy}
            className="bg-accent hover:bg-blue-500 disabled:opacity-50 rounded-md py-2 text-sm font-medium"
          >
            {busy ? "Starting…" : "Add & Start"}
          </button>
          {error && <p className="text-xs text-red-400">{error}</p>}
        </form>
      </div>

      <div className="card p-4 flex-1">
        <h2 className="text-sm font-semibold mb-3 text-white/80">
          Cameras ({cameras.length})
        </h2>
        <ul className="flex flex-col gap-2">
          {cameras.map((c) => (
            <li
              key={c.camera_id}
              className={`rounded-md px-3 py-2 cursor-pointer border ${
                selected === c.camera_id
                  ? "border-accent bg-panel2"
                  : "border-white/5 hover:bg-panel2"
              }`}
              onClick={() => onSelect(c.camera_id)}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm">{c.camera_id}</span>
                <span
                  className={`h-2 w-2 rounded-full ${
                    c.connected ? "bg-green-400" : "bg-yellow-500"
                  }`}
                />
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs text-white/40">
                  {c.people_count} people · {c.fps} fps
                </span>
                <button
                  className="text-xs text-red-400 hover:underline"
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemove(c.camera_id);
                  }}
                >
                  remove
                </button>
              </div>
            </li>
          ))}
          {cameras.length === 0 && (
            <li className="text-sm text-white/30">No cameras yet.</li>
          )}
        </ul>
      </div>
    </aside>
  );
}
