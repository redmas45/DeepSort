from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes import router
from backend.app.core.config import get_settings
from backend.app.services.pipeline import TrackingPipeline


settings = get_settings()
print("RAW:", raw_detection_count)
print("AFTER FILTER:", len(detections))
app = FastAPI(title=settings.app_name)
app.state.pipeline = TrackingPipeline(settings)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


static_dir = settings.root_static_dir
static_index = static_dir / "index.html"

app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    return FileResponse(static_index)
