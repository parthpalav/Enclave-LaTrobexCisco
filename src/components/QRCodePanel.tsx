import React from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { QrCode, ExternalLink } from 'lucide-react';

export const QRCodePanel: React.FC = () => {
  const hostname = typeof window !== 'undefined' && window.location.hostname ? window.location.hostname : 'localhost';
  const port = typeof window !== 'undefined' && window.location.port ? window.location.port : '5173';
  const displayUrl = `http://${hostname}:${port}/display`;

  return (
    <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-2xl flex flex-col items-center justify-center text-center shadow-lg relative overflow-hidden group">
      <div className="flex items-center space-x-2 text-slate-300 text-xs font-semibold uppercase tracking-wider mb-3">
        <QrCode className="w-4 h-4 text-cyan-400" />
        <span>Join Event</span>
      </div>

      <div className="bg-white p-3 rounded-xl shadow-md border border-slate-700/50 flex items-center justify-center group-hover:scale-105 transition-transform duration-200">
        <QRCodeSVG
          value={displayUrl}
          size={120}
          bgColor="#FFFFFF"
          fgColor="#0F172A"
          level="M"
          includeMargin={false}
        />
      </div>

      <p className="mt-3 text-xs font-bold text-slate-200 tracking-wide">
        Scan to Join
      </p>

      <a
        href={displayUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-1 text-[11px] font-mono text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors"
      >
        <span>{displayUrl}</span>
        <ExternalLink className="w-3 h-3" />
      </a>
    </div>
  );
};
