from __future__ import annotations

from fastapi import APIRouter, FastAPI

jobs_router = APIRouter(tags=["jobs"])
ingest_router = APIRouter(tags=["ingest"])
review_router = APIRouter(tags=["review"])
exports_router = APIRouter(tags=["exports"])
queue_router = APIRouter(tags=["queue"])
presets_router = APIRouter(tags=["presets"])
portfolio_router = APIRouter(tags=["portfolio"])
system_router = APIRouter(tags=["system"])


def include_api_routers(app: FastAPI) -> None:
    app.include_router(jobs_router)
    app.include_router(ingest_router)
    app.include_router(review_router)
    app.include_router(exports_router)
    app.include_router(queue_router)
    app.include_router(presets_router)
    app.include_router(portfolio_router)
    app.include_router(system_router)
