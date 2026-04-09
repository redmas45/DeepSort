import type { Stats } from "../types";

type StatsOverlayProps = {
  stats: Stats | null;
  status: string;
  message: string;
};

export function StatsOverlay({ stats, status, message }: StatsOverlayProps) {
  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Client</p>
          <h2>Stats overlay</h2>
        </div>
        <span className={`status-chip status-${status}`}>{status}</span>
      </div>

      <div className="stats-grid">
        <div className="stat">
          <span>FPS</span>
          <strong>{stats?.fps ?? "--"}</strong>
        </div>
        <div className="stat">
          <span>Objects</span>
          <strong>{stats?.object_count ?? "--"}</strong>
        </div>
        <div className="stat">
          <span>Frame</span>
          <strong>{stats?.frame_index ?? "--"}</strong>
        </div>
      </div>

      <p className="muted">{message}</p>
    </div>
  );
}
