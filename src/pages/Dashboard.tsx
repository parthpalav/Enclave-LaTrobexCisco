import React, { useState, useCallback, useEffect } from 'react';
import { useSocket } from '../hooks/useSocket';
import { Header } from '../components/Header';
import { ControlButtons } from '../components/ControlButtons';
import { HeatmapPlaceholder } from '../components/HeatmapPlaceholder';
import { StatusPanel } from '../components/StatusPanel';
import { ConfirmationModal } from '../components/ConfirmationModal';
import { DisasterDetectionModal } from '../components/DisasterDetectionModal';
import { Toast } from '../components/Toast';
import type { ToastMessage } from '../components/Toast';
import { QRCodePanel } from '../components/QRCodePanel';
import { BillboardPanel } from '../components/BillboardPanel';
import { ConnectedDevicesPanel } from '../components/ConnectedDevicesPanel';
import { speakEmergency, stopEmergencySpeech } from '../utils/speech';

export const Dashboard: React.FC = () => {
  const {
    isConnected,
    connectedDevices,
    devicesList,
    crowdCount,
    venueCapacity,
    crowdStatus,
    isEmergency,
    raiseSOS,
    raiseEarthquake,
    clearSOS,
  } = useSocket();

  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [isDisasterMenuOpen, setIsDisasterMenuOpen] = useState<boolean>(false);
  const [isEEWOverlayOpen, setIsEEWOverlayOpen] = useState<boolean>(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  // Handle Emergency Voice Announcement on Admin Panel ONLY
  useEffect(() => {
    if (isEmergency) {
      speakEmergency();
    } else {
      stopEmergencySpeech();
    }

    return () => {
      stopEmergencySpeech();
    };
  }, [isEmergency]);

  // Toast Helper
  const addToast = useCallback((type: 'success' | 'error', message: string) => {
    const id = Date.now().toString() + Math.random().toString().substring(2, 5);
    setToasts((prev) => [...prev, { id, type, message }]);
  }, []);

  const handleDismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const payload = event.data;
      if (payload?.type !== 'EEW_FLAG_E') {
        return;
      }

      const success = raiseEarthquake();
      if (success) {
        addToast('success', 'Earthquake Early Warning broadcasted to devices');
      } else {
        addToast('error', 'Unable to reach server.');
      }
    };

    window.addEventListener('message', handleMessage);

    return () => {
      window.removeEventListener('message', handleMessage);
    };
  }, [addToast, raiseEarthquake]);

  // Handle "Raise SOS" button click
  const handleRaiseSOSClick = () => {
    if (!isConnected) {
      addToast('error', 'Unable to reach server.');
      return;
    }
    setIsModalOpen(true);
  };

  // Handle modal confirmation (requests GPS coordinates if available, falls back to null gracefully)
  const handleConfirmSOS = () => {
    setIsModalOpen(false);

    const dispatchSOS = (lat: number | null = null, lon: number | null = null) => {
      const success = raiseSOS({
        disasterType: 'OVERCROWDING',
        latitude: lat,
        longitude: lon,
      });

      if (success) {
        addToast('success', 'Emergency Alert Broadcasted');
      } else {
        addToast('error', 'Unable to reach server.');
      }
    };

    if (typeof window !== 'undefined' && 'geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          dispatchSOS(pos.coords.latitude, pos.coords.longitude);
        },
        () => {
          // If permission is denied or timeout, send SOS with null coordinates
          dispatchSOS(null, null);
        },
        { timeout: 4000, maximumAge: 0 }
      );
    } else {
      dispatchSOS(null, null);
    }
  };

  const handleEarthquakeTrigger = () => {
    setIsDisasterMenuOpen(false);

    if (!isConnected) {
      addToast('error', 'Unable to reach server.');
      return;
    }

    setIsEEWOverlayOpen(true);
    addToast('success', 'Earthquake simulation started');
  };

  const handleCancelSOS = () => {
    setIsModalOpen(false);
  };

  // Handle "Clear SOS" action
  const handleClearSOSClick = () => {
    const success = clearSOS();
    if (success) {
      addToast('success', 'Emergency Alert Cleared');
    } else {
      addToast('error', 'Unable to reach server.');
    }
  };

  return (
    <div className="h-screen w-screen bg-slate-950 text-slate-100 flex flex-col overflow-hidden font-sans select-none">
      {/* Toast Notifications */}
      <Toast toasts={toasts} onDismiss={handleDismissToast} />

      {/* SOS Confirmation Modal */}
      <ConfirmationModal
        isOpen={isModalOpen}
        onCancel={handleCancelSOS}
        onConfirm={handleConfirmSOS}
      />

      {/* Disaster Detection Menu Overlay Modal */}
      <DisasterDetectionModal
        isOpen={isDisasterMenuOpen}
        onClose={() => setIsDisasterMenuOpen(false)}
        onEarthquakeTrigger={handleEarthquakeTrigger}
      />

      {/* 1. Dashboard Header */}
      <Header
        isConnected={isConnected}
        onDisasterDetectionClick={() => setIsDisasterMenuOpen(true)}
      />

      {/* 2. Control Action Toolbar */}
      <ControlButtons
        onRaiseSOSClick={handleRaiseSOSClick}
        onClearSOSClick={handleClearSOSClick}
        isEmergencyActive={isEmergency}
      />

      {/* 3. Central Viewport (Heatmap + Join QR Panel + Digital Billboard Link + Connected Devices Panel) */}
      <div className="flex-1 p-4 md:p-6 grid grid-cols-1 lg:grid-cols-4 gap-4 min-h-0 bg-slate-950">
        {/* Heatmap Viewport (Occupies 3 out of 4 columns on large screens) */}
        <div className="lg:col-span-3 flex flex-col min-h-0">
          <HeatmapPlaceholder />
        </div>

        {/* Right Side Control Cards: Join Event QR Code + Digital Billboard Link + Connected Attendee Devices */}
        <div className="flex flex-col gap-4 min-h-0 overflow-y-auto">
          <QRCodePanel />
          <BillboardPanel />
          <ConnectedDevicesPanel
            devicesList={devicesList}
            connectedDevices={connectedDevices}
          />
        </div>
      </div>

      {/* 4. Telemetry & Status Panel (Footer) */}
      <StatusPanel
        isConnected={isConnected}
        connectedDevices={connectedDevices}
        crowdCount={crowdCount}
        venueCapacity={venueCapacity}
        crowdStatus={crowdStatus}
      />

      {isEEWOverlayOpen && (
        <div className="fixed inset-0 z-[70] bg-slate-950/90 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-6xl h-[92vh] bg-slate-900 border border-cyan-500/30 rounded-3xl overflow-hidden shadow-2xl shadow-cyan-950/40 flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700 bg-slate-950/80">
              <div>
                <p className="text-[10px] uppercase tracking-[0.3em] text-cyan-300">Earthquake Early Warning</p>
                <h3 className="text-lg font-bold text-white">SEISMOS Live Simulation</h3>
              </div>
              <button
                type="button"
                onClick={() => setIsEEWOverlayOpen(false)}
                className="rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-700"
              >
                Close
              </button>
            </div>

            <iframe
              src="/eew.html"
              title="Earthquake Early Warning Simulation"
              className="w-full h-full border-0 bg-slate-950"
            />
          </div>
        </div>
      )}
    </div>
  );
};
