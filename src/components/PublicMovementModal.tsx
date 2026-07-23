import React, { useEffect, useState, useRef } from 'react';
import { X, Camera, Footprints, AlertCircle, RefreshCw, Eye, ShieldCheck } from 'lucide-react';

interface PublicMovementModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PublicMovementModal: React.FC<PublicMovementModalProps> = ({ isOpen, onClose }) => {
  const [viewMode, setViewMode] = useState<'control_room' | 'local_webcam'>('control_room');
  const [isCameraActive, setIsCameraActive] = useState<boolean>(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [personCount, setPersonCount] = useState<number>(0);
  const [serverHeadcount, setServerHeadcount] = useState<number | null>(null);
  const [serverRisk, setServerRisk] = useState<number | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const uploadIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const hostname = typeof window !== 'undefined' && window.location.hostname ? window.location.hostname : 'localhost';
  const flaskServerUrl = `http://${hostname}:5002`;
  const cameraIdRef = useRef<string>(`webcam_${Math.floor(Math.random() * 899 + 100)}`);

  // Listen for Escape key press to dismiss modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  // Poll teammate's Flask server telemetry analytics
  useEffect(() => {
    if (!isOpen) return;

    const fetchAnalytics = async () => {
      try {
        const res = await fetch(`${flaskServerUrl}/api/analytics`);
        if (res.ok) {
          const data = await res.json();
          setServerHeadcount(data.global_headcount ?? 0);
          setServerRisk(data.global_max_risk ?? 0);
        }
      } catch {
        // Flask server offline or unreached
      }
    };

    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 1500);

    return () => clearInterval(interval);
  }, [isOpen, flaskServerUrl]);

  // Stream local webcam frames to Python Flask YOLO backend for real-time detection
  const startFrameUpload = () => {
    if (uploadIntervalRef.current) clearInterval(uploadIntervalRef.current);

    let inFlight = false;
    uploadIntervalRef.current = setInterval(() => {
      if (!videoRef.current || !videoRef.current.videoWidth || inFlight) return;

      const video = videoRef.current;
      const canvas = canvasRef.current || document.createElement('canvas');
      canvasRef.current = canvas;
      canvas.width = 640;
      canvas.height = 480;

      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      ctx.drawImage(video, 0, 0, 640, 480);

      inFlight = true;
      canvas.toBlob(
        async (blob) => {
          if (!blob) {
            inFlight = false;
            return;
          }

          const formData = new FormData();
          formData.append('frame', blob, 'frame.jpg');
          formData.append('camera_id', cameraIdRef.current);
          formData.append('device_name', `Webcam Node (${cameraIdRef.current})`);

          try {
            await fetch(`${flaskServerUrl}/api/stream_upload`, {
              method: 'POST',
              body: formData,
            });
          } catch {
            // Ignore upload errors
          } finally {
            inFlight = false;
          }
        },
        'image/jpeg',
        0.65
      );
    }, 150);
  };

  // Safely request webcam stream across secure and legacy contexts
  const startWebcam = async () => {
    setCameraError(null);

    if (typeof window === 'undefined' || !navigator) {
      setCameraError('Webcam access unavailable in this environment.');
      setIsCameraActive(false);
      return;
    }

    const hasMediaDevices = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);

