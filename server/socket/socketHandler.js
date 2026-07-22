const logger = require('../utils/logger');
const { getCurrentCrowd } = require('../services/crowdSimulation');

let connectedDevices = 0;
// Track connected device instances for the Admin Dashboard display
const activeDevicesMap = new Map();
let deviceCounter = 0;

/**
 * Initializes Socket.IO event handlers.
 * 
 * @param {import('socket.io').Server} io - Socket.IO server instance.
 */
function initSocketHandler(io) {
  io.on('connection', (socket) => {
    connectedDevices += 1;
    deviceCounter += 1;

    const deviceName = `Device ${deviceCounter}`;
    activeDevicesMap.set(socket.id, {
      id: socket.id,
      name: deviceName,
      connectedAt: new Date().toLocaleTimeString(),
    });

    logger.info('Device Connected', `Socket ID: ${socket.id} (${deviceName}) | Total Devices: ${connectedDevices}`);

    // Broadcast updated device count & active device list
    io.emit('device-count', connectedDevices);
    io.emit('devices-list', Array.from(activeDevicesMap.values()));

    // Send current crowd metrics to newly connected client immediately
    const current = getCurrentCrowd();
    socket.emit('crowd-count', current.count);
    socket.emit('crowd-status', current.status);

    // Listen for SOS Broadcast trigger from Admin Dashboard
    socket.on('raise-sos', (data = {}) => {
      logger.alert('Emergency Broadcast Initiated', 'SOS event received from Admin Dashboard');

      const sosPayload = {
        title: 'Emergency',
        message: 'Overcrowding detected. Proceed calmly to the nearest exit.',
        disasterType: data?.disasterType || 'OVERCROWDING',
        latitude: typeof data?.latitude === 'number' ? data.latitude : null,
        longitude: typeof data?.longitude === 'number' ? data.longitude : null,
        timestamp: data?.timestamp || new Date().toISOString(),
      };

      // Broadcast emergency alert payload with coordinates to all connected devices
      io.emit('sos-alert', sosPayload);
      logger.success(
        'SOS Broadcast Sent',
        `Payload sent to ${connectedDevices} devices (Lat: ${sosPayload.latitude}, Lon: ${sosPayload.longitude})`
      );
    });

    // Listen for Clear SOS trigger from Admin Dashboard
    socket.on('clear-sos', () => {
      logger.info('Clear Emergency Alert', 'Clear SOS event received from Admin Dashboard');

      // Broadcast clear-alert event to all connected devices
      io.emit('clear-alert');
      logger.success('Clear Alert Sent', 'All attendee devices restored to normal waiting screen');
    });

    // Handle Client Disconnection
    socket.on('disconnect', (reason) => {
      connectedDevices = Math.max(0, connectedDevices - 1);
      const disconnectedDevice = activeDevicesMap.get(socket.id);
      activeDevicesMap.delete(socket.id);

      logger.warn('Device Disconnected', `Socket ID: ${socket.id} (${disconnectedDevice?.name || 'Device'}) [${reason}] | Total Devices: ${connectedDevices}`);

      // Broadcast updated device count & active device list
      io.emit('device-count', connectedDevices);
      io.emit('devices-list', Array.from(activeDevicesMap.values()));
    });

    // Error handling
    socket.on('error', (err) => {
      logger.warn('Socket Error', err.message || err);
    });
  });
}

module.exports = {
  initSocketHandler,
  getConnectedDevicesCount: () => connectedDevices,
};
