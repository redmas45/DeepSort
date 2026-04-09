from __future__ import annotations

import asyncio
import time
from pathlib import Path

import cv2
import numpy as np

from backend.app.core.config import Settings
from backend.app.models.schemas import StatsPayload, StreamPayload, VideoSourcePayload
from backend.app.services.detector import build_detector
from backend.app.services.encoder import (
    annotate_frame,
    decode_frame_from_base64,
    encode_frame_to_base64,
    to_track_payloads,
)
from backend.app.services.tracker import build_tracker


class LiveTrackingSession:
    def __init__(self, settings: Settings, source_name: str = "browser-camera") -> None:
        self.settings = settings
        self.source_name = source_name
        self.detector = build_detector(settings)
        self.tracker = build_tracker(settings)
        self.frame_index = 0
        self.last_tick = time.perf_counter()

    def process_base64_frame(self, frame_data: str, pipeline: "TrackingPipeline") -> dict:
        frame = decode_frame_from_base64(frame_data)
        payload = pipeline.build_frame_payload(
            source_name=self.source_name,
            frame=frame,
            frame_index=self.frame_index,
            detector=self.detector,
            tracker=self.tracker,
            last_tick=self.last_tick,
        )
        self.frame_index += 1
        self.last_tick = time.perf_counter()
        return payload


class TrackingPipeline:
    DEMO_SOURCE = "demo://synthetic"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.video_dir.mkdir(parents=True, exist_ok=True)

    def list_sources(self) -> list[VideoSourcePayload]:
        sources = [VideoSourcePayload(name=self.DEMO_SOURCE, source_type="synthetic")]
        extensions = {".mp4", ".avi", ".mov", ".mkv"}
        for path in sorted(self.settings.video_dir.iterdir()):
            if path.is_file() and path.suffix.lower() in extensions:
                sources.append(VideoSourcePayload(name=path.name, source_type="video"))
        return sources

    async def stream(self, source_name: str):
        if source_name == self.DEMO_SOURCE:
            async for payload in self._stream_synthetic():
                yield payload
            return

        source_path = self.settings.video_dir / source_name
        if not source_path.exists():
            raise FileNotFoundError(f"Video source '{source_name}' not found in {self.settings.video_dir}")

        async for payload in self._stream_video(source_path):
            yield payload

    async def _stream_video(self, source_path: Path):
        detector = build_detector(self.settings)
        tracker = build_tracker(self.settings)
        capture = cv2.VideoCapture(str(source_path))

        if not capture.isOpened():
            raise RuntimeError(f"Unable to open video file: {source_path}")

        frame_index = 0
        last_tick = time.perf_counter()

        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break

                payload = self.build_frame_payload(
                    source_name=source_path.name,
                    frame=frame,
                    frame_index=frame_index,
                    detector=detector,
                    tracker=tracker,
                    last_tick=last_tick,
                )
                last_tick = time.perf_counter()
                yield payload

                frame_index += 1
                await asyncio.sleep(1 / max(self.settings.stream_fps, 1))
        finally:
            capture.release()

        yield {"event": "end", "video_name": source_path.name}

    async def _stream_synthetic(self):
        detector = build_detector(self.settings)
        tracker = build_tracker(self.settings)
        frame_index = 0
        last_tick = time.perf_counter()

        while True:
            frame = self._generate_synthetic_frame(frame_index)
            payload = self.build_frame_payload(
                source_name=self.DEMO_SOURCE,
                frame=frame,
                frame_index=frame_index,
                detector=detector,
                tracker=tracker,
                last_tick=last_tick,
            )
            last_tick = time.perf_counter()
            yield payload

            frame_index += 1
            await asyncio.sleep(1 / max(self.settings.stream_fps, 1))

    def create_live_session(self, source_name: str = "browser-camera") -> LiveTrackingSession:
        return LiveTrackingSession(self.settings, source_name=source_name)

    def build_frame_payload(self, source_name: str, frame: np.ndarray, frame_index: int, detector, tracker, last_tick: float) -> dict:
        preprocessed = self._preprocess(frame)
        detections = detector.detect(preprocessed, frame_index)
        tracked = tracker.update(detections, preprocessed)
        tracks = to_track_payloads(
            [
                (track.track_id, track.bbox, track.class_name, track.confidence, track.velocity_px)
                for track in tracked
            ]
        )
        annotated = annotate_frame(preprocessed, tracks)
        encoded_frame = encode_frame_to_base64(annotated, self.settings.jpeg_quality)
        now = time.perf_counter()
        fps = 1.0 / max(now - last_tick, 1e-6)
        stats = StatsPayload(
            frame_index=frame_index,
            fps=round(fps, 2),
            object_count=len(tracks),
            active_track_ids=[track.track_id for track in tracks],
        )

        payload = StreamPayload(
            event="frame",
            video_name=source_name,
            frame=encoded_frame,
            tracks=tracks,
            stats=stats,
        )
        return payload.model_dump()

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        resized = cv2.resize(frame, (self.settings.frame_width, self.settings.frame_height))
        normalized = cv2.convertScaleAbs(resized, alpha=1.0, beta=0.0)
        return normalized

    def _generate_synthetic_frame(self, frame_index: int) -> np.ndarray:
        width = self.settings.frame_width
        height = self.settings.frame_height
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :] = (18, 24, 36)

        for column in range(0, width, 80):
            cv2.line(frame, (column, 0), (column, height), (32, 44, 68), 1)
        for row in range(0, height, 80):
            cv2.line(frame, (0, row), (width, row), (32, 44, 68), 1)

        pulse = int(30 + 20 * np.sin(frame_index / 8))
        cv2.rectangle(frame, (30, 30), (width - 30, height - 30), (70, 120 + pulse, 180), 2)
        cv2.putText(
            frame,
            "DeepSORT Railway Starter",
            (40, 58),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (220, 235, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            "Synthetic demo source active",
            (40, 98),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (166, 190, 240),
            2,
            cv2.LINE_AA,
        )
        return frame
