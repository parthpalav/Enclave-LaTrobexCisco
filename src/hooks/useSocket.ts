import { useEffect, useState, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';

export type CrowdStatus = 'SAFE' | 'WARNING' | 'DANGER';

export interface DeviceInfo {
  id: string;
  name: string;
  connectedAt: string;
}

export interface EmergencyPayload {
  title: string;
  message: string;
  timestamp: string;
}

export interface UseSocketReturn {
  isConnected: boolean;
  connectedDevices: number;
  devicesList: DeviceInfo[];
  crowdCount: number;
  crowdStatus: CrowdStatus;
  venueCapacity: number;
  isEmergency: boolean;
  emergencyPayload: EmergencyPayload | null;
  raiseSOS: () => boolean;
  clearSOS: () => boolean;
}

// Automatically resolve server host dynamically based on current window location
const getSocketUrl = () => {
  if (import.meta.env.VITE_SOCKET_URL) {
    return import.meta.env.VITE_SOCKET_URL;
  }
  const hostname = typeof window !== 'undefined' && window.location.hostname ? window.location.hostname : 'localhost';
  return `http://${hostname}:5001`;
};

export function useSocket(): UseSocketReturn {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [connectedDevices, setConnectedDevices] = useState<number>(0);
  const [devicesList, setDevicesList] = useState<DeviceInfo[]>([]);
  const [crowdCount, setCrowdCount] = useState<number>(0);
  const [crowdStatus, setCrowdStatus] = useState<CrowdStatus>('SAFE');
  const [isEmergency, setIsEmergency] = useState<boolean>(false);
  const [emergencyPayload, setEmergencyPayload] = useState<EmergencyPayload | null>(null);

  const venueCapacity = 100;
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    const socketUrl = getSocketUrl();
    const socket = io(socketUrl, {
      autoConnect: true,
      transports: ['websocket', 'polling'],
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
    });

    socketRef.current = socket;

    // Connection events
    socket.on('connect', () => {
      setIsConnected(true);
    });

    socket.on('disconnect', () => {
      setIsConnected(false);
    });

    socket.on('connect_error', () => {
      setIsConnected(false);
    });

    // Telemetry events
    socket.on('device-count', (count: number) => {
      if (typeof count === 'number' && !isNaN(count)) {
        setConnectedDevices(count);
      }
    });

    socket.on('devices-list', (list: DeviceInfo[]) => {
      if (Array.isArray(list)) {
        setDevicesList(list);
      }
    });

    socket.on('crowd-count', (count: number) => {
      if (typeof count === 'number' && !isNaN(count)) {
        setCrowdCount(count);
      }
    });

    socket.on('crowd-status', (status: string) => {
      const upperStatus = String(status).toUpperCase();
      if (upperStatus === 'SAFE' || upperStatus === 'WARNING' || upperStatus === 'DANGER') {
        setCrowdStatus(upperStatus as CrowdStatus);
      }
    });

    // Emergency events
    socket.on('sos-alert', (payload: EmergencyPayload) => {
      setIsEmergency(true);
      setEmergencyPayload(payload || {
        title: 'Emergency',
        message: 'Overcrowding detected. Proceed calmly to the nearest exit.',
        timestamp: new Date().toISOString(),
      });
    });

    socket.on('clear-alert', () => {
      setIsEmergency(false);
      setEmergencyPayload(null);
    });

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, []);

  const raiseSOS = useCallback((): boolean => {
    if (socketRef.current && socketRef.current.connected) {
      socketRef.current.emit('raise-sos');
      return true;
    }
    return false;
  }, []);

  const clearSOS = useCallback((): boolean => {
    if (socketRef.current && socketRef.current.connected) {
      socketRef.current.emit('clear-sos');
      return true;
    }
    return false;
  }, []);

  return {
    isConnected,
    connectedDevices,
    devicesList,
    crowdCount,
    crowdStatus,
    venueCapacity,
    isEmergency,
    emergencyPayload,
    raiseSOS,
    clearSOS,
  };
}
