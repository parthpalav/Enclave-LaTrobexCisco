import type { Analytics } from "../types";
import StatCard from "./StatCard";

interface Props {
  analytics?: Analytics;
  fps?: number;
}

function densityColor(score: number): string {
  if (score >= 75) return "#ef4444";
  if (score >= 50) return "#f97316";
  if (score >= 25) return "#eab308";
  return "#22c55e";
}

const CROWD_LEVELS: Record<string, { label: string; color: string; bg: string }> = {
  low: { label: "Low", color: "#22c55e", bg: "rgba(34,197,94,0.15)" },
  moderate: { label: "Moderate", color: "#eab308", bg: "rgba(234,179,8,0.15)" },
  crowded: { label: "Crowded", color: "#f97316", bg: "rgba(249,115,22,0.15)" },
  overcrowded: { label: "Overcrowded", color: "#ef4444", bg: "rgba(239,68,68,0.18)" },
};

export default function AnalyticsPanel({ analytics, fps }: Props) {
  const a = analytics;
  const level = CROWD_LEVELS[a?.crowd_level ?? "low"] ?? CROWD_LEVELS.low;
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
      <div
        className="col-span-2 md:col-span-3 card p-4 flex items-center justify-between"
        style={{ backgroundColor: level.bg, borderColor: level.color }}
      >
        <div>
          <span className="text-xs uppercase tracking-wide text-white/50">
            Crowd Status
          </span>
          <div className="text-2xl font-bold" style={{ color: level.color }}>
            {level.label}
          </div>
        </div>
        <div className="text-right">
          <span className="text-xs uppercase tracking-wide text-white/50">People</span>
          <div className="text-2xl font-bold" style={{ color: level.color }}>
            {a?.people_count ?? "—"}
          </div>
        </div>
      </div>
      <StatCard label="People" value={a?.people_count ?? "—"} />
      <StatCard
        label="Density Score"
        value={a ? a.density_score.toFixed(1) : "—"}
        accent={a ? densityColor(a.density_score) : undefined}
      />
      <StatCard label="Max Density" value={a ? a.max_density.toFixed(2) : "—"} />
      <StatCard label="Avg Density" value={a ? a.average_density.toFixed(3) : "—"} />
      <StatCard
        label="Movement"
        value={a ? a.movement_index.toFixed(2) : "—"}
        unit="px/f"
      />
      <StatCard label="FPS" value={fps?.toFixed(1) ?? a?.fps?.toFixed(1) ?? "—"} />
      <div className="col-span-2 md:col-span-3 card p-4">
        <span className="text-xs uppercase tracking-wide text-white/50">
          Crowded Zones
        </span>
        <div className="mt-2 flex flex-wrap gap-2">
          {a && a.crowded_zones.length > 0 ? (
            a.crowded_zones.slice(0, 8).map((z, i) => (
              <span
                key={i}
                className="text-xs px-2 py-1 rounded-md bg-panel2 border border-white/5"
                title={`(${z.x}, ${z.y}) r=${z.radius}`}
              >
                zone {i + 1} · {(z.intensity * 100).toFixed(0)}%
              </span>
            ))
          ) : (
            <span className="text-sm text-white/30">No crowded zones</span>
          )}
        </div>
      </div>
    </div>
  );
}
