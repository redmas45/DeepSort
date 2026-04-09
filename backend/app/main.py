from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes import router
from backend.app.core.config import get_settings
from backend.app.services.pipeline import TrackingPipeline


settings = get_settings()
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


frontend_dist = settings.frontend_dist_dir
frontend_index = frontend_dist / "index.html"
frontend_assets = frontend_dist / "assets"

if frontend_assets.exists():
    app.mount("/assets", StaticFiles(directory=frontend_assets), name="assets")

if frontend_dist.exists() and frontend_index.exists():

    @app.get("/")
    async def root():
        return FileResponse(frontend_index)

else:

    @app.get("/")
    async def root():
        return JSONResponse(
            {
                "message": "DeepSORT Railway Starter backend is running.",
                "next_step": "Build the frontend or hit /api/videos and /ws/stream.",
            }
        )
