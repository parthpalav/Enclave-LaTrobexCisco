import React, { useEffect, useRef } from 'react';
import { AlertOctagon, Flame, Navigation, Cross } from 'lucide-react';
import type { EmergencyPayload } from '../hooks/useSocket';

interface EmergencyScreenProps {
  payload: EmergencyPayload | null;
}

export const EmergencyScreen: React.FC<EmergencyScreenProps> = ({ payload }) => {
  const audioCtxRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    // 1. Device Vibration
    if (typeof window !== 'undefined' && 'vibrate' in navigator) {
      try {
        navigator.vibrate([300, 100, 300, 100, 600]);
      } catch {
        // Fail gracefully if blocked by device permissions
      }
    }

    // 2. Web Audio Alarm Sound Synthesizer (Works without external assets)
    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (AudioCtx) {
        const ctx = new AudioCtx();
        audioCtxRef.current = ctx;

        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(880, ctx.currentTime); // A5 note
        osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.5);

        gain.gain.setValueAtTime(0.3, ctx.currentTime);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start();
        osc.stop(ctx.currentTime + 1.2);
      }
    } catch {
      // Fail gracefully if autoplay is restricted by browser policy
    }

    return () => {
      if (audioCtxRef.current) {
        audioCtxRef.current.close().catch(() => {});
      }
    };
  }, []);

  const handleOpenMap = () => {
    const mapsUrl = 'https://www.google.com/maps/dir/?api=1&destination=28.641889,77.230694';
    window.open(mapsUrl, '_blank', 'noopener,noreferrer');
  };

  const handleOpenHospital = () => {
    const hospitalUrl = 'https://www.google.com/search?q=hospital+near+me&oq=hospital+near+me';
    window.open(hospitalUrl, '_blank', 'noopener,noreferrer');
  };

  const formattedTime = payload?.timestamp
    ? new Date(payload.timestamp).toLocaleTimeString()
    : new Date().toLocaleTimeString();

  return (
    <div className="h-screen w-screen bg-red-950 text-white flex flex-col justify-between p-5 overflow-y-auto select-none font-sans border-4 border-red-600 animate-pulse">
      {/* Top Warning Banner */}
      <div className="flex items-center justify-center space-x-3 bg-red-900/90 border border-red-500/60 px-4 py-3 rounded-2xl shadow-2xl shrink-0">
        <AlertOctagon className="w-7 h-7 text-red-100 animate-bounce shrink-0" />
        <h1 className="text-xl font-black tracking-wider text-white uppercase">
          🚨 EMERGENCY ALERT
        </h1>
      </div>

      {/* Center Evacuation Message */}
      <main className="flex-1 flex flex-col items-center justify-center text-center px-3 my-auto py-4 space-y-4">
        <div className="w-16 h-16 rounded-full bg-red-900/80 border-2 border-red-400 flex items-center justify-center shadow-2xl shadow-red-900 shrink-0">
          <Flame className="w-9 h-9 text-red-200 animate-ping" />
        </div>

        <div className="space-y-1.5">
          <h2 className="text-2xl font-black tracking-tight text-red-100 leading-tight">
            Overcrowding Detected
          </h2>
          <p className="text-base font-bold text-white max-w-sm leading-snug">
            Please evacuate calmly. Proceed to the nearest exit.
          </p>
          <p className="text-xs text-red-200 font-medium max-w-xs">
            Follow instructions from emergency personnel.
          </p>
        </div>

        {/* Safety Directives */}
        <div className="bg-red-900/70 border border-red-500/50 p-2.5 rounded-2xl max-w-xs w-full shadow-inner space-y-0.5">
          <p className="text-xs font-black text-red-100 uppercase tracking-widest">
            Do not run. Do not push.
          </p>
          <p className="text-[11px] text-red-200">
            Keep clear of designated emergency corridors.
          </p>
        </div>

        {/* Divider */}
        <div className="w-full max-w-xs border-t border-red-500/40 my-1" />

        {/* Evacuation & Medical Navigation Actions */}
        <div className="w-full max-w-xs flex flex-col items-center space-y-2.5">
          <div className="flex items-center space-x-1.5 text-white">
            <Navigation className="w-4 h-4 text-white" />
            <h3 className="text-sm font-bold tracking-wide">Safe Evacuation & Medical Help</h3>
          </div>

          {/* Open Safe Evacuation Route Button */}
          <button
            onClick={handleOpenMap}
            className="w-full py-3 px-4 bg-white hover:bg-slate-100 text-slate-900 font-extrabold text-sm rounded-2xl shadow-2xl border border-red-200 transition-all duration-150 active:scale-[0.98] cursor-pointer flex items-center justify-center space-x-2"
            aria-label="Open Google Maps navigation to the safe evacuation point"
          >
            <span>🗺️</span>
            <span>Open Safe Route in Google Maps</span>
          </button>

          {/* Find Medical Help Button */}
          <button
            onClick={handleOpenHospital}
            className="w-full py-3 px-4 bg-white hover:bg-slate-100 text-slate-900 font-extrabold text-sm rounded-2xl shadow-2xl border border-red-200 transition-all duration-150 active:scale-[0.98] cursor-pointer flex items-center justify-center space-x-2"
            aria-label="Search for nearby hospitals and medical assistance"
          >
            <Cross className="w-4 h-4 text-red-600 fill-red-600 shrink-0" />
            <span>Find Medical Help</span>
          </button>
        </div>
      </main>

      {/* Footer Timestamp */}
      <footer className="text-center bg-red-900/50 py-2 rounded-xl border border-red-800 shrink-0">
        <p className="text-xs font-mono text-red-200">
          Time of Broadcast: <span className="font-bold text-white">{formattedTime}</span>
        </p>
      </footer>
    </div>
  );
};
