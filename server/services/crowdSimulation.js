const logger = require('../utils/logger');

let currentCrowdCount = 0;
let currentCrowdStatus = 'SAFE';
let simulationInterval = null;

/**
 * Updates crowd count, evaluates crowd status, and broadcasts real-time events.
 * This central function is designed for future direct integration with a Python YOLO script.
 * 
 * @param {number} count - The detected or simulated crowd count.
 * @param {import('socket.io').Server} io - Socket.IO server instance.
 */
function updateCrowdCount(count, io) {
  if (typeof count !== 'number' || isNaN(count)) {
    return;
  }

  currentCrowdCount = count;

  // Determine Crowd Status based on thresholds
  if (count < 40) {
    currentCrowdStatus = 'SAFE';
  } else if (count >= 40 && count <= 70) {
    currentCrowdStatus = 'WARNING';
  } else {
    currentCrowdStatus = 'DANGER';
  }

  // Broadcast real-time Socket.IO events to all connected clients
  if (io) {
    io.emit('crowd-count', currentCrowdCount);
    io.emit('crowd-status', currentCrowdStatus);
  }

  logger.metrics(
    io ? io.sockets.sockets.size : 0,
    currentCrowdCount,
    currentCrowdStatus
  );

  return {
    count: currentCrowdCount,
    status: currentCrowdStatus,
  };
}

/**
 * Starts the automated crowd simulation timer.
 * Generates a random crowd count every 3 seconds until replaced by live YOLO stream.
 * 
 * @param {import('socket.io').Server} io - Socket.IO server instance.
 */
function startCrowdSimulation(io) {
  if (simulationInterval) {
    clearInterval(simulationInterval);
  }

  // Initial trigger immediately
  const initialCrowd = Math.floor(Math.random() * 80) + 20;
  updateCrowdCount(initialCrowd, io);

  // Repeat every 3000ms (3 seconds)
  simulationInterval = setInterval(() => {
    const crowd = Math.floor(Math.random() * 80) + 20;
    updateCrowdCount(crowd, io);
  }, 3000);

  logger.info('Crowd Simulation', 'Started simulation engine (3s tick)');
}

/**
 * Stops the crowd simulation timer.
 */
function stopCrowdSimulation() {
  if (simulationInterval) {
    clearInterval(simulationInterval);
    simulationInterval = null;
    logger.info('Crowd Simulation', 'Stopped simulation engine');
  }
}

module.exports = {
  updateCrowdCount,
  startCrowdSimulation,
  stopCrowdSimulation,
  getCurrentCrowd: () => ({ count: currentCrowdCount, status: currentCrowdStatus }),
};
