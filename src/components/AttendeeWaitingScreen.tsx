import React from 'react';
import { ShieldCheck, Radio } from 'lucide-react';
import type { CrowdStatus } from '../hooks/useSocket';

interface AttendeeWaitingScreenProps {
  isConnected: boolean;
  crowdCount: number;
  crowdStatus: CrowdStatus;
}

export const AttendeeWaitingScreen: React.FC<AttendeeWaitingScreenProps> = ({
  isConnected,
  crowdCount,
  crowdStatus,
}) => {
  const getStatusBadge = (status: CrowdStatus) => {
    switch (status) {
      case 'SAFE':
        return {
          label: 'SAFE',
          bg: 'bg-emerald-950/80 border-emerald-500/40 text-emerald-400',
          dot: 'bg-emerald-500',
        };
      case 'WARNING':
        return {
          label: 'WARNING',
          bg: 'bg-amber-950/80 border-amber-500/40 text-amber-400',
          dot: 'bg-amber-500',
        };
      case 'DANGER':
        return {
          label: 'DANGER',
          bg: 'bg-rose-950/80 border-rose-500/40 text-rose-400',
          dot: 'bg-rose-500 animate-pulse',
        };
      default:
        return {
          label: 'SAFE',
          bg: 'bg-emerald-950/80 border-emerald-500/40 text-emerald-400',
          dot: 'bg-emerald-500',
        };
    }
  };

  const statusStyle = getStatusBadge(crowdStatus);

  return (
    <div className="h-screen w-screen bg-slate-950 text-slate-100 flex flex-col justify-between p-6 overflow-hidden select-none font-sans">
      {/* Top Header & Connection Status */}
      <header className="flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 bg-slate-900 border border-slate-800 rounded-xl text-cyan-400">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <span className="text-lg font-bold tracking-tight text-white">CrowdShield</span>
        </div>

        {/* Connection Indicator */}
        <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-full border text-xs font-semibold ${
          isConnected
            ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-400'
            : 'bg-rose-950/60 border-rose-500/40 text-rose-400'
        }`}>
          <span className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-emerald-500 animate-ping' : 'bg-rose-500'}`} />
          <span>{isConnected ? '🟢 Connected' : '🔴 Disconnected'}</span>
        </div>
      </header>

      {/* Main Center Message */}
      <main className="flex-1 flex flex-col items-center justify-center text-center px-4 my-auto">
        <div className="w-24 h-24 rounded-3xl bg-slate-900/90 border border-slate-800 flex items-center justify-center mb-6 shadow-2xl">
          <Radio className={`w-12 h-12 ${isConnected ? 'text-emerald-400 animate-pulse' : 'text-slate-600'}`} />
        </div>

        <h1 className="text-3xl font-extrabold text-white tracking-tight mb-2">
          You are currently safe.
        </h1>
        <p className="text-base text-slate-400 max-w-xs font-medium">
          {isConnected ? 'Waiting for emergency instructions...' : 'Attempting to reconnect...'}
        </p>
      </main>

      {/* Bottom Telemetry Cards */}
      <footer className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          {/* Current Crowd Status */}
          <div className={`p-4 rounded-2xl border flex flex-col items-center justify-center text-center shadow-lg ${statusStyle.bg}`}>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
              Current Crowd Status
            </span>
            <span className="text-xl font-black tracking-wide flex items-center gap-2">
              <span className={`w-2.5 h-2.5 rounded-full ${statusStyle.dot}`} />
              {statusStyle.label}
            </span>
          </div>

          {/* Current Crowd Count */}
          <div className="p-4 rounded-2xl border border-slate-800 bg-slate-900/80 flex flex-col items-center justify-center text-center shadow-lg">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
              Current Crowd Count
            </span>
            <span className="text-2xl font-black text-white font-mono">
              {crowdCount}
            </span>
          </div>
        </div>

        <p className="text-center text-[11px] text-slate-500">
          CrowdShield Attendee Safety Node • Live Event Stream
        </p>
      </footer>
    </div>
  );
};
