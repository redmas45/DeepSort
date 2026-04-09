# DeepSORT Railway Starter

This project turns your diagram into a deployable inference app:

- Input: browser camera, bundled demo videos, or user-uploaded videos
- ML core: OpenCV preprocessing, YOLO11m person detection, DeepSORT tracking, track state store
- Server: FastAPI REST + WebSocket streaming
- Client: plain HTML, CSS, and JavaScript served directly by FastAPI
- Deploy target: Railway using a single Dockerfile

## Final Goal

The final product is a web app that asks for browser camera access, streams frames to FastAPI, runs YOLO11m person detection plus DeepSORT tracking, and sends annotated frames back with stable person IDs in real time.

That means the full end-to-end flow is:

1. Request webcam access in the browser
2. Capture live frames in the browser client
3. Stream those frames to FastAPI over WebSocket
4. Resize and normalize frames with OpenCV
5. Detect only `person` objects with YOLO11
6. Track those detections with DeepSORT using Kalman filtering and Hungarian matching
7. Store track metadata such as ID, bbox, class, velocity, counts, and FPS
8. Push annotated JPEG frames plus JSON metadata back to the browser
9. Allow users to upload an unknown video and run the same detection-and-tracking pipeline on it

## Project Structure

```text
.
|-- backend/
|   `-- app/
|       |-- api/routes.py
|       |-- core/config.py
|       |-- models/schemas.py
|       |-- services/detector.py
|       |-- services/encoder.py
|       |-- services/pipeline.py
|       |-- services/tracker.py
|       |-- static/app.js
|       |-- static/index.html
|       |-- static/styles.css
|       `-- main.py
|-- data/videos/
|-- .env.example
|-- Dockerfile
|-- local.py
|-- railway.json
|-- requirements-ml.txt
`-- requirements.txt
```

## What Works Right Now

- FastAPI backend with `/health`, `/api/goal`, `/api/videos`, `/api/videos/upload`, and `/ws/stream`
- Live camera ingestion with `/ws/live-camera`
- Built-in synthetic source so the app runs even before you upload real videos
- Real video support from `data/videos/` and uploaded files
- DeepSORT tracker path is available and configured as the target default
- YOLO11m-compatible Ultralytics detector path is wired in for `person` tracking
- Plain HTML/CSS/JS dashboard supports both live camera mode and uploaded-video mode
- Single-container Railway deployment

## Local Development

### Backend

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-ml.txt
Copy-Item .env.example .env
uvicorn backend.app.main:app --reload
```

### All-In-One Local Run

```powershell
python local.py
```

That starts FastAPI and serves the built-in frontend from the same app on `http://127.0.0.1:8000`.

## Live Camera Architecture

Important deployment detail:

- Railway cannot directly access a user webcam.
- The browser must request camera permission with `getUserMedia`.
- The browser captures frames and sends them to FastAPI over WebSocket.
- FastAPI runs YOLO11 + DeepSORT and sends the annotated result back.

That is now the architecture implemented in this starter, and the local frontend is plain HTML/CSS/JS so no Node build is required.

## Add Your Own Videos

Put your files inside:

```text
data/videos/
```

Supported extensions in this starter:

- `.mp4`
- `.avi`
- `.mov`
- `.mkv`

The app also lets a user upload a new video from the browser and then stream that file through the same backend.

## Railway Deployment

1. Push this repo to GitHub.
2. Create a new Railway project from the repo.
3. Railway will detect `Dockerfile` and build the full stack.
4. Set environment variables from `.env.example`.
5. Open the generated Railway URL and start the stream.

Recommended production env:

```env
DETECTOR_BACKEND=ultralytics
YOLO_MODEL=yolo11_model/yolo11m.pt
MODEL_DEVICE=cpu
TRACKER_BACKEND=deepsort
TRACKED_CLASS_NAMES=person
```

The Docker image now copies `yolo11_model/` into the container, so the bundled `yolo11m.pt` can be used directly instead of retraining a model.

If Railway startup time becomes too heavy on CPU, temporarily switch `DETECTOR_BACKEND=mock` while you finish the UI and transport layer.

## Detector Roadmap

Current build direction:

1. YOLO11m for the first real-time version
2. DeepSORT for stable identities
3. Faster R-CNN later for comparison and benchmarking against YOLO11

## Notes

- This starter is intentionally structured so detector and tracker backends are swappable.
- Railway is a good fit for the dashboard and API layer, but sustained CPU-only YOLO11m inference may eventually need a larger instance or a separate GPU-ready inference service.
- Uploaded videos are stored on the app filesystem, so for long-term production retention you would eventually move those files to object storage.
