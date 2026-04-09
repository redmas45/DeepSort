import { useEffect, useState } from "react";
import { StatsOverlay } from "./components/StatsOverlay";
import { TrackPanel } from "./components/TrackPanel";
import { VideoCanvas } from "./components/VideoCanvas";
import { useTrackingStream } from "./hooks/useTrackingStream";
import { fetchSources } from "./lib/api";
import type { VideoSource } from "./types";

type TrackingMode = "video" | "camera";

export default function App() {
  const [sources, setSources] = useState<VideoSource[]>([]);
  const [selectedSource, setSelectedSource] = useState<string>("demo://synthetic");
  const [mode, setMode] = useState<TrackingMode>("camera");
  const [loadingSources, setLoadingSources] = useState(true);
  const [sourceError, setSourceError] = useState("");
  const { connectVideo, startCamera, disconnect, frameData, tracks, stats, status, message } =
    useTrackingStream();

  useEffect(() => {
    async function loadSources() {
      try {
        const nextSources = await fetchSources();
        setSources(nextSources);
        if (nextSources.length > 0) {
          setSelectedSource(nextSources[0].name);
        }
      } catch (error) {
        setSourceError(error instanceof Error ? error.message : "Unable to fetch sources.");
      } finally {
        setLoadingSources(false);
      }
    }

    void loadSources();
  }, []);

  return (
    <main className="app-shell">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">DeepSORT + Railway</p>
          <h1>Open the camera, detect people, and keep stable IDs in real time.</h1>
          <p className="hero-text">
            The final product now matches your goal: browser camera access, YOLO11 person detection,
            DeepSORT tracking, and a Railway-hosted dashboard that returns annotated live frames, counts,
            and person IDs. The prerecorded videos stay available for demos and side-by-side evaluation.
          </p>
        </div>

        <div className="hero-controls panel">
          <div className="mode-switch" role="tablist" aria-label="Tracking mode">
            <button
              className={`mode-chip ${mode === "camera" ? "mode-chip-active" : ""}`}
              onClick={() => setMode("camera")}
              type="button"
            >
              Live camera
            </button>
            <button
              className={`mode-chip ${mode === "video" ? "mode-chip-active" : ""}`}
              onClick={() => setMode("video")}
              type="button"
            >
              Video playback
            </button>
          </div>

          <label className="field">
            <span>{mode === "camera" ? "Fallback demo source" : "Video source"}</span>
            <select
              value={selectedSource}
              onChange={(event) => setSelectedSource(event.target.value)}
              disabled={loadingSources || mode === "camera"}
            >
              {sources.map((source) => (
                <option key={source.name} value={source.name}>
                  {source.name}
                </option>
              ))}
            </select>
          </label>

          <div className="button-row">
            <button
              className="button button-primary"
              onClick={() => {
                if (mode === "camera") {
                  void startCamera();
                  return;
                }
                connectVideo(selectedSource);
              }}
            >
              {mode === "camera" ? "Enable camera tracking" : "Start video stream"}
            </button>
            <button className="button button-secondary" onClick={disconnect}>
              Stop stream
            </button>
          </div>

          <p className="muted">
            {mode === "camera"
              ? "Camera permission is requested in the browser, then frames are streamed to FastAPI for tracking."
              : "Use your uploaded videos to test the same tracking pipeline without a live camera."}
          </p>
          {sourceError ? <p className="error-text">{sourceError}</p> : null}
          {loadingSources ? <p className="muted">Loading available sources...</p> : null}
        </div>
      </section>

      <section className="dashboard-grid">
        <VideoCanvas frameData={frameData} />
        <div className="side-stack">
          <TrackPanel tracks={tracks} />
          <StatsOverlay stats={stats} status={status} message={message} />
        </div>
      </section>
    </main>
  );
}
