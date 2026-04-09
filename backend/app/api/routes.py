from __future__ import annotations

import re
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect

from backend.app.core.config import get_settings
from backend.app.models.schemas import HealthPayload


router = APIRouter()


@router.get("/health", response_model=HealthPayload)
async def healthcheck() -> HealthPayload:
    settings = get_settings()
    return HealthPayload(
        status="ok",
        app_name=settings.app_name,
        environment=settings.app_env,
    )


@router.get("/api/goal")
async def project_goal():
    return {
        "goal": (
            "Open the browser camera, detect people with YOLO11, track them with DeepSORT, and "
            "return annotated live frames plus stable person IDs to a Railway-hosted dashboard."
        ),
        "pipeline": [
            "Browser camera or uploaded video -> OpenCV preprocessing",
            "YOLO11 person detection -> DeepSORT tracking",
            "Kalman filter motion model + Hungarian assignment -> stable track IDs",
            "FastAPI websocket -> JPEG frame encoder -> React dashboard",
        ],
        "deployment_target": "Railway",
        "important_note": (
            "Railway cannot directly read a user's webcam. The browser must request camera access, "
            "capture frames locally, and stream those frames to the backend over WebSocket."
        ),
    }


@router.get("/api/videos")
async def list_videos(request: Request):
    pipeline = request.app.state.pipeline
    return {"sources": [source.model_dump() for source in pipeline.list_sources()]}


@router.post("/api/videos/upload")
async def upload_video(request: Request, file: UploadFile = File(...)):
    settings = get_settings()
    pipeline = request.app.state.pipeline

    original_name = file.filename or "upload.mp4"
    extension = Path(original_name).suffix.lower()
    if extension not in settings.video_extension_list:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format. Allowed extensions: {', '.join(sorted(settings.video_extension_list))}",
        )

    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(original_name).stem).strip("-._") or "upload"
    target_name = f"{safe_stem}-{uuid4().hex[:8]}{extension}"
    target_path = settings.video_dir / target_name
    settings.video_dir.mkdir(parents=True, exist_ok=True)

    with target_path.open("wb") as destination:
        shutil.copyfileobj(file.file, destination)

    await file.close()

    sources = [source.model_dump() for source in pipeline.list_sources()]
    return {
        "message": f"Uploaded {target_name}",
        "source": {"name": target_name, "source_type": "video"},
        "sources": sources,
    }


@router.websocket("/ws/stream")
async def stream_video(websocket: WebSocket, video: str = "demo://synthetic"):
    await websocket.accept()
    pipeline = websocket.app.state.pipeline

    try:
        async for payload in pipeline.stream(video):
            await websocket.send_json(payload)
    except FileNotFoundError as exc:
        await websocket.send_json({"event": "error", "message": str(exc)})
    except WebSocketDisconnect:
        return
    except Exception as exc:  # pragma: no cover - defensive websocket handling
        await websocket.send_json({"event": "error", "message": f"Unexpected stream error: {exc}"})
    finally:
        await websocket.close()


@router.websocket("/ws/live-camera")
async def stream_live_camera(websocket: WebSocket):
    await websocket.accept()
    pipeline = websocket.app.state.pipeline
    live_session = pipeline.create_live_session()

    try:
        await websocket.send_json(
            {
                "event": "ready",
                "message": "Camera websocket connected. Send JPEG data URLs as frame events.",
            }
        )

        while True:
            payload = await websocket.receive_json()
            event = payload.get("event")

            if event == "frame":
                frame_data = payload.get("frame", "")
                if not frame_data:
                    await websocket.send_json({"event": "error", "message": "Frame payload is empty."})
                    continue
                await websocket.send_json(live_session.process_base64_frame(frame_data, pipeline))
                continue

            if event == "stop":
                await websocket.send_json({"event": "end", "video_name": "browser-camera"})
                break

            await websocket.send_json({"event": "error", "message": f"Unsupported live event: {event}"})
    except WebSocketDisconnect:
        return
    except Exception as exc:  # pragma: no cover - defensive websocket handling
        await websocket.send_json({"event": "error", "message": f"Unexpected live stream error: {exc}"})
    finally:
        await websocket.close()
