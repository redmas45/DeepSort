import { useEffect, useRef, useState } from "react";
import type { Stats, StreamFrameMessage, StreamInfoMessage, Track } from "../types";

function buildWebSocketUrl(video: string) {
  const explicitOrigin = import.meta.env.VITE_BACKEND_URL as string | undefined;

  if (explicitOrigin) {
    const url = new URL(explicitOrigin);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    url.pathname = "/ws/stream";
    url.searchParams.set("video", video);
    return url.toString();
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/stream?video=${encodeURIComponent(video)}`;
}

export function useTrackingStream() {
  const socketRef = useRef<WebSocket | null>(null);
  const [frameData, setFrameData] = useState<string>("");
  const [tracks, setTracks] = useState<Track[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [status, setStatus] = useState<"idle" | "connecting" | "live" | "closed" | "error">("idle");
  const [message, setMessage] = useState<string>("Select a source and start the stream.");

  function disconnect() {
    socketRef.current?.close();
    socketRef.current = null;
    setStatus("closed");
  }

  function connect(video: string) {
    disconnect();
    setStatus("connecting");
    setMessage(`Connecting to ${video}...`);

    const socket = new WebSocket(buildWebSocketUrl(video));
    socketRef.current = socket;

    socket.onopen = () => {
      setStatus("live");
      setMessage(`Streaming ${video}`);
    };

    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as StreamFrameMessage | StreamInfoMessage;

      if (payload.event === "frame") {
        setFrameData(`data:image/jpeg;base64,${payload.frame}`);
        setTracks(payload.tracks);
        setStats(payload.stats);
        return;
      }

      if (payload.event === "end") {
        setMessage(`Stream finished for ${payload.video_name ?? video}`);
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
      setStatus((current) => (current === "error" ? current : "closed"));
    };
  }

  useEffect(() => {
    return () => {
      socketRef.current?.close();
    };
  }, []);

  return {
    connect,
    disconnect,
    frameData,
    tracks,
    stats,
    status,
    message,
  };
}
