import React from 'react';
import { Smartphone, Wifi } from 'lucide-react';
import type { DeviceInfo } from '../hooks/useSocket';

interface ConnectedDevicesPanelProps {
  devicesList: DeviceInfo[];
  connectedDevices: number;
}

export const ConnectedDevicesPanel: React.FC<ConnectedDevicesPanelProps> = ({
  devicesList,
  connectedDevices,
}) => {
  // If list is empty but connectedDevices > 0, generate fallback placeholder badges for demo visual
  const activeItems = devicesList.length > 0
    ? devicesList
    : Array.from({ length: connectedDevices }, (_, idx) => ({
        id: `mock-${idx + 1}`,
        name: `Device ${idx + 1}`,
        connectedAt: 'Active',
      }));

  return (
    <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-2xl flex flex-col justify-between shadow-lg">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2 text-slate-300 text-xs font-semibold uppercase tracking-wider">
          <Smartphone className="w-4 h-4 text-emerald-400" />
          <span>Connected Users ({connectedDevices})</span>
        </div>
        <div className="flex items-center space-x-1.5 text-[11px] text-emerald-400 font-mono">
          <Wifi className="w-3.5 h-3.5 animate-pulse" />
          <span>Wi-Fi Mesh Active</span>
        </div>
      </div>

      {activeItems.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-6 text-slate-500 text-xs italic">
          No attendee devices connected yet.
          <span className="text-[10px] text-slate-600 not-italic mt-1">Scan the QR code to connect mobile clients</span>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto pr-1">
          {activeItems.map((device) => (
            <div
              key={device.id}
              className="flex items-center space-x-2 px-3 py-1.5 bg-slate-800/80 border border-slate-700/60 rounded-xl text-xs font-medium text-slate-200 shadow-sm animate-fadeIn"
            >
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
              <span className="font-semibold">{device.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
