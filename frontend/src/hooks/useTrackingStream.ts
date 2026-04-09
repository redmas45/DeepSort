import { useEffect, useRef, useState } from "react";
import type { Stats, StreamFrameMessage, StreamInfoMessage, Track } from "../types";

const CAMERA_CAPTURE_FPS = 5;
const CAMERA_JPEG_QUALITY = 0.72;
const CAMERA_MAX_WIDTH = 960;

function buildWebSocketUrl(pathname: string, params?: Record<string, string>) {
  const explicitOrigin = import.meta.env.VITE_BACKEND_URL as string | undefined;

  if (explicitOrigin) {
    const url = new URL(explicitOrigin);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    url.pathname = pathname;
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.set(key, value);
      });
    }
    return url.toString();
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const url = new URL(`${protocol}//${window.location.host}${pathname}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.set(key, value);
    });
  }
  return url.toString();
}

export function useTrackingStream() {
  const socketRef = useRef<WebSocket | null>(null);
  const cameraStreamRef = useRef<MediaStream | null>(null);
  const captureVideoRef = useRef<HTMLVideoElement | null>(null);
  const captureCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const captureTimerRef = useRef<number | null>(null);
  const [frameData, setFrameData] = useState<string>("");
  const [tracks, setTracks] = useState<Track[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [status, setStatus] = useState<"idle" | "connecting" | "live" | "closed" | "error">("idle");
  const [message, setMessage] = useState<string>("Select a source and start the stream.");

  function stopCameraCapture() {
    if (captureTimerRef.current !== null) {
      window.clearInterval(captureTimerRef.current);
      captureTimerRef.current = null;
    }

    cameraStreamRef.current?.getTracks().forEach((track) => track.stop());
    cameraStreamRef.current = null;
    captureVideoRef.current = null;
    captureCanvasRef.current = null;
  }

  function disconnect() {
    socketRef.current?.close();
    socketRef.current = null;
    stopCameraCapture();
    setStatus("closed");
    setMessage("Tracking stopped.");
  }

  function bindSocket(socket: WebSocket) {
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as StreamFrameMessage | StreamInfoMessage;

      if (payload.event === "frame") {
        setFrameData(`data:image/jpeg;base64,${payload.frame}`);
        setTracks(payload.tracks);
        setStats(payload.stats);
        return;
      }

      if (payload.event === "ready") {
        setMessage(payload.message ?? "Camera stream ready.");
        return;
      }

      if (payload.event === "end") {
        setMessage(`Stream finished for ${payload.video_name ?? "current source"}`);
        setStatus("closed");
        return;
      }

      setMessage(payload.message ?? "Stream error");
      setStatus("error");
    };

    socket.onerror = () => {
      setStatus("error");
      setMessage("WebSocket connection failed.");
    };

    socket.onclose = () => {
      if (socketRef.current === socket) {
        socketRef.current = null;
      }
      stopCameraCapture();
      setStatus((current) => (current === "error" ? current : "closed"));
    };
  }

  function startCameraPump(socket: WebSocket) {
    const video = captureVideoRef.current;
    if (!video) {
      setStatus("error");
      setMessage("Camera preview is not available.");
      return;
    }

    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d");
    if (!context) {
      setStatus("error");
      setMessage("Unable to create a camera capture canvas.");
      return;
    }
    captureCanvasRef.current = canvas;

    captureTimerRef.current = window.setInterval(() => {
      if (socket.readyState !== WebSocket.OPEN || !video.videoWidth || !video.videoHeight) {
        return;
      }

      const scale = Math.min(1, CAMERA_MAX_WIDTH / video.videoWidth);
      canvas.width = Math.round(video.videoWidth * scale);
      canvas.height = Math.round(video.videoHeight * scale);
      context.drawImage(video, 0, 0, canvas.width, canvas.height);

      socket.send(
        JSON.stringify({
          event: "frame",
          frame: canvas.toDataURL("image/jpeg", CAMERA_JPEG_QUALITY),
        }),
      );
    }, Math.round(1000 / CAMERA_CAPTURE_FPS));
  }

  function connectVideo(video: string) {
    disconnect();
    setStatus("connecting");
    setMessage(`Connecting to ${video}...`);

    const socket = new WebSocket(buildWebSocketUrl("/ws/stream", { video }));
    socketRef.current = socket;

    socket.onopen = () => {
      setStatus("live");
      setMessage(`Streaming ${video}`);
    };
    bindSocket(socket);
  }

  async function startCamera() {
    disconnect();
    setStatus("connecting");
    setMessage("Requesting camera access...");

    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus("error");
      setMessage("This browser does not support camera capture.");
      return;
    }

    try {
      let mediaStream: MediaStream;
      try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: "environment",
          },
          audio: false,
        });
      } catch {
        mediaStream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        });
      }

      const captureVideo = document.createElement("video");
      captureVideo.srcObject = mediaStream;
      captureVideo.muted = true;
      captureVideo.playsInline = true;
      await captureVideo.play();

      cameraStreamRef.current = mediaStream;
      captureVideoRef.current = captureVideo;

      const socket = new WebSocket(buildWebSocketUrl("/ws/live-camera"));
      socketRef.current = socket;

      socket.onopen = () => {
        setStatus("live");
        setMessage("Camera tracking is live.");
        startCameraPump(socket);
      };

      bindSocket(socket);
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Unable to access the camera.");
      stopCameraCapture();
    }
  }

  useEffect(() => {
    return () => {
      socketRef.current?.close();
      stopCameraCapture();
    };
  }, []);

  return {
    connectVideo,
    startCamera,
    disconnect,
    frameData,
    tracks,
    stats,
    status,
    message,
  };
}
