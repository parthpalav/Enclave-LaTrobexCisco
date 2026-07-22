import React from 'react';
import { AlertTriangle, Phone, MessageSquare, Info, CheckCircle2, Footprints } from 'lucide-react';

interface ControlButtonsProps {
  onRaiseSOSClick: () => void;
  onClearSOSClick: () => void;
  isEmergencyActive: boolean;
}

export const ControlButtons: React.FC<ControlButtonsProps> = ({
  onRaiseSOSClick,
  onClearSOSClick,
  isEmergencyActive,
}) => {
  return (
    <div className="bg-slate-900/60 border-b border-slate-800/80 px-6 py-4 flex items-center justify-between gap-4 shrink-0 shadow-sm">
      <div className="flex items-center space-x-4 w-full md:w-auto flex-wrap gap-y-2">
        {/* Raise SOS Button (Only Functional Emergency Trigger Button) */}
        <button
          onClick={onRaiseSOSClick}
          className="group relative flex-1 md:flex-initial inline-flex items-center justify-center space-x-2.5 px-6 py-3.5 bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-bold text-base rounded-xl shadow-lg shadow-red-950/50 hover:shadow-red-600/30 border border-red-500/50 transition-all duration-200 active:scale-[0.98] cursor-pointer"
          aria-label="Raise SOS Emergency Alert"
        >
          <AlertTriangle className="w-5 h-5 group-hover:scale-110 transition-transform text-red-100" />
          <span>Raise SOS</span>
        </button>

        {/* Clear SOS Alert Button (Active when emergency broadcast is live) */}
        {isEmergencyActive && (
          <button
            onClick={onClearSOSClick}
            className="flex-1 md:flex-initial inline-flex items-center justify-center space-x-2 px-5 py-3.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm rounded-xl shadow-lg shadow-emerald-950/40 border border-emerald-400/50 transition-all active:scale-[0.98] cursor-pointer animate-pulse"
            aria-label="Clear Emergency Alert"
          >
            <CheckCircle2 className="w-5 h-5" />
            <span>Clear Alert</span>
          </button>
        )}

        {/* Make Call (Disabled with Tooltip) */}
        <div className="relative group flex-1 md:flex-initial">
          <button
            disabled
            className="w-full inline-flex items-center justify-center space-x-2.5 px-6 py-3.5 bg-slate-800/50 text-slate-500 font-semibold text-base rounded-xl border border-slate-800 cursor-not-allowed opacity-60 transition-colors"
            aria-label="Make Call (Disabled)"
          >
            <Phone className="w-5 h-5 text-slate-500" />
            <span>Make Call</span>
          </button>

          {/* Hover Tooltip */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 hidden group-hover:flex flex-col items-center z-30 pointer-events-none w-64">
            <div className="w-2.5 h-2.5 bg-slate-800 rotate-45 border-t border-l border-slate-700 -mb-1.5" />
            <div className="bg-slate-800 text-slate-300 text-xs py-2 px-3 rounded-lg border border-slate-700 shadow-xl flex items-start gap-2">
              <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
              <span>
                <strong>Future Integration:</strong> Automated emergency call using Twilio.
              </span>
            </div>
          </div>
        </div>

        {/* Send SMS (Disabled with Tooltip) */}
        <div className="relative group flex-1 md:flex-initial">
          <button
            disabled
            className="w-full inline-flex items-center justify-center space-x-2.5 px-6 py-3.5 bg-slate-800/50 text-slate-500 font-semibold text-base rounded-xl border border-slate-800 cursor-not-allowed opacity-60 transition-colors"
            aria-label="Send SMS (Disabled)"
          >
            <MessageSquare className="w-5 h-5 text-slate-500" />
            <span>Send SMS</span>
          </button>

          {/* Hover Tooltip */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 hidden group-hover:flex flex-col items-center z-30 pointer-events-none w-64">
            <div className="w-2.5 h-2.5 bg-slate-800 rotate-45 border-t border-l border-slate-700 -mb-1.5" />
            <div className="bg-slate-800 text-slate-300 text-xs py-2 px-3 rounded-lg border border-slate-700 shadow-xl flex items-start gap-2">
              <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
              <span>
                <strong>Future Integration:</strong> Bulk SMS broadcasting using Twilio.
              </span>
            </div>
          </div>
        </div>

        {/* Public Movement (UI Placeholder Button) */}
        <div className="relative group flex-1 md:flex-initial">
          <button
            disabled
            className="w-full inline-flex items-center justify-center space-x-2.5 px-6 py-3.5 bg-slate-800/50 text-slate-500 font-semibold text-base rounded-xl border border-slate-800 cursor-not-allowed opacity-60 transition-colors"
            aria-label="Public Movement (UI Placeholder)"
          >
            <Footprints className="w-5 h-5 text-slate-500" />
            <span>Public Movement</span>
          </button>

          {/* Hover Tooltip */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 hidden group-hover:flex flex-col items-center z-30 pointer-events-none w-64">
            <div className="w-2.5 h-2.5 bg-slate-800 rotate-45 border-t border-l border-slate-700 -mb-1.5" />
            <div className="bg-slate-800 text-slate-300 text-xs py-2 px-3 rounded-lg border border-slate-700 shadow-xl flex items-start gap-2">
              <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
              <span>
                <strong>Future Integration:</strong> Real-time crowd movement analytics & crowd flow modeling.
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="hidden lg:flex items-center space-x-2 text-xs text-slate-400 bg-slate-950/60 px-3 py-2 rounded-lg border border-slate-800/60">
        <span className="w-2 h-2 rounded-full bg-red-500 animate-ping"></span>
        <span>Emergency Broadcast Engine Ready</span>
      </div>
    </div>
  );
};
