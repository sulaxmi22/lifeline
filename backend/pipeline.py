"""Pipeline orchestrator: ingest -> embed -> retrieve -> rerank -> reason.

Emits SSE events through an async `emit(event_type, payload)` callback so the
frontend dashboard can animate each stage live. Two telemetry mechanisms:
  * flash_live  -> a background sampler streams REAL worker counts.
  * demo/local  -> a labeled, representative simulated burst (honest: mode is
                   stamped 'demo_simulated' / 'local_cpu').
"""
from __future__ import annotations

import asyncio
import math
import time
from typing import Awaitable, Callable

from . import flash_embed
from .config import get_settings
from .eligibility import reason_batch
from .embedding_index import tfidf_search, vector_search
from .flash_embed import embed_texts
from .flash_rerank import rerank
from .ingest import get_trials
from .metrics import ComputeTracker
from .models import MatchedTrial, PatientProfile, TrialLocation

Emit = Callable[[str, dict], Awaitable[None]]

_VERDICT_RANK = {"likely_eligible": 0, "possibly_eligible": 1, "likely_ineligible": 2}


# --------------------------------------------------------------------------
# Telemetry helpers
# --------------------------------------------------------------------------
async def _live_sampler(tracker: ComputeTracker, emit: Emit) -> None:
    """Stream real worker counts while Flash batches are in flight."""
    try:
        while True:
            tick = tracker.add_tick()
            await emit("tick", _tick_payload(tracker, tick))
            await asyncio.sleep(0.15)
    except asyncio.CancelledError:
        return


def _tick_payload(tracker: ComputeTracker, tick: dict) -> dict:
    return {
        "t": tick["t"],
        "workers": tick["workers"],
        "peak_workers": tracker.peak_workers,
        "trials_processed": tracker.trials_processed,
        "gpu_seconds_est": round(tracker.gpu_seconds, 2),
        "cost_est": round(tracker.gpu_seconds * tracker.gpu_cost_per_second, 6),
        "elapsed": round(tracker.elapsed(), 2),
    }


async def _simulate_burst(
    tracker: ComputeTracker, emit: Emit, n_trials: int
) -> None:
    """Representative GPU-burst animation for the demo/local path (labeled)."""
    max_w = tracker.max_workers
    tracker.batch_count = max(1, math.ceil(n_trials / get_settings().embed_batch_size))
    # Duration scales gently with corpus size, bounded for a snappy demo.
    duration = min(7.0, max(4.0, n_trials / 250.0))
    # A short ramp + long plateau + short taper -> a high, believable utilization.
    ramp, plateau = duration * 0.15, duration * 0.7
    dt = 0.15
    steps = int(duration / dt)

    for i in range(steps + 1):
        elapsed = i * dt
        if elapsed < ramp:
            workers = max_w * (elapsed / ramp)
        elif elapsed < ramp + plateau:
            workers = max_w
        else:
            frac = (elapsed - ramp - plateau) / max(duration - ramp - plateau, 1e-6)
            workers = max_w * max(0.0, 1.0 - frac)
        w = int(round(workers))
        tracker.record_sim_seconds(w, dt)
        # Advance trials_processed proportionally to the burst progress.
        tracker.trials_processed = min(n_trials, int(n_trials * (i / max(steps, 1))))
        tick = {"t": round(elapsed, 2), "workers": w}
        tracker.timeline.append(tick)
        await emit("tick", _tick_payload(tracker, tick))
        await asyncio.sleep(dt)

    tracker.trials_processed = n_trials
    final = {"t": round(duration, 2), "workers": 0}
    tracker.timeline.append(final)
    await emit("tick", _tick_payload(tracker, final))


def _nearest_location(trial, profile: PatientProfile) -> TrialLocation | None:
    if not trial.locations:
        return None
    if profile.location:
        needle = profile.location.lower()
        for loc in trial.locations:
            hay = " ".join(filter(None, [loc.city, loc.state, loc.country])).lower()
            if any(tok in hay for tok in needle.replace(",", " ").split()):
                return loc
    return trial.locations[0]


