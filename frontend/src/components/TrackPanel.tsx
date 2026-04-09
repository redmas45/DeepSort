import type { Track } from "../types";

type TrackPanelProps = {
  tracks: Track[];
};

export function TrackPanel({ tracks }: TrackPanelProps) {
  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Client</p>
          <h2>Track panel</h2>
        </div>
        <span className="pill">{tracks.length} active</span>
      </div>

      <div className="track-list">
        {tracks.length === 0 ? (
          <p className="muted">No active tracks yet.</p>
        ) : (
          tracks.map((track) => (
            <article className="track-card" key={track.track_id}>
              <div className="track-card-row">
                <strong>ID {track.track_id}</strong>
                <span>{track.class_name}</span>
              </div>
              <div className="track-card-row">
                <span>confidence {track.confidence.toFixed(2)}</span>
                <span>
                  velocity {track.velocity_px[0].toFixed(1)}, {track.velocity_px[1].toFixed(1)}
                </span>
              </div>
            </article>
          ))
        )}
      </div>
    </div>
  );
}
