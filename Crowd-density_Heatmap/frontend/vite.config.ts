import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The backend base URL is injected at build/runtime via VITE_API_BASE.
// In dev we proxy /api (REST + WebSocket) to the backend so there are no CORS
// surprises. `ws: true` is required so the /api/v1/stream/live WebSocket
// upgrade is forwarded to the backend.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
