import React from 'react';
import { AlertOctagon, X } from 'lucide-react';

interface ConfirmationModalProps {
  isOpen: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  isOpen,
  onCancel,
  onConfirm,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
      <div 
        className="bg-slate-900 border border-red-500/40 rounded-2xl max-w-md w-full p-6 shadow-2xl shadow-red-950/50 relative overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="sos-modal-title"
      >
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-red-600 via-rose-500 to-red-600" />

        <button
          onClick={onCancel}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 transition-colors p-1 rounded-lg hover:bg-slate-800"
          aria-label="Close dialog"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex flex-col items-center text-center space-y-4 pt-2">
          <div className="w-14 h-14 rounded-full bg-red-950/80 border border-red-500/30 flex items-center justify-center text-red-500 shadow-inner">
            <AlertOctagon className="w-8 h-8 animate-bounce" />
          </div>

          <div className="space-y-2">
            <h3 id="sos-modal-title" className="text-xl font-bold text-white">
              Confirm Emergency Broadcast
            </h3>
            <p className="text-sm text-slate-300 font-medium px-2">
              Are you sure you want to broadcast an emergency alert?
            </p>
          </div>

          <div className="bg-red-950/40 border border-red-900/50 p-3 rounded-xl text-xs text-red-300 text-left w-full">
            <strong>Warning:</strong> This action will send an immediate SOS event (<code className="bg-red-900/60 px-1 py-0.5 rounded font-mono">raise-sos</code>) to all connected attendee devices across the network.
          </div>
        </div>

        <div className="mt-6 flex items-center space-x-3">
          <button
            onClick={onCancel}
            className="flex-1 py-3 px-4 bg-slate-800 hover:bg-slate-750 text-slate-300 hover:text-white font-semibold text-sm rounded-xl border border-slate-700 transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 py-3 px-4 bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-bold text-sm rounded-xl shadow-lg shadow-red-950/60 border border-red-500/50 transition-all cursor-pointer"
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
};
