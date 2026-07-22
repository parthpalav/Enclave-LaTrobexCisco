interface Props {
  image?: string;
  connected: boolean;
  title: string;
}

/** Displays a live image (heatmap overlay or raw preview) with a status dot. */
export default function HeatmapView({ image, connected, title }: Props) {
  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/5">
        <span className="text-sm font-medium text-white/80">{title}</span>
        <span className="flex items-center gap-2 text-xs text-white/50">
          <span
            className={`inline-block h-2 w-2 rounded-full ${
              connected ? "bg-green-400" : "bg-red-500"
            }`}
          />
          {connected ? "Live" : "Offline"}
        </span>
      </div>
      <div className="aspect-video bg-black flex items-center justify-center">
        {image ? (
          <img src={image} alt={title} className="w-full h-full object-contain" />
        ) : (
          <span className="text-white/30 text-sm">Waiting for stream…</span>
        )}
      </div>
    </div>
  );
}
