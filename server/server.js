const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');

const logger = require('./utils/logger');
const healthRoutes = require('./routes/health');
const { initSocketHandler } = require('./socket/socketHandler');
const { startCrowdSimulation } = require('./services/crowdSimulation');

const PORT = process.env.PORT || 5001;
const HOST = process.env.HOST || '0.0.0.0';

// Express Application Setup
const app = express();

// Enable CORS for all HTTP and WebSocket origins
app.use(cors({
  origin: '*',
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
}));

app.use(express.json());

// Base Route
app.get('/', (req, res) => {
  res.status(200).json({ status: 'CrowdShield Server Running' });
});

// Health Route
app.use('/health', healthRoutes);

// HTTP Server & Socket.IO Initialization
const server = http.createServer(app);

const io = new Server(server, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST'],
  },
  transports: ['websocket', 'polling'],
});

// Initialize Socket Event Handlers
initSocketHandler(io);

// Start Server & Background Crowd Simulator
server.listen(PORT, HOST, () => {
  logger.success('Server Started', `CrowdShield Central Control Engine running on http://${HOST}:${PORT}`);
  
  // Start the 3-second crowd simulation engine
  startCrowdSimulation(io);
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    logger.warn('Port Conflict', `Port ${PORT} is in use. Exiting...`);
    process.exit(1);
  } else {
    console.error('Server error:', err);
  }
});

// Graceful Shutdown Handling
process.on('SIGINT', () => {
  logger.warn('Server Shutdown', 'Received SIGINT. Closing HTTP and Socket.IO server...');
  server.close(() => {
    process.exit(0);
  });
});
