# DeepSORT Railway Starter

This project turns your diagram into a deployable starter app:

- Input: local video files or a built-in synthetic demo source
- ML core: OpenCV preprocessing, detector adapter, tracker adapter, track state store
- Server: FastAPI REST + WebSocket streaming
- Client: React dashboard with live frame, track panel, and stats overlay
- Deploy target: Railway using a single Dockerfile

## Final Goal

The final product is a web app that reads uploaded videos, runs per-frame detection, keeps stable object IDs across frames, and streams both the annotated image and tracking metadata to a browser in real time.

That means the full end-to-end flow is:

1. Read 1 to 5 video files from `data/videos/`
2. Extract frames with OpenCV
3. Resize and normalize frames
4. Run object detection
5. Pass detections into a tracker for persistent IDs
6. Store track metadata such as ID, bbox, class, velocity, counts, and FPS
7. Push JPEG frames plus JSON metadata over a FastAPI WebSocket
8. Render the live result in a React dashboard on Railway

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
|       `-- main.py
|-- data/videos/
|-- frontend/
|   |-- package.json
|   |-- vite.config.ts
|   `-- src/
|       |-- components/
|       |-- hooks/useTrackingStream.ts
|       |-- lib/api.ts
|       |-- App.tsx
|       |-- main.tsx
|       |-- styles.css
|       `-- types.ts
|-- .env.example
|-- Dockerfile
|-- railway.json
`-- requirements.txt
```

## What Works Right Now

- FastAPI backend with `/health`, `/api/goal`, `/api/videos`, and `/ws/stream`
- Built-in synthetic source so the app runs even before you upload real videos
- Real video support from `data/videos/`
- Simple persistent-ID tracker that is light enough for Railway
- Optional DeepSORT adapter if you switch `TRACKER_BACKEND=deepsort`
- Optional Ultralytics detector if you install `ultralytics` and set `DETECTOR_BACKEND=ultralytics`
- React dashboard with live canvas, track list, and stats cards
- Single-container Railway deployment

## Local Development

### Backend

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn backend.app.main:app --reload
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173` and proxies to the API at `http://localhost:8000`.

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

## Railway Deployment

1. Push this repo to GitHub.
2. Create a new Railway project from the repo.
3. Railway will detect `Dockerfile` and build the full stack.
4. Set environment variables from `.env.example`.
5. Open the generated Railway URL and start the stream.

For a first Railway deployment, keep:

```env
DETECTOR_BACKEND=mock
TRACKER_BACKEND=simple
```

That keeps startup lighter and avoids downloading heavier ML packages until you are ready.

## Upgrading To Real YOLO + DeepSORT

When you want to move from scaffold mode to real ML inference:

1. Install `ultralytics` and its runtime dependencies.
2. Set `DETECTOR_BACKEND=ultralytics`
3. Set `YOLO_MODEL=yolov8n.pt` or your own weights path
4. Set `TRACKER_BACKEND=deepsort`
5. Add real sample videos to `data/videos/`

## Notes

- This starter is intentionally structured so detector and tracker backends are swappable.
- Railway is a good fit for the dashboard and API layer, but heavy YOLO inference may eventually need a larger instance or a separate GPU-ready service.
