import React, { useState, useCallback, useEffect } from 'react';
import { useSocket } from '../hooks/useSocket';
import { Header } from '../components/Header';
import { ControlButtons } from '../components/ControlButtons';
import { HeatmapPlaceholder } from '../components/HeatmapPlaceholder';
import { StatusPanel } from '../components/StatusPanel';
import { ConfirmationModal } from '../components/ConfirmationModal';
import { DisasterDetectionModal } from '../components/DisasterDetectionModal';
import { PublicMovementModal } from '../components/PublicMovementModal';
import { Toast } from '../components/Toast';
import type { ToastMessage } from '../components/Toast';
import { QRCodePanel } from '../components/QRCodePanel';
import { BillboardPanel } from '../components/BillboardPanel';
import { ConnectedDevicesPanel } from '../components/ConnectedDevicesPanel';
import { speakEmergency, stopEmergencySpeech } from '../utils/speech';
import { AlertTriangle } from 'lucide-react';

export const Dashboard: React.FC = () => {
  const {
    isConnected,
    connectedDevices,
    devicesList,
    crowdCount,
    venueCapacity,
    crowdStatus,
    isEmergency,
    emergencyPayload,
    raiseSOS,
    clearSOS,
  } = useSocket();

  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [isDisasterMenuOpen, setIsDisasterMenuOpen] = useState<boolean>(false);
  const [isEEWOverlayOpen, setIsEEWOverlayOpen] = useState<boolean>(false);
  const [isPublicMovementOpen, setIsPublicMovementOpen] = useState<boolean>(false);
  const [autoTriggerInfo, setAutoTriggerInfo] = useState<string | null>(null);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  // Handle Emergency Voice Announcement on Admin Panel ONLY
  useEffect(() => {
    if (isEmergency) {
      const isEarthquake = emergencyPayload?.disasterType === 'EARTHQUAKE' || emergencyPayload?.title?.toLowerCase().includes('earthquake');
      if (isEarthquake) {
        speakEmergency(
          'Attention. Earthquake detected. Evacuate immediately to open ground. Remain calm and follow emergency instructions.'
        );
      } else {
        speakEmergency();
      }
    } else {
      stopEmergencySpeech();
      setAutoTriggerInfo(null);
    }

    return () => {
      stopEmergencySpeech();
    };
  }, [isEmergency, emergencyPayload]);

  // Toast Helper
  const addToast = useCallback((type: 'success' | 'error', message: string) => {
    const id = Date.now().toString() + Math.random().toString().substring(2, 5);
    setToasts((prev) => [...prev, { id, type, message }]);
  }, []);

  const handleDismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Single Reusable triggerSOS Function (used by both Manual Raise SOS & Automatic Earthquake Detection)
  const triggerSOS = useCallback(
    (disasterType: string = 'OVERCROWDING', lat: number | null = null, lon: number | null = null, autoReason?: string) => {
      const success = raiseSOS({
        disasterType,
        latitude: lat,
        longitude: lon,
      });

      if (success) {
        if (autoReason) {
          setAutoTriggerInfo(`Automatic SOS Triggered • Reason: ${autoReason}`);
          addToast('success', `Automatic SOS Triggered: ${autoReason}`);
        } else {
          addToast('success', 'Emergency Alert Broadcasted');
        }
      } else {
        addToast('error', 'Unable to reach server.');
      }
    },
    [raiseSOS, addToast]
  );

  // Subscribe to SEISMOS EEW_FLAG_E from the Earthquake simulation iframe
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const payload = event.data;
      if (payload?.type !== 'EEW_FLAG_E') {
        return;
      }

      if (payload.value === true) {
        // Automatically trigger SOS with EARTHQUAKE disaster payload
        if (typeof window !== 'undefined' && 'geolocation' in navigator) {
          navigator.geolocation.getCurrentPosition(
            (pos) => {
              triggerSOS('EARTHQUAKE', pos.coords.latitude, pos.coords.longitude, 'Earthquake Detection');
            },
            () => {
              triggerSOS('EARTHQUAKE', null, null, 'Earthquake Detection');
            },
            { timeout: 3000 }
          );
        } else {
          triggerSOS('EARTHQUAKE', null, null, 'Earthquake Detection');
        }
      }
    };

    window.addEventListener('message', handleMessage);

    return () => {
      window.removeEventListener('message', handleMessage);
    };
  }, [triggerSOS]);

  // Handle "Raise SOS" button click (Manual Flow)
  const handleRaiseSOSClick = () => {
    if (!isConnected) {
      addToast('error', 'Unable to reach server.');
      return;
    }
    setIsModalOpen(true);
  };

  // Handle manual modal confirmation
  const handleConfirmSOS = () => {
    setIsModalOpen(false);

    if (typeof window !== 'undefined' && 'geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          triggerSOS('OVERCROWDING', pos.coords.latitude, pos.coords.longitude);
        },
        () => {
          triggerSOS('OVERCROWDING', null, null);
        },
        { timeout: 4000, maximumAge: 0 }
      );
    } else {
      triggerSOS('OVERCROWDING', null, null);
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
      setAutoTriggerInfo(null);
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

      {/* Public Movement YOLO People Counter Modal View */}
      <PublicMovementModal
        isOpen={isPublicMovementOpen}
        onClose={() => setIsPublicMovementOpen(false)}
      />

      {/* 1. Dashboard Header */}
      <Header
        isConnected={isConnected}
        onDisasterDetectionClick={() => setIsDisasterMenuOpen(true)}
      />

      {/* Automatic SOS Trigger Informational Banner */}
      {autoTriggerInfo && isEmergency && (
        <div className="bg-amber-950/90 border-b border-amber-500/40 px-6 py-2 flex items-center space-x-2 text-xs font-mono text-amber-200 animate-pulse shrink-0">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
          <span className="font-bold">{autoTriggerInfo}</span>
        </div>
      )}

      {/* 2. Control Action Toolbar */}
      <ControlButtons
        onRaiseSOSClick={handleRaiseSOSClick}
        onClearSOSClick={handleClearSOSClick}
        onPublicMovementClick={() => setIsPublicMovementOpen(true)}
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

      {/* SEISMOS EEW Simulation Overlay */}
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
