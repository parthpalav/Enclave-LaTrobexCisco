# CrowdShield Central Server

The central control server for **CrowdShield**, built with Node.js, Express, and Socket.IO. It operates in-memory to manage real-time communication between the Admin Dashboard, attendee mobile/display clients, and future Python YOLO crowd detection streams.

---

## 📁 Folder Structure

```
server/
├── package.json
├── server.js                 # Express server entry point & Socket.IO server initialization
├── socket/
│   └── socketHandler.js      # Socket connection lifecycle, device counter, and SOS handler
├── routes/
│   └── health.js             # GET /health health check route
├── services/
│   └── crowdSimulation.js    # Crowd update engine & 3-second simulation timer
├── utils/
│   └── logger.js             # Formatted terminal logger
└── README.md                 # Server documentation
```

---

## 📦 Installation & Setup

1. **Navigate to the server directory**:
   ```bash
   cd server
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start the server**:
   - Production mode:
     ```bash
     npm start
     ```
   - Development mode (with auto-reload):
     ```bash
     npm run dev
     ```

The server listens on **`http://0.0.0.0:5001`**.

---

## 📡 HTTP Endpoints

- `GET /` -> Returns `{ "status": "CrowdShield Server Running" }`
- `GET /health` -> Returns `{ "healthy": true }`

---

## 🔌 Socket.IO Event Dictionary

### Emitted Events (Server ➔ Clients)
| Event | Type | Description | Payload Example |
| :--- | :--- | :--- | :--- |
| `device-count` | `number` | Total number of connected clients | `4` |
| `devices-list` | `array` | List of connected device instances | `[{ "id": "...", "name": "Device 1" }]` |
| `crowd-count` | `number` | Real-time detected or simulated crowd count | `56` |
| `crowd-status` | `string` | Crowd safety status (`SAFE`, `WARNING`, `DANGER`) | `"WARNING"` |
| `sos-alert` | `object` | Emergency alert broadcast triggered by Admin Dashboard | `{ "title": "Emergency", "message": "Overcrowding detected. Proceed calmly to the nearest exit.", "timestamp": "..." }` |
| `clear-alert` | `void` | Signal to clear emergency alert and return attendee screens to normal state | `null` |

### Listened Events (Dashboard ➔ Server)
| Event | Description | Action Taken |
| :--- | :--- | :--- |
| `raise-sos` | Emergency broadcast trigger sent from Admin Dashboard | Logs `[Emergency Broadcast Initiated]` and broadcasts `sos-alert` to all connected clients. |
| `clear-sos` | Clear emergency broadcast trigger sent from Admin Dashboard | Logs `[Clear Emergency Alert]` and broadcasts `clear-alert` to all connected clients. |

---

## 🤖 Future YOLO Integration

The crowd management engine is designed for seamless plug-and-play integration with a Python YOLO object detection pipeline.

In `services/crowdSimulation.js`:
```javascript
updateCrowdCount(count, io)
```
When the Python YOLO script is deployed, invoke `updateCrowdCount(yoloCount, io)` directly upon receiving camera frame detections.
