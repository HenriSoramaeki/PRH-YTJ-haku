"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import api

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    logger.info("Startup complete: %s", settings.app_name)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    logging.getLogger().setLevel(settings.log_level.upper())

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api.router)

    # Yksi osoite selaimelle: tarjoa Vite-build (frontend/dist) jos olemassa
    project_root = Path(__file__).resolve().parent.parent.parent
    dist = project_root / "frontend" / "dist"
    assets_dir = dist / "assets"
    if dist.is_dir() and (dist / "index.html").is_file():
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="ui-assets")

        @app.get("/", include_in_schema=False)
        async def spa_index():
            return FileResponse(dist / "index.html")

        logger.info("Serving UI from %s", dist)
    else:
        logger.warning(
            "No frontend build at %s — run: cd frontend && npm run build",
            dist,
        )

    return app


app = create_app()
