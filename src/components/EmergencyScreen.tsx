import React, { useEffect, useRef } from 'react';
import { AlertOctagon, Flame } from 'lucide-react';
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

  const formattedTime = payload?.timestamp
    ? new Date(payload.timestamp).toLocaleTimeString()
    : new Date().toLocaleTimeString();

  return (
    <div className="h-screen w-screen bg-red-950 text-white flex flex-col justify-between p-6 overflow-hidden select-none font-sans border-4 border-red-600 animate-pulse">
      {/* Top Warning Banner */}
      <div className="flex items-center justify-center space-x-3 bg-red-900/90 border border-red-500/60 px-4 py-3 rounded-2xl shadow-2xl">
        <AlertOctagon className="w-8 h-8 text-red-100 animate-bounce" />
        <h1 className="text-2xl font-black tracking-wider text-white uppercase">
          🚨 EMERGENCY ALERT
        </h1>
      </div>

      {/* Center Evacuation Message */}
      <main className="flex-1 flex flex-col items-center justify-center text-center px-4 my-auto space-y-6">
        <div className="w-24 h-24 rounded-full bg-red-900/80 border-2 border-red-400 flex items-center justify-center shadow-2xl shadow-red-900">
          <Flame className="w-14 h-14 text-red-200 animate-ping" />
        </div>

        <div className="space-y-3">
          <h2 className="text-3xl font-black tracking-tight text-red-100 leading-tight">
            Overcrowding Detected
          </h2>
          <p className="text-xl font-bold text-white max-w-sm leading-snug">
            Please evacuate calmly. Proceed to the nearest exit.
          </p>
          <p className="text-base text-red-200 font-medium max-w-xs">
            Follow instructions from emergency personnel.
          </p>
        </div>

        {/* Safety Directives */}
        <div className="bg-red-900/70 border border-red-500/50 p-4 rounded-2xl max-w-xs w-full shadow-inner space-y-1">
          <p className="text-sm font-black text-red-100 uppercase tracking-widest">
            Do not run. Do not push.
          </p>
          <p className="text-xs text-red-200">
            Keep clear of designated emergency corridors.
          </p>
        </div>
      </main>

      {/* Footer Timestamp */}
      <footer className="text-center bg-red-900/50 py-3 rounded-xl border border-red-800">
        <p className="text-xs font-mono text-red-200">
          Time of Broadcast: <span className="font-bold text-white">{formattedTime}</span>
        </p>
      </footer>
    </div>
  );
};
