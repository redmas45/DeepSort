from __future__ import annotations

import base64

import cv2
import numpy as np

from backend.app.models.schemas import BoundingBox, TrackPayload


def annotate_frame(frame: np.ndarray, tracks: list[TrackPayload]) -> np.ndarray:
    annotated = frame.copy()
    for track in tracks:
        x1 = int(track.bbox.x1)
        y1 = int(track.bbox.y1)
        x2 = int(track.bbox.x2)
        y2 = int(track.bbox.y2)
        color = (70 + (track.track_id * 30) % 185, 180, 255 - (track.track_id * 40) % 180)

        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            annotated,
            f"ID {track.track_id} | {track.class_name}",
            (x1, max(y1 - 10, 24)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
            cv2.LINE_AA,
        )
    return annotated


def encode_frame_to_base64(frame: np.ndarray, jpeg_quality: int) -> str:
    success, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])
    if not success:
        raise RuntimeError("Unable to encode frame as JPEG")
    return base64.b64encode(buffer.tobytes()).decode("utf-8")


def to_track_payloads(tracks: list[tuple[int, tuple[float, float, float, float], str, float, tuple[float, float]]]) -> list[TrackPayload]:
    payloads: list[TrackPayload] = []
    for track_id, bbox, class_name, confidence, velocity in tracks:
        payloads.append(
            TrackPayload(
                track_id=track_id,
                class_name=class_name,
                confidence=round(confidence, 3),
                bbox=BoundingBox(x1=bbox[0], y1=bbox[1], x2=bbox[2], y2=bbox[3]),
                velocity_px=(round(velocity[0], 2), round(velocity[1], 2)),
            )
        )
    return payloads
