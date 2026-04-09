from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "DeepSORT Railway Starter"
    app_env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    video_source_dir: str = "data/videos"
    frame_width: int = 960
    frame_height: int = 540
    stream_fps: int = 10
    jpeg_quality: int = 80
    detector_backend: str = "ultralytics"
    yolo_model: str = "yolo11n.pt"
    confidence_threshold: float = 0.35
    iou_threshold: float = 0.45
    tracker_backend: str = "deepsort"
    max_track_age: int = 30
    match_distance_threshold: float = 120.0
    tracked_class_names: str = "person"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def video_dir(self) -> Path:
        return ROOT_DIR / self.video_source_dir

    @property
    def frontend_dist_dir(self) -> Path:
        return ROOT_DIR / "frontend" / "dist"

    @property
    def tracked_class_name_list(self) -> list[str]:
        return [class_name.strip().lower() for class_name in self.tracked_class_names.split(",") if class_name.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
