"""FastAPI app: intake -> background pipeline -> SSE progress stream.

Flow:
  POST /api/match/start  {profile}            -> {job_id}
  GET  /api/match/stream/{job_id}  (SSE)      -> stage / tick / done / error events

The pipeline runs as a detached task pushing events into a per-job queue, so a
dropped SSE connection never kills the work, and the terminal `done` event
carries the full results payload (no separate result fetch needed).
"""
from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from . import pipeline
from .config import get_settings
from .models import PatientProfile

app = FastAPI(title="Lifeline API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# job_id -> asyncio.Queue of (event_type, payload) tuples.
_JOBS: dict[str, asyncio.Queue] = {}
_DONE = object()  # sentinel that closes a stream


async def _run_job(job_id: str, profile: PatientProfile) -> None:
    queue = _JOBS[job_id]

    async def emit(event_type: str, payload: dict) -> None:
        await queue.put((event_type, payload))

    try:
        await pipeline.run(profile, emit)
    except Exception as exc:  # noqa: BLE001 - surface as a clean error event
        await queue.put(("error", {"message": f"Matching failed: {exc}"}))
    finally:
        await queue.put((_DONE, None))


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", **get_settings().describe()}


@app.get("/api/config")
async def config() -> dict:
    """Frontend reads this to show the right dashboard banner before a run."""
    s = get_settings()
    return {
        "demo_mode": s.demo_mode,
        "use_flash": s.use_flash,
        "use_claude": s.use_claude,
        "use_live_ingest": s.use_live_ingest,
        "max_workers": s.max_workers,
        "gpu_cost_per_second": s.gpu_cost_per_second,
    }


@app.post("/api/match/start")
async def start_match(profile: PatientProfile) -> dict:
    if not profile.condition or not profile.condition.strip():
        raise HTTPException(status_code=422, detail="A condition is required.")
    job_id = uuid.uuid4().hex
    _JOBS[job_id] = asyncio.Queue()
    asyncio.create_task(_run_job(job_id, profile))
    return {"job_id": job_id}


@app.get("/api/match/stream/{job_id}")
async def stream_match(job_id: str):
    queue = _JOBS.get(job_id)
    if queue is None:
        raise HTTPException(status_code=404, detail="Unknown or expired job.")

    async def event_gen():
        try:
            while True:
                event_type, payload = await queue.get()
                if event_type is _DONE:
                    break
                yield {"event": event_type, "data": json.dumps(payload)}
        finally:
            _JOBS.pop(job_id, None)

    return EventSourceResponse(event_gen())
