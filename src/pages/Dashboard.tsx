import React, { useState, useCallback } from 'react';
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
    clearSOS,
  } = useSocket();

  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [isDisasterMenuOpen, setIsDisasterMenuOpen] = useState<boolean>(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  // Toast Helper
  const addToast = useCallback((type: 'success' | 'error', message: string) => {
    const id = Date.now().toString() + Math.random().toString().substring(2, 5);
    setToasts((prev) => [...prev, { id, type, message }]);
  }, []);

  const handleDismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

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
    </div>
  );
};
