from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np

from backend.app.core.config import Settings
from backend.app.services.detector import Detection


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TrackedObject:
    track_id: int
    bbox: tuple[float, float, float, float]
    class_name: str
    confidence: float
    velocity_px: tuple[float, float]


class BaseTracker:
    def update(self, detections: list[Detection], frame: np.ndarray) -> list[TrackedObject]:
        raise NotImplementedError


class SimpleTrackerBackend(BaseTracker):
    """A lightweight ID persistence tracker that is cheap to run on Railway."""

    def __init__(self, settings: Settings) -> None:
        self.max_track_age = settings.max_track_age
        self.match_distance_threshold = settings.match_distance_threshold
        self.next_track_id = 1
        self.track_store: dict[int, dict[str, object]] = {}

    def update(self, detections: list[Detection], frame: np.ndarray) -> list[TrackedObject]:
        unmatched_track_ids = set(self.track_store.keys())
        results: list[TrackedObject] = []

        for detection in detections:
            best_track_id = None
            best_distance = math.inf
            detection_center = self._center(detection.bbox)

            for track_id in list(unmatched_track_ids):
                track = self.track_store[track_id]
                previous_center = track["center"]
                distance = math.dist(detection_center, previous_center)
                if distance < best_distance and distance <= self.match_distance_threshold:
                    best_distance = distance
                    best_track_id = track_id

            if best_track_id is None:
                best_track_id = self.next_track_id
                self.next_track_id += 1
                previous_center = detection_center
            else:
                unmatched_track_ids.discard(best_track_id)
                previous_center = self.track_store[best_track_id]["center"]

            velocity = (
                float(detection_center[0] - previous_center[0]),
                float(detection_center[1] - previous_center[1]),
            )
            self.track_store[best_track_id] = {
                "bbox": detection.bbox,
                "center": detection_center,
                "age": 0,
                "class_name": detection.class_name,
                "confidence": detection.confidence,
            }
            results.append(
                TrackedObject(
                    track_id=best_track_id,
                    bbox=detection.bbox,
                    class_name=detection.class_name,
                    confidence=detection.confidence,
                    velocity_px=velocity,
                )
            )

        for track_id in list(unmatched_track_ids):
            track = self.track_store[track_id]
            track["age"] = int(track["age"]) + 1
            if int(track["age"]) > self.max_track_age:
                del self.track_store[track_id]

        return results

    @staticmethod
    def _center(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


class DeepSortTrackerBackend(BaseTracker):
    def __init__(self, settings: Settings) -> None:
        from deep_sort_realtime.deepsort_tracker import DeepSort

        self.tracker = DeepSort(max_age=settings.max_track_age, embedder_gpu=False)
        self.previous_centers: dict[int, tuple[float, float]] = {}

    def update(self, detections: list[Detection], frame: np.ndarray) -> list[TrackedObject]:
        bounding_boxes = []
        for detection in detections:
            x1, y1, x2, y2 = detection.bbox
            bounding_boxes.append(([x1, y1, x2 - x1, y2 - y1], detection.confidence, detection.class_name))

        results: list[TrackedObject] = []
        for track in self.tracker.update_tracks(bounding_boxes, frame=frame):
            if not track.is_confirmed():
                continue

            track_id = int(track.track_id)
            x1, y1, x2, y2 = track.to_ltrb()
            center = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
            previous_center = self.previous_centers.get(track_id, center)
            self.previous_centers[track_id] = center

            results.append(
                TrackedObject(
                    track_id=track_id,
                    bbox=(float(x1), float(y1), float(x2), float(y2)),
                    class_name=str(getattr(track, "det_class", "object") or "object"),
                    confidence=float(getattr(track, "det_conf", 0.0) or 0.0),
                    velocity_px=(float(center[0] - previous_center[0]), float(center[1] - previous_center[1])),
                )
            )
        return results


def build_tracker(settings: Settings) -> BaseTracker:
    if settings.tracker_backend.lower() != "deepsort":
        return SimpleTrackerBackend(settings)

    try:
        return DeepSortTrackerBackend(settings)
    except Exception as exc:  # pragma: no cover - runtime dependency fallback
        logger.warning(
            "DeepSORT tracker unavailable, falling back to simple tracker: %s",
            exc,
        )
        return SimpleTrackerBackend(settings)