    if (!hasMediaDevices) {
      const legacyGetUserMedia =
        (navigator as unknown as { getUserMedia?: Function }).getUserMedia ||
        (navigator as unknown as { webkitGetUserMedia?: Function }).webkitGetUserMedia ||
        (navigator as unknown as { mozGetUserMedia?: Function }).mozGetUserMedia;

      if (!legacyGetUserMedia) {
        setCameraError(
          'Insecure Context (HTTP): Browser blocks local webcam on LAN IP addresses. Open dashboard at http://localhost:5173 or switch to "CCTV Control Room" mode!'
        );
        setIsCameraActive(false);
        return;
      }

      try {
        const stream: MediaStream = await new Promise((resolve, reject) => {
          legacyGetUserMedia.call(
            navigator,
            { video: { width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false },
            resolve,
            reject
          );
        });

        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
        setIsCameraActive(true);
        startFrameUpload();
        return;
      } catch (err: unknown) {
        const errorMsg = err instanceof Error ? err.message : 'Webcam permission denied.';
        setCameraError(`Camera Error: ${errorMsg}`);
        setIsCameraActive(false);
        return;
      }
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
        audio: false,
      });

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setIsCameraActive(true);
      startFrameUpload();
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Permission denied or webcam unavailable.';
      setCameraError(`Camera Error: ${errorMsg}`);
      setIsCameraActive(false);
    }
  };

  // Stop local webcam stream and frame uploader
  const stopWebcam = () => {
    if (uploadIntervalRef.current) {
      clearInterval(uploadIntervalRef.current);
      uploadIntervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsCameraActive(false);
  };

  // Cleanup camera when modal closes
  useEffect(() => {
    if (!isOpen) {
      stopWebcam();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const activeHeadcount = serverHeadcount !== null ? serverHeadcount : (isCameraActive ? personCount : 0);

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-[70] flex items-center justify-center p-4 md:p-6 bg-slate-950/85 backdrop-blur-md animate-fadeIn cursor-pointer"
      role="dialog"
      aria-modal="true"
      aria-labelledby="public-movement-title"
    >
      {/* Hidden processing canvas */}
      <canvas ref={canvasRef} style={{ display: 'none' }} />

      {/* Modal Container */}
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-slate-900 border border-slate-800 rounded-3xl max-w-6xl w-full h-[90vh] p-6 shadow-2xl relative cursor-default overflow-hidden flex flex-col justify-between"
      >
        {/* Subtle Top Accent Line */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-cyan-500 via-blue-500 to-indigo-500" />

        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4 shrink-0">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-cyan-950/80 border border-cyan-500/40 rounded-2xl text-cyan-400 shadow-inner">
              <Footprints className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <h2 id="public-movement-title" className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                <span>Public Movement & YOLO People Counter</span>
              </h2>
              <p className="text-xs text-slate-400 font-medium mt-0.5">
                Real-Time Computer Vision Crowd Analytics & Spatial Density Tracking
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {/* View Mode Toggle */}
            <div className="bg-slate-950/80 border border-slate-800 p-1 rounded-xl flex items-center space-x-1">
              <button
                type="button"
                onClick={() => setViewMode('control_room')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${viewMode === 'control_room'
                  ? 'bg-cyan-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
                  }`}
              >
                CCTV Control Room
              </button>
              <button
                type="button"
                onClick={() => {
                  setViewMode('local_webcam');
                  if (!isCameraActive) startWebcam();
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${viewMode === 'local_webcam'
                  ? 'bg-cyan-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
                  }`}
              >
                Local Webcam Node
              </button>
            </div>

            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white p-2 rounded-xl hover:bg-slate-800 transition-colors cursor-pointer"
              aria-label="Close Public Movement View"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Telemetry Metrics Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 my-3 shrink-0">
          <div className="bg-slate-950/80 border border-slate-800 p-3 rounded-2xl flex items-center space-x-3">
            <div className="p-2 bg-cyan-900/40 text-cyan-400 rounded-xl">
              <Eye className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[10px] uppercase font-mono tracking-wider text-slate-400">Total Headcount</p>
              <p className="text-lg font-black text-white font-mono">{activeHeadcount} Ppl</p>
            </div>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 p-3 rounded-2xl flex items-center space-x-3">
            <div className="p-2 bg-emerald-900/40 text-emerald-400 rounded-xl">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[10px] uppercase font-mono tracking-wider text-slate-400">Stampede Risk</p>
              <p className="text-lg font-black text-emerald-400 font-mono">
                {serverRisk !== null ? serverRisk.toFixed(2) : '0.00 (NOMINAL)'}
              </p>
            </div>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 p-3 rounded-2xl flex items-center space-x-3">
            <div className="p-2 bg-indigo-900/40 text-indigo-400 rounded-xl">
              <Camera className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[10px] uppercase font-mono tracking-wider text-slate-400">YOLO Model</p>
              <p className="text-xs font-bold text-white font-mono">YOLOv8 + ByteTrack</p>
            </div>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 p-3 rounded-2xl flex items-center justify-between px-4">
            <div>
              <p className="text-[10px] uppercase font-mono tracking-wider text-slate-400">Camera Engine</p>
              <p className="text-xs font-bold text-cyan-300 font-mono">
                {viewMode === 'control_room' ? 'Flask Multi-CCTV' : 'YOLO Stream Node'}
              </p>
            </div>

            {viewMode === 'local_webcam' && (
              <button
                type="button"
                onClick={isCameraActive ? stopWebcam : startWebcam}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${isCameraActive
                  ? 'bg-rose-600 hover:bg-rose-500 text-white'
                  : 'bg-emerald-600 hover:bg-emerald-500 text-white'
                  }`}
              >
                {isCameraActive ? 'Stop Camera' : 'Start Camera'}
              </button>
            )}
          </div>
        </div>

        {/* Main Viewport Content */}
        <div className="flex-1 bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden relative min-h-0 flex flex-col justify-center items-center">
          {viewMode === 'control_room' ? (
            /* 1. Teammate's Flask CCTV Digital Twin Control Room Feed */
            <iframe
              src={flaskServerUrl}
              title="CCTV Digital Twin & YOLO Control Room"
              className="w-full h-full border-0 bg-slate-950"
            />
          ) : (
            /* 2. Direct Browser Webcam Stream Engine */
            <div className="relative w-full h-full flex flex-col items-center justify-center bg-slate-950">
              <video
                ref={videoRef}
                className={`w-full h-full object-cover ${!isCameraActive ? 'hidden' : ''}`}
                autoPlay
                playsInline
                muted
              />

              {/* Live Bounding Box Overlay indicator */}
              {isCameraActive && (
                <div className="absolute top-4 left-4 bg-slate-950/80 border border-cyan-500/50 backdrop-blur-md px-3 py-1.5 rounded-xl text-xs font-mono text-cyan-300 flex items-center space-x-2 shadow-lg">
                  <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
                  <span>YOLO STREAM NODE ACTIVE • HEADCOUNT: {activeHeadcount}</span>
                </div>
              )}

              {/* Camera Stopped / Insecure Context / Permission Denied State */}
              {!isCameraActive && (
                <div className="flex flex-col items-center justify-center p-6 text-center space-y-4 max-w-md">
                  <div className="w-16 h-16 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-400">
                    <Camera className="w-8 h-8 text-cyan-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white">Laptop Webcam Node Standby</h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Tap Start Camera below or switch to <strong className="text-cyan-300">CCTV Control Room</strong> mode in the top right.
                    </p>
                  </div>

                  {cameraError && (
                    <div className="flex items-center space-x-2 text-xs font-semibold text-rose-300 bg-rose-950/80 border border-rose-500/40 p-3.5 rounded-xl text-left shadow-lg">
                      <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
                      <span>{cameraError}</span>
                    </div>
                  )}

                  <div className="flex items-center space-x-3 pt-1">
                    <button
                      type="button"
                      onClick={startWebcam}
                      className="px-5 py-2.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold text-xs rounded-xl shadow-lg border border-cyan-400/40 transition-all active:scale-95 cursor-pointer flex items-center space-x-2"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      <span>Start Webcam Feed</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setViewMode('control_room')}
                      className="px-5 py-2.5 bg-slate-800 hover:bg-slate-750 text-cyan-300 font-bold text-xs rounded-xl border border-slate-700 transition-all active:scale-95 cursor-pointer"
                    >
                      Use CCTV Control Room
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer Note */}
        <p className="text-center text-[11px] text-slate-500 mt-3 shrink-0">
          Press <kbd className="bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded border border-slate-700 font-mono text-[10px]">Esc</kbd> or click outside to dismiss this view
        </p>
      </div>
    </div>
  );
};
