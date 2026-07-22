import React from 'react';
import { Server, Smartphone, Users, Shield, Maximize2 } from 'lucide-react';
import type { CrowdStatus } from '../hooks/useSocket';

interface StatusPanelProps {
  isConnected: boolean;
  connectedDevices: number;
  crowdCount: number;
  venueCapacity: number;
  crowdStatus: CrowdStatus;
}

export const StatusPanel: React.FC<StatusPanelProps> = ({
  isConnected,
  connectedDevices,
  crowdCount,
  venueCapacity,
  crowdStatus,
}) => {
  const getCrowdStatusBadge = (status: CrowdStatus) => {
    switch (status) {
      case 'SAFE':
        return {
          label: 'SAFE',
          bgColor: 'bg-emerald-950/80',
          borderColor: 'border-emerald-500/40',
          textColor: 'text-emerald-400',
          dotColor: 'bg-emerald-500',
          glow: 'shadow-emerald-900/30',
        };
      case 'WARNING':
        return {
          label: 'WARNING',
          bgColor: 'bg-amber-950/80',
          borderColor: 'border-amber-500/40',
          textColor: 'text-amber-400',
          dotColor: 'bg-amber-500',
          glow: 'shadow-amber-900/30',
        };
      case 'DANGER':
        return {
          label: 'DANGER',
          bgColor: 'bg-rose-950/80',
          borderColor: 'border-rose-500/40',
          textColor: 'text-rose-400',
          dotColor: 'bg-rose-500 animate-pulse',
          glow: 'shadow-rose-900/40',
        };
      default:
        return {
          label: 'UNKNOWN',
          bgColor: 'bg-slate-800',
          borderColor: 'border-slate-700',
          textColor: 'text-slate-400',
          dotColor: 'bg-slate-500',
          glow: '',
        };
    }
  };

  const statusStyle = getCrowdStatusBadge(crowdStatus);
  const occupancyPercentage = Math.min(100, Math.round((crowdCount / venueCapacity) * 100));

  return (
    <footer className="bg-slate-900/90 border-t border-slate-800 px-6 py-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 shrink-0 shadow-lg">
      {/* 1. Server Status */}
      <div className="bg-slate-950/70 border border-slate-800/80 p-3.5 rounded-xl flex items-center justify-between shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-slate-850 rounded-lg text-slate-400 border border-slate-800">
            <Server className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Server Status</p>
            <p className="text-sm font-bold text-white flex items-center gap-2 mt-0.5">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'
                }`}
              />
              {isConnected ? 'Server Connected' : 'Server Offline'}
            </p>
          </div>
        </div>
      </div>

      {/* 2. Connected Devices */}
      <div className="bg-slate-950/70 border border-slate-800/80 p-3.5 rounded-xl flex items-center justify-between shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-slate-850 rounded-lg text-slate-400 border border-slate-800">
            <Smartphone className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Connected Devices</p>
            <p className="text-lg font-extrabold text-slate-100 mt-0.5">
              {connectedDevices}
            </p>
          </div>
        </div>
      </div>

      {/* 3. Current Crowd Count */}
      <div className="bg-slate-950/70 border border-slate-800/80 p-3.5 rounded-xl flex items-center justify-between shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-slate-850 rounded-lg text-slate-400 border border-slate-800">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Current Crowd Count</p>
            <p className="text-lg font-extrabold text-slate-100 mt-0.5">
              {crowdCount}
            </p>
          </div>
        </div>
        <div className="text-right">
          <span className="text-xs font-mono text-slate-400">{occupancyPercentage}%</span>
        </div>
      </div>

      {/* 4. Venue Capacity */}
      <div className="bg-slate-950/70 border border-slate-800/80 p-3.5 rounded-xl flex items-center justify-between shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-slate-850 rounded-lg text-slate-400 border border-slate-800">
            <Maximize2 className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Venue Capacity</p>
            <p className="text-lg font-extrabold text-slate-100 mt-0.5">
              {venueCapacity}
            </p>
          </div>
        </div>
      </div>

      {/* 5. Crowd Status */}
      <div className={`border p-3.5 rounded-xl flex items-center justify-between shadow-md ${statusStyle.bgColor} ${statusStyle.borderColor} ${statusStyle.glow}`}>
        <div className="flex items-center space-x-3">
          <div className={`p-2 rounded-lg border border-current ${statusStyle.textColor}`}>
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Crowd Status</p>
            <p className={`text-base font-black tracking-wider flex items-center gap-2 mt-0.5 ${statusStyle.textColor}`}>
              <span className={`w-2.5 h-2.5 rounded-full ${statusStyle.dotColor}`} />
              {statusStyle.label}
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
};
