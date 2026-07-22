interface Props {
  label: string;
  value: string | number;
  unit?: string;
  accent?: string;
}

export default function StatCard({ label, value, unit, accent = "#3b82f6" }: Props) {
  return (
    <div className="card p-4 flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-white/50">{label}</span>
      <div className="flex items-baseline gap-1">
        <span className="text-2xl font-semibold" style={{ color: accent }}>
          {value}
        </span>
        {unit && <span className="text-sm text-white/40">{unit}</span>}
      </div>
    </div>
  );
}
