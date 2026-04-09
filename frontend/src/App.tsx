import { useEffect, useState } from "react";
import { StatsOverlay } from "./components/StatsOverlay";
import { TrackPanel } from "./components/TrackPanel";
import { VideoCanvas } from "./components/VideoCanvas";
import { useTrackingStream } from "./hooks/useTrackingStream";
import { fetchSources } from "./lib/api";
import type { VideoSource } from "./types";

export default function App() {
  const [sources, setSources] = useState<VideoSource[]>([]);
  const [selectedSource, setSelectedSource] = useState<string>("demo://synthetic");
  const [loadingSources, setLoadingSources] = useState(true);
  const [sourceError, setSourceError] = useState("");
  const { connect, disconnect, frameData, tracks, stats, status, message } = useTrackingStream();

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
          <h1>Track people across video streams with stable IDs and a live dashboard.</h1>
          <p className="hero-text">
            This starter follows your diagram: input videos, OpenCV preprocessing, detector and tracker
            adapters, FastAPI streaming, and a React client for frames, tracks, and stats.
          </p>
        </div>

        <div className="hero-controls panel">
          <label className="field">
            <span>Video source</span>
            <select
              value={selectedSource}
              onChange={(event) => setSelectedSource(event.target.value)}
              disabled={loadingSources}
            >
              {sources.map((source) => (
                <option key={source.name} value={source.name}>
                  {source.name}
                </option>
              ))}
            </select>
          </label>

          <div className="button-row">
            <button className="button button-primary" onClick={() => connect(selectedSource)}>
              Start stream
            </button>
            <button className="button button-secondary" onClick={disconnect}>
              Stop stream
            </button>
          </div>

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
