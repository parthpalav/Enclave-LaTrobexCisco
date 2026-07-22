import React, { useState } from 'react';
import { Monitor, Copy, Check, ExternalLink } from 'lucide-react';

export const BillboardPanel: React.FC = () => {
  const [copied, setCopied] = useState<boolean>(false);

  const hostname = typeof window !== 'undefined' && window.location.hostname ? window.location.hostname : 'localhost';
  const port = typeof window !== 'undefined' && window.location.port ? window.location.port : '5173';
  const billboardUrl = `http://${hostname}:${port}/billboard`;

  const handleCopy = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(billboardUrl).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2500);
      });
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-2xl flex flex-col justify-between shadow-lg relative overflow-hidden group">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2 text-slate-300 text-xs font-semibold uppercase tracking-wider">
          <Monitor className="w-4 h-4 text-cyan-400" />
          <span>Digital Billboard</span>
        </div>
        <a
          href={billboardUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-slate-400 hover:text-cyan-400 transition-colors p-1 rounded-md"
          title="Open Billboard in new tab"
        >
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      </div>

      <p className="text-xs text-slate-400 font-medium mb-3">
        Roadside LED Display Client Link:
      </p>

      {/* Selectable URL Input Box */}
      <div className="flex items-center space-x-2 bg-slate-950/80 border border-slate-800 p-2 rounded-xl mb-3">
        <input
          type="text"
          readOnly
          value={billboardUrl}
          onClick={(e) => (e.target as HTMLInputElement).select()}
          className="bg-transparent text-xs font-mono text-cyan-300 w-full outline-none select-all cursor-pointer"
        />
      </div>

      {/* Copy Link Button */}
      <button
        onClick={handleCopy}
        className={`w-full py-2.5 px-3 rounded-xl text-xs font-bold flex items-center justify-center space-x-2 transition-all cursor-pointer ${
          copied
            ? 'bg-emerald-600 text-white shadow-emerald-950/40'
            : 'bg-slate-800 hover:bg-slate-750 text-slate-200 hover:text-white border border-slate-700'
        }`}
        aria-label="Copy digital billboard URL to clipboard"
      >
        {copied ? (
          <>
            <Check className="w-4 h-4 text-emerald-200 animate-bounce" />
            <span>Copied to Clipboard!</span>
          </>
        ) : (
          <>
            <Copy className="w-4 h-4 text-cyan-400" />
            <span>Copy Link</span>
          </>
        )}
      </button>
    </div>
  );
};
