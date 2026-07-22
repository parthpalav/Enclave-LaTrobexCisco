import React from 'react';
import { ShieldAlert, Server, Radar } from 'lucide-react';

interface HeaderProps {
  isConnected: boolean;
  onDisasterDetectionClick?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ isConnected, onDisasterDetectionClick }) => {
  const hostname = typeof window !== 'undefined' && window.location.hostname ? window.location.hostname : 'localhost';

  return (
    <header className="bg-slate-900/90 backdrop-blur-md border-b border-slate-800 px-6 py-3.5 flex items-center justify-between shadow-lg shrink-0">
      <div className="flex items-center space-x-3.5">
        <div className="p-2 bg-gradient-to-br from-rose-500/20 to-red-600/20 border border-rose-500/30 rounded-xl flex items-center justify-center text-rose-500 shadow-inner">
          <ShieldAlert className="w-6 h-6 animate-pulse" />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            CrowdShield Admin Dashboard
          </h1>
          <p className="text-xs text-slate-400 font-medium">
            Event Monitoring & Emergency Dispatch Center
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {/* Disaster Detection Trigger Button */}
        {onDisasterDetectionClick && (
          <button
            onClick={onDisasterDetectionClick}
            className="flex items-center space-x-2 bg-gradient-to-r from-amber-600/20 via-orange-600/20 to-cyan-600/20 hover:from-amber-600/30 hover:to-cyan-600/30 text-amber-200 hover:text-white border border-amber-500/40 px-3.5 py-1.5 rounded-xl text-xs font-semibold shadow-sm transition-all duration-200 cursor-pointer active:scale-95"
            aria-label="Open Disaster Detection Menu"
          >
            <Radar className="w-4 h-4 text-amber-400 animate-pulse" />
            <span>Disaster Detection</span>
          </button>
        )}

        <div className="hidden sm:flex items-center space-x-2 bg-slate-850 border border-slate-800 px-3 py-1.5 rounded-lg text-xs font-mono text-slate-300">
          <Server className="w-3.5 h-3.5 text-slate-400" />
          <span>Local Node: {hostname}:5001</span>
        </div>

        <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-full border text-xs font-semibold ${
          isConnected 
            ? 'bg-emerald-950/60 border-emerald-500/30 text-emerald-400' 
            : 'bg-rose-950/60 border-rose-500/30 text-rose-400'
        }`}>
          <span className={`w-2 h-2 rounded-full ${
            isConnected ? 'bg-emerald-500 animate-ping' : 'bg-rose-500'
          }`} />
          <span>{isConnected ? 'LIVE' : 'OFFLINE'}</span>
        </div>
      </div>
    </header>
  );
};
