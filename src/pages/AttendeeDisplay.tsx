import React from 'react';
import { useSocket } from '../hooks/useSocket';
import { AttendeeWaitingScreen } from '../components/AttendeeWaitingScreen';
import { EmergencyScreen } from '../components/EmergencyScreen';

export const AttendeeDisplay: React.FC = () => {
  const {
    isConnected,
    crowdCount,
    crowdStatus,
    isEmergency,
    emergencyPayload,
  } = useSocket();

  if (isEmergency) {
    return <EmergencyScreen payload={emergencyPayload} />;
  }

  return (
    <AttendeeWaitingScreen
      isConnected={isConnected}
      crowdCount={crowdCount}
      crowdStatus={crowdStatus}
    />
  );
};
