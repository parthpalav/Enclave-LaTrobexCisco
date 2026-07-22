import React from 'react';
import { Video, Sparkles, Eye } from 'lucide-react';

export const HeatmapPlaceholder: React.FC = () => {
  return (
    <div className="relative w-full h-full bg-slate-900/90 border border-slate-800/80 rounded-2xl flex flex-col items-center justify-center p-6 text-center shadow-2xl overflow-hidden group">
      {/* Subtle grid pattern background to simulate surveillance canvas */}
      <div 
        className="absolute inset-0 opacity-15 pointer-events-none bg-[radial-gradient(#334155_1px,transparent_1px)] [background-size:24px_24px]"
        aria-hidden="true"
      />

      {/* Top Left Feed Label Badge */}
      <div className="absolute top-4 left-4 flex items-center space-x-2 bg-slate-950/80 border border-slate-800 backdrop-blur-md px-3 py-1.5 rounded-lg text-xs font-mono text-slate-300 shadow-md">
        <Video className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
        <span>CAM-01 • VENUE MAIN FLOOR</span>
      </div>

      {/* Top Right Live Vision Indicator */}
      <div className="absolute top-4 right-4 flex items-center space-x-2 bg-slate-950/80 border border-slate-800 backdrop-blur-md px-3 py-1.5 rounded-lg text-xs font-mono text-slate-400 shadow-md">
        <Eye className="w-3.5 h-3.5 text-amber-400" />
        <span>YOLO DETECTOR: STANDBY</span>
      </div>

      {/* Center Content Box */}
      <div className="relative z-10 max-w-lg mx-auto flex flex-col items-center justify-center space-y-3.5">
        <div className="w-20 h-20 rounded-2xl bg-slate-800/80 border border-slate-700/60 flex items-center justify-center text-slate-400 shadow-inner group-hover:scale-105 transition-transform duration-300">
          <Sparkles className="w-10 h-10 text-cyan-400/80" />
        </div>

        <div className="space-y-1">
          <h2 className="text-2xl font-bold text-slate-100 tracking-tight">
            Crowd Density Heatmap
          </h2>
          <p className="text-slate-400 font-medium text-sm">
            (Placeholder)
          </p>
        </div>

        <div className="bg-slate-950/70 border border-slate-800 px-4 py-2 rounded-xl text-xs font-mono text-slate-400 max-w-md shadow-sm">
          <span className="text-cyan-400 font-semibold">Future:</span> YOLO-generated density visualization
        </div>
      </div>

      {/* Corner Reticle Markers */}
      <div className="absolute top-3 left-3 w-4 h-4 border-t-2 border-l-2 border-slate-700 pointer-events-none" />
      <div className="absolute top-3 right-3 w-4 h-4 border-t-2 border-r-2 border-slate-700 pointer-events-none" />
      <div className="absolute bottom-3 left-3 w-4 h-4 border-b-2 border-l-2 border-slate-700 pointer-events-none" />
      <div className="absolute bottom-3 right-3 w-4 h-4 border-b-2 border-r-2 border-slate-700 pointer-events-none" />
    </div>
  );
};
