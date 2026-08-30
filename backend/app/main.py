import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .models import DashboardSnapshot

DATA_PATH = Path(__file__).parent.parent / "data" / "dashboard.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.snapshot = DashboardSnapshot.model_validate_json(DATA_PATH.read_text())
    except Exception as exc:
        raise RuntimeError(f"Invalid or missing dashboard snapshot at {DATA_PATH}: {exc}") from exc
    yield


app = FastAPI(title="PostHog Engineering Impact API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dashboard", response_model=DashboardSnapshot)
def dashboard(request: Request) -> DashboardSnapshot:
    return request.app.state.snapshot