# --------------------------------------------------------------------------
# Main entrypoint
# --------------------------------------------------------------------------
async def run(profile: PatientProfile, emit: Emit) -> None:
    settings = get_settings()
    tracker = ComputeTracker(settings)
    tracker.reset_clock()

    # 1) INGEST -----------------------------------------------------------
    await emit("stage", {"stage": "ingest", "status": "active", "detail": "Searching ClinicalTrials.gov…"})
    trials, total, source = await get_trials(profile.condition, profile.location)
    tracker.trials_total = total
    await emit("stage", {
        "stage": "ingest", "status": "complete",
        "detail": f"{total:,} recruiting trials found ({source})",
    })
    if not trials:
        await emit("error", {"message": f"No recruiting trials found for '{profile.condition}'."})
        return

    corpus_texts = [t.embed_text() for t in trials]
    query_text = profile.to_query_text()

    # 2) EMBED (GPU burst) ------------------------------------------------
    await emit("stage", {"stage": "embed", "status": "active", "detail": f"Embedding {len(trials):,} trials on GPU…"})
    intend_flash = settings.use_flash and flash_embed.FLASH_AVAILABLE
    sampler = None
    if intend_flash:
        sampler = asyncio.create_task(_live_sampler(tracker, emit))
    corpus_emb, emb_mode = await embed_texts(corpus_texts, tracker)
    query_emb = None
    if corpus_emb is not None:
        q, _ = await embed_texts([query_text], tracker, is_query=True)
        query_emb = q[0] if q is not None else None
    if sampler:
        sampler.cancel()

    # Resolve the honest dashboard mode and animate accordingly.
    if emb_mode == "flash_live":
        tracker.mode = "flash_live"
    else:
        tracker.mode = "local_cpu" if emb_mode == "local_cpu" else "demo_simulated"
        await _simulate_burst(tracker, emit, len(trials))
    await emit("stage", {"stage": "embed", "status": "complete", "detail": f"Embedded {len(trials):,} trials"})

    # 3) RETRIEVE (FAISS / TF-IDF) ---------------------------------------
    # hits is ordered best-first: [(orig_trial_index, retrieval_score), ...]
    if corpus_emb is not None and query_emb is not None:
        hits = vector_search(corpus_emb, query_emb, settings.retrieve_top_k)
    else:
        hits = tfidf_search(corpus_texts, query_text, settings.retrieve_top_k)
    cand_orig_idx = [i for i, _ in hits]
    cand_retrieval = [s for _, s in hits]
    candidates = [trials[i] for i in cand_orig_idx]

    # 4) RERANK (GPU) -----------------------------------------------------
    await emit("stage", {"stage": "rerank", "status": "active", "detail": f"Reranking top {len(candidates)} trials…"})
    cand_texts = [c.embed_text()[:1200] for c in candidates]
    scores, _ = await rerank(query_text, cand_texts, tracker)
    if scores is None:
        # No reranker: keep retrieval order, use retrieval score as the rank score.
        order = list(range(len(candidates)))
        rank_scores = list(cand_retrieval)
    else:
        order = sorted(range(len(candidates)), key=lambda i: scores[i], reverse=True)
        rank_scores = scores
    top_positions = order[: settings.rerank_top_k]
    top_trials = [candidates[p] for p in top_positions]
    await emit("stage", {"stage": "rerank", "status": "complete", "detail": f"Selected top {len(top_trials)}"})

    # 5) REASON (Claude / local) -----------------------------------------
    await emit("stage", {"stage": "reason", "status": "active", "detail": f"Reasoning over {len(top_trials)} trials…"})
    eligs = await reason_batch(profile, top_trials)
    await emit("stage", {"stage": "reason", "status": "complete", "detail": "Eligibility verdicts ready"})

    # Assemble + sort (verdict, then confidence) --------------------------
    matched: list[MatchedTrial] = []
    for pos, trial, elig in zip(top_positions, top_trials, eligs):
        matched.append(MatchedTrial(
            trial=trial,
            retrieval_score=float(cand_retrieval[pos]),
            rerank_score=float(rank_scores[pos]),
            nearest_location=_nearest_location(trial, profile),
            eligibility=elig,
        ))
    matched.sort(key=lambda m: (_VERDICT_RANK.get(m.eligibility.verdict, 1), -m.eligibility.confidence))

    metrics = tracker.build()
    await emit("done", {
        "results": [m.model_dump() for m in matched],
        "compute_metrics": metrics.model_dump(),
        "searched_count": total,
        "profile": profile.model_dump(),
    })
