from __future__ import annotations

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

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
            "Stream uploaded videos through a tracking pipeline, detect objects, keep stable IDs "
            "across frames, and expose frames plus metadata to a live React dashboard."
        ),
        "pipeline": [
            "Video source -> OpenCV reader -> frame preprocessing",
            "Detector adapter -> tracker adapter -> track state store",
            "FastAPI websocket -> JPEG frame encoder -> React dashboard",
        ],
        "deployment_target": "Railway",
    }


@router.get("/api/videos")
async def list_videos(request: Request):
    pipeline = request.app.state.pipeline
    return {"sources": [source.model_dump() for source in pipeline.list_sources()]}


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
