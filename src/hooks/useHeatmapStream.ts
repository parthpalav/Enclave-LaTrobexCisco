import { useEffect, useRef, useState } from "react";
import type { Analytics, CameraStatus, LiveFrame } from "../types/heatmap";
import { heatmapWsUrl } from "../services/heatmapApi";

interface HeatmapStreamState {
  connected: boolean;
  image?: string;
  rawImage?: string;
  analytics?: Analytics;
  status?: CameraStatus;
}

export function useHeatmapStream(cameraId: string | null): HeatmapStreamState {
  const [state, setState] = useState<HeatmapStreamState>({ connected: false });
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
      try {
        const ws = new WebSocket(heatmapWsUrl(cameraId));
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
      } catch {
        setState((s) => ({ ...s, connected: false }));
        if (!closed) {
          timer = setTimeout(connect, retryRef.current);
          retryRef.current = Math.min(retryRef.current * 1.5, 8000);
        }
      }
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
