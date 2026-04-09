from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class TrackPayload(BaseModel):
    track_id: int
    class_name: str
    confidence: float
    bbox: BoundingBox
    velocity_px: tuple[float, float] = Field(default=(0.0, 0.0))


class StatsPayload(BaseModel):
    frame_index: int
    fps: float
    object_count: int
    active_track_ids: list[int]
    raw_detection_count: int = 0
    filtered_detection_count: int = 0
    total_unique_tracks: int = 0
    processing_ms: float = 0.0
    detection_ms: float = 0.0
    tracking_ms: float = 0.0
    encode_ms: float = 0.0


class StreamPayload(BaseModel):
    event: str = "frame"
    video_name: str
    frame: str
    tracks: list[TrackPayload]
    stats: StatsPayload


class VideoSourcePayload(BaseModel):
    name: str
    source_type: str


class HealthPayload(BaseModel):
    status: str
    app_name: str
    environment: str
