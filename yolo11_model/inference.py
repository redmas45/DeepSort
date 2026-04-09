from pathlib import Path

import cv2
from ultralytics import YOLO

try:
    import torch
except ImportError:  # pragma: no cover - local helper script fallback
    torch = None


MODEL_PATH = Path(__file__).with_name("yolo11m.pt")
MODEL_DEVICE = 0 if torch and torch.cuda.is_available() else "cpu"

model = YOLO(str(MODEL_PATH))
cap = cv2.VideoCapture(0)

while cap.isOpened():
    ok, frame = cap.read()
    if not ok:
        break

    results = model.predict(
        source=frame,
        conf=0.4,
        iou=0.5,
        device=MODEL_DEVICE,
        verbose=False,
        classes=[0],
    )

    annotated_frame = results[0].plot()
    display = cv2.resize(annotated_frame, (1280, 720))
    cv2.imshow("YOLO11m Person Detection", display)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
