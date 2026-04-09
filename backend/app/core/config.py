from functools import lru_cache
from pathlib import Path
from typing import Optional

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
    camera_capture_fps: int = 4
    camera_max_width: int = 960
    camera_jpeg_quality: float = 0.85
    jpeg_quality: int = 82
    detector_backend: str = "ultralytics"
    yolo_model: str = "yolo11_model/yolo11m.pt"
    model_device: str = "cpu"
    confidence_threshold: float = 0.6
    iou_threshold: float = 0.45
    
    # --- ADDED: DETECTOR FILTERS ---
    min_detection_area: int = 2000
    min_detection_height: int = 80
    max_detection_width_height_ratio: float = 1.5

    tracker_backend: str = "deepsort"
    max_track_age: int = 30
    
    # --- ADDED: DEEPSORT TRACKER SETTINGS ---
    tracker_n_init: int = 3
    tracker_max_iou_distance: float = 0.7
    tracker_max_cosine_distance: float = 0.2
    tracker_nn_budget: int = 100
    tracker_embedder: str = "mobilenet"
    tracker_embedder_model_name: Optional[str] = None
    tracker_embedder_weights: Optional[str] = None
    tracker_use_half: bool = False

    match_distance_threshold: float = 120.0
    tracked_class_names: str = "person"
    allowed_video_extensions: str = ".mp4,.avi,.mov,.mkv"

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
        configured_path = Path(self.video_source_dir)
        if configured_path.is_absolute():
            return configured_path
        return ROOT_DIR / configured_path

    @property
    def frontend_dist_dir(self) -> Path:
        return ROOT_DIR / "frontend" / "dist"

    @property
    def root_static_dir(self) -> Path:
        return ROOT_DIR / "backend" / "app" / "static"

    @property
    def tracked_class_name_list(self) -> list[str]:
        return [class_name.strip().lower() for class_name in self.tracked_class_names.split(",") if class_name.strip()]

    @property
    def video_extension_list(self) -> set[str]:
        return {extension.strip().lower() for extension in self.allowed_video_extensions.split(",") if extension.strip()}

    @property
    def resolved_yolo_model(self) -> str:
        configured_path = Path(self.yolo_model)
        if configured_path.is_absolute():
            return str(configured_path)

        relative_path = ROOT_DIR / configured_path
        if relative_path.exists():
            return str(relative_path)

        return self.yolo_model


@lru_cache
def get_settings() -> Settings:
    return Settings()