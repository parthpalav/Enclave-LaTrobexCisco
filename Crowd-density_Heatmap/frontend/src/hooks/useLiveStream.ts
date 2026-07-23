import { useEffect, useRef, useState } from "react";
import type { Analytics, CameraStatus, LiveFrame } from "../types";
import { wsUrl } from "../services/api";

interface LiveState {
  connected: boolean;
  image?: string;
  rawImage?: string;
  analytics?: Analytics;
  status?: CameraStatus;
}

/**
 * Subscribe to the backend WebSocket for a camera and expose the latest
 * heatmap image + analytics. Auto-reconnects with backoff.
 */
export function useLiveStream(cameraId: string | null): LiveState {
  const [state, setState] = useState<LiveState>({ connected: false });
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef<number>(1000);

  useEffect(() => {
    if (!cameraId) {
      setState({ connected: false });
      return;
    }

    let closed = false;
    let timer: ReturnType<typeof setTimeout>;

    const connect = () => {
      const ws = new WebSocket(wsUrl(cameraId));
      wsRef.current = ws;

      ws.onopen = () => {
        retryRef.current = 1000;
        setState((s) => ({ ...s, connected: true }));
      };

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data) as LiveFrame | { error: string };
          if ("error" in msg) return;
          setState({
            connected: true,
            image: msg.image,
            rawImage: msg.raw_image,
            analytics: msg.analytics,
            status: msg.status,
          });
        } catch {
          /* ignore malformed frames */
        }
      };

      ws.onclose = () => {
        setState((s) => ({ ...s, connected: false }));
        if (!closed) {
          timer = setTimeout(connect, retryRef.current);
          retryRef.current = Math.min(retryRef.current * 1.5, 8000);
        }
      };

      ws.onerror = () => ws.close();
    };

    connect();

    return () => {
      closed = true;
      clearTimeout(timer);
      wsRef.current?.close();
    };
  }, [cameraId]);

  return state;
}
