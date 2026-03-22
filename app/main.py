"""FastAPI application entry point — The Unified Service Scheduler."""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.database import engine, Base, SessionLocal
from app.routes import router as api_router
from app.seed import seed_database


# ── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="The Unified Service Scheduler",
    description=(
        "Keyloop Technical Assessment — Scenario A. "
        "Resource-constrained appointment booking with real-time "
        "availability checks and Redis distributed locking."
    ),
    version="1.0.0",
)

# Include API routes
app.include_router(api_router)

# ── Template serving for the test harness ────────────────────────────────────
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.on_event("startup")
def on_startup():
    """Create tables and seed data on startup (skipped during tests)."""
    if os.getenv("TESTING") == "1":
        return
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def serve_test_harness(request: Request):
    """Serve the client-side test harness (simple HTML/JS form)."""
    return templates.TemplateResponse("index.html", {"request": request})


# ── Health endpoints ─────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
def liveness():
    return {"status": "ok"}
