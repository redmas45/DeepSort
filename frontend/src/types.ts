export type VideoSource = {
  name: string;
  source_type: string;
};

export type BoundingBox = {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
};

export type Track = {
  track_id: number;
  class_name: string;
  confidence: number;
  bbox: BoundingBox;
  velocity_px: [number, number];
};

export type Stats = {
  frame_index: number;
  fps: number;
  object_count: number;
  active_track_ids: number[];
};

export type StreamFrameMessage = {
  event: "frame";
  video_name: string;
  frame: string;
  tracks: Track[];
  stats: Stats;
};

export type StreamInfoMessage = {
  event: "end" | "error";
  video_name?: string;
  message?: string;
};
