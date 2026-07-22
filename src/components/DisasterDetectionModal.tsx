import React, { useEffect } from 'react';
import { Activity, Waves, X, AlertTriangle } from 'lucide-react';

interface DisasterDetectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onEarthquakeTrigger: () => void;
}

export const DisasterDetectionModal: React.FC<DisasterDetectionModalProps> = ({
  isOpen,
  onClose,
  onEarthquakeTrigger,
}) => {
  // Listen for Escape key press to dismiss modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-slate-950/85 backdrop-blur-md animate-fadeIn cursor-pointer"
      role="dialog"
      aria-modal="true"
      aria-labelledby="disaster-modal-title"
    >
      {/* Modal Container */}
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-slate-900 border border-slate-800 rounded-3xl max-w-2xl w-full p-8 shadow-2xl relative cursor-default overflow-hidden"
      >
        {/* Subtle Top Gradient Line */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-amber-500 via-cyan-500 to-blue-500" />

        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-slate-400 hover:text-white p-2 rounded-xl hover:bg-slate-800 transition-colors cursor-pointer"
          aria-label="Close Disaster Detection Menu"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center space-x-3 mb-6">
          <div className="p-2.5 bg-slate-800/80 border border-slate-700 rounded-2xl text-cyan-400">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <h2 id="disaster-modal-title" className="text-xl font-bold text-white tracking-tight">
              Disaster Detection Engine
            </h2>
            <p className="text-xs text-slate-400 font-medium mt-0.5">
              Select a specialized disaster monitoring module for real-time sensor analytics
            </p>
          </div>
        </div>

        {/* Two Large Horizontal Cards: Earthquake & Flood */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 my-2">
          {/* Left Card: Earthquake */}
          <button
            type="button"
            onClick={onEarthquakeTrigger}
            className="group relative bg-gradient-to-br from-amber-950/90 via-amber-900/60 to-orange-950/90 border border-amber-500/40 hover:border-amber-400/80 rounded-2xl p-6 flex flex-col items-center justify-center text-center shadow-xl shadow-amber-950/30 hover:scale-[1.02] transition-all duration-200 cursor-pointer select-none w-full"
            aria-label="Trigger Earthquake Early Warning Alert"
          >
            <div className="w-16 h-16 rounded-2xl bg-amber-900/60 border border-amber-500/40 flex items-center justify-center text-amber-300 mb-4 group-hover:scale-110 transition-transform duration-200 shadow-inner">
              <Activity className="w-8 h-8 animate-pulse" />
            </div>

            <div className="space-y-1">
              <h3 className="text-2xl font-black text-amber-100 tracking-wide flex items-center justify-center gap-2">
                <span>🌍</span>
                <span>Earthquake</span>
              </h3>
              <p className="text-xs text-amber-200/80 font-medium">
                Seismic Activity & Ground Tremor Analysis
              </p>
            </div>

            <div className="mt-4 px-3 py-1 bg-amber-950/80 border border-amber-500/30 rounded-lg text-[10px] font-mono text-amber-300 uppercase tracking-widest">
              Trigger EEW Module
            </div>
          </button>

          {/* Right Card: Flood */}
          <div
            className="group relative bg-gradient-to-br from-cyan-950/90 via-blue-900/60 to-slate-900/90 border border-cyan-500/40 hover:border-cyan-400/80 rounded-2xl p-6 flex flex-col items-center justify-center text-center shadow-xl shadow-cyan-950/30 hover:scale-[1.02] transition-all duration-200 cursor-pointer select-none"
            aria-label="Flood Disaster Detection (Placeholder)"
          >
            <div className="w-16 h-16 rounded-2xl bg-cyan-900/60 border border-cyan-500/40 flex items-center justify-center text-cyan-300 mb-4 group-hover:scale-110 transition-transform duration-200 shadow-inner">
              <Waves className="w-8 h-8 animate-pulse" />
            </div>

            <div className="space-y-1">
              <h3 className="text-2xl font-black text-cyan-100 tracking-wide flex items-center justify-center gap-2">
                <span>🌊</span>
                <span>Flood</span>
              </h3>
              <p className="text-xs text-cyan-200/80 font-medium">
                Water Surge & Flash Flood Monitoring
              </p>
            </div>

            <div className="mt-4 px-3 py-1 bg-cyan-950/80 border border-cyan-500/30 rounded-lg text-[10px] font-mono text-cyan-300 uppercase tracking-widest">
              Telemetry Module Standby
            </div>
          </div>
        </div>

        {/* Footer Note */}
        <p className="text-center text-[11px] text-slate-500 mt-6">
          Press <kbd className="bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded border border-slate-700 font-mono text-[10px]">Esc</kbd> or click outside to close this menu
        </p>
      </div>
    </div>
  );
};
