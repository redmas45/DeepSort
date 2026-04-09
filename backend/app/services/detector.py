from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from backend.app.core.config import Settings


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Detection:
    bbox: tuple[float, float, float, float]
    confidence: float
    class_name: str
    class_id: int = 0


class BaseDetector:
    def detect(self, frame: np.ndarray, frame_index: int) -> list[Detection]:
        raise NotImplementedError

    def get_runtime_metrics(self) -> dict[str, int]:
        return {
            "raw_detection_count": 0,
            "filtered_detection_count": 0,
        }


class MockDetector(BaseDetector):
    def __init__(self) -> None:
        self.last_raw_detection_count = 0
        self.last_filtered_detection_count = 0

    def detect(self, frame: np.ndarray, frame_index: int) -> list[Detection]:
        height, width = frame.shape[:2]
        box_width = max(width // 8, 90)
        box_height = max(height // 4, 120)

        detections: list[Detection] = []
        for idx in range(3):
            x1 = (frame_index * (18 + idx * 6) + 80 + idx * 170) % max(width - box_width - 1, 1)
            y1 = 60 + idx * 110 + ((frame_index * (7 + idx)) % 35)
            x2 = min(x1 + box_width, width - 1)
            y2 = min(y1 + box_height, height - 1)
            detections.append(
                Detection(
                    bbox=(float(x1), float(y1), float(x2), float(y2)),
                    confidence=0.88 - idx * 0.08,
                    class_name="person",
                    class_id=0,
                )
            )

        self.last_raw_detection_count = len(detections)
        self.last_filtered_detection_count = len(detections)
        return detections

    def get_runtime_metrics(self) -> dict[str, int]:
        return {
            "raw_detection_count": self.last_raw_detection_count,
            "filtered_detection_count": self.last_filtered_detection_count,
        }


class UltralyticsDetector(BaseDetector):
    def __init__(self, settings: Settings) -> None:
        from ultralytics import YOLO

        self.model = YOLO(settings.resolved_yolo_model)
        self.model_device = settings.model_device
        self.confidence_threshold = settings.confidence_threshold
        self.iou_threshold = settings.iou_threshold
        self.tracked_class_names = set(settings.tracked_class_name_list)
        self.allowed_class_ids = [0] if self.tracked_class_names == {"person"} else None
        self.min_detection_area = settings.min_detection_area
        self.min_detection_height = settings.min_detection_height
        self.max_detection_width_height_ratio = settings.max_detection_width_height_ratio
        self.last_raw_detection_count = 0
        self.last_filtered_detection_count = 0

    def detect(self, frame: np.ndarray, frame_index: int) -> list[Detection]:
        results = self.model.predict(
            source=frame,
            verbose=False,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            device=self.model_device,
            classes=self.allowed_class_ids,
        )

        detections: list[Detection] = []
        raw_detection_count = 0

        for result in results:
            names = result.names
            for box in result.boxes:
                raw_detection_count += 1

                x1, y1, x2, y2 = box.xyxy[0].tolist()
                confidence = float(box.conf[0].item())
                class_id = int(box.cls[0].item())
                class_name = str(names.get(class_id, class_id))

                if self.tracked_class_names and class_name.lower() not in self.tracked_class_names:
                    continue

                if not self._passes_bbox_filters(x1, y1, x2, y2):
                    continue

                detections.append(
                    Detection(
                        bbox=(x1, y1, x2, y2),
                        confidence=confidence,
                        class_name=class_name,
                        class_id=class_id,
                    )
                )

        # 🔥 NEW: REMOVE DUPLICATE OVERLAPPING DETECTIONS
        detections = self._remove_duplicate_detections(detections)

        self.last_raw_detection_count = raw_detection_count
        self.last_filtered_detection_count = len(detections)

        return detections

    def _passes_bbox_filters(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        width = max(x2 - x1, 0.0)
        height = max(y2 - y1, 0.0)
        area = width * height

        if area < self.min_detection_area:
            return False
        if height < self.min_detection_height:
            return False
        if height <= 0:
            return False
        if width / height > self.max_detection_width_height_ratio:
            return False

        return True

    # 🔥 CORE FIX FUNCTION
    def _remove_duplicate_detections(self, detections: list[Detection]) -> list[Detection]:
        if not detections:
            return detections

        filtered = []

        for i, det1 in enumerate(detections):
            x1, y1, x2, y2 = det1.bbox
            area1 = (x2 - x1) * (y2 - y1)

            keep = True

            for j, det2 in enumerate(detections):
                if i == j:
                    continue

                xx1, yy1, xx2, yy2 = det2.bbox
                area2 = (xx2 - xx1) * (yy2 - yy1)

                # Compute IoU
                inter_x1 = max(x1, xx1)
                inter_y1 = max(y1, yy1)
                inter_x2 = min(x2, xx2)
                inter_y2 = min(y2, yy2)

                inter_area = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
                union_area = area1 + area2 - inter_area

                iou = inter_area / union_area if union_area > 0 else 0

                # Remove weaker overlapping box
                if iou > 0.7 and det1.confidence < det2.confidence:
                    keep = False
                    break

            if keep:
                filtered.append(det1)

        return filtered

    def get_runtime_metrics(self) -> dict[str, int]:
        return {
            "raw_detection_count": self.last_raw_detection_count,
            "filtered_detection_count": self.last_filtered_detection_count,
        }


def build_detector(settings: Settings) -> BaseDetector:
    if settings.detector_backend.lower() != "ultralytics":
        return MockDetector()

    try:
        return UltralyticsDetector(settings)
    except Exception as exc:
        logger.warning(
            "Ultralytics detector unavailable, falling back to mock detector: %s",
            exc,
        )
        return MockDetector()