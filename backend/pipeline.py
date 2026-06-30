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
        "gpu_work_items": tracker.gpu_work_items,
        "gpu_calls": tracker.batch_count,
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

    async def log(msg: str, level: str = "info") -> None:
        """Stream a timestamped line to the dashboard's live activity feed."""
        await emit("log", {"t": round(tracker.elapsed(), 2), "level": level, "msg": msg})

    # Seed infra telemetry (what/where/how) shown live on the dashboard.
    reason_engine = (
        f"Claude · {settings.claude_model}" if settings.use_claude else "Local rule engine"
    )
    tracker.telemetry = {
        "provider": "RunPod Serverless",
        "endpoint_host": "api.runpod.ai",
        "gpu": settings.flash_gpu,
        "embed_endpoint": "lifeline-embed",
        "rerank_endpoint": "lifeline-rerank",
        "embed_endpoint_id": settings.flash_embed_endpoint,
        "rerank_endpoint_id": settings.flash_rerank_endpoint,
        "embed_model": settings.embed_model,
        "rerank_model": settings.rerank_model,
        "reason_engine": reason_engine,
        "batch_size": settings.embed_batch_size,
        "vector_dim": None,
        "ingest_source": None,
        "ingest_total": 0,
        "ingest_fetched": 0,
        "data_sources": [],
    }
    await log(f"Lifeline pipeline started · condition='{profile.condition}'"
              + (f", location='{profile.location}'" if profile.location else ""))

    # 1) INGEST -----------------------------------------------------------
    await emit("stage", {"stage": "ingest", "status": "active", "detail": "Searching ClinicalTrials.gov…"})
    await log("→ Querying ClinicalTrials.gov v2 REST API (filter: RECRUITING)")
    trials, total, source = await get_trials(profile.condition, profile.location)
    tracker.trials_total = total
    src_label = {
        "live": "live ClinicalTrials.gov",
        "brightdata": "Bright Data → ClinicalTrials.gov",
        "cache": "cached snapshot",
    }.get(source, source)
    tracker.telemetry.update(
        ingest_source=source, ingest_total=total, ingest_fetched=len(trials)
    )
    tracker.telemetry["data_sources"] = [
        {"name": "ClinicalTrials.gov v2", "via": src_label, "items": len(trials), "ok": bool(trials)}
    ]
    await log(f"✓ {total:,} recruiting trials via {src_label} → ingested {len(trials):,}")
    await emit("stage", {
        "stage": "ingest", "status": "complete",
        "detail": f"{total:,} recruiting trials found ({src_label})",
    })
    if not trials:
        await emit("error", {"message": f"No recruiting trials found for '{profile.condition}'."})
        return

    corpus_texts = [t.embed_text() for t in trials]
    query_text = profile.to_query_text()

    # 2) EMBED (GPU burst) ------------------------------------------------
    await emit("stage", {"stage": "embed", "status": "active", "detail": f"Embedding {len(trials):,} trials on GPU…"})
    intend_flash = settings.use_flash and flash_embed.FLASH_AVAILABLE
    n_batches = max(1, math.ceil(len(trials) / settings.embed_batch_size))
    await log(
        f"→ Embedding {len(trials):,} trials · {settings.embed_model} · {n_batches} batch"
        f"{'es' if n_batches != 1 else ''} → "
        + (f"RunPod {settings.flash_gpu} (lifeline-embed)" if intend_flash else "local fallback")
    )
    sampler = None
    if intend_flash:
        sampler = asyncio.create_task(_live_sampler(tracker, emit))
    tracker.count_trials = True              # count unique trials only here
    corpus_emb, emb_mode = await embed_texts(corpus_texts, tracker)
    tracker.count_trials = False
    query_emb = None
    if corpus_emb is not None:
        q, _ = await embed_texts([query_text], tracker, is_query=True)
        query_emb = q[0] if q is not None else None
    if sampler:
        sampler.cancel()

    dim = int(corpus_emb.shape[1]) if corpus_emb is not None else None
    tracker.telemetry["vector_dim"] = dim

    # Resolve the honest dashboard mode and animate accordingly.
    if emb_mode == "flash_live":
        tracker.mode = "flash_live"
        await log(
            f"✓ Embedded on RunPod · {tracker.batch_count} GPU call"
            f"{'s' if tracker.batch_count != 1 else ''} · peak {tracker.peak_workers} worker"
            f"{'s' if tracker.peak_workers != 1 else ''} · {dim}-dim vectors"
        )
    else:
        tracker.mode = "local_cpu" if emb_mode == "local_cpu" else "demo_simulated"
        await log(
            f"⚠ Flash unavailable → {tracker.mode} path; showing representative burst",
            level="warn",
        )
        await _simulate_burst(tracker, emit, len(trials))
        tracker.gpu_work_items = max(tracker.gpu_work_items, len(trials))
    await emit("stage", {"stage": "embed", "status": "complete", "detail": f"Embedded {len(trials):,} trials"})

    # 3) RETRIEVE (FAISS / TF-IDF) ---------------------------------------
    # hits is ordered best-first: [(orig_trial_index, retrieval_score), ...]
    if corpus_emb is not None and query_emb is not None:
        hits = vector_search(corpus_emb, query_emb, settings.retrieve_top_k)
        search_kind = f"FAISS cosine over {len(trials):,} × {dim}-dim vectors"
    else:
        hits = tfidf_search(corpus_texts, query_text, settings.retrieve_top_k)
        search_kind = f"TF-IDF cosine over {len(trials):,} trials"
    cand_orig_idx = [i for i, _ in hits]
    cand_retrieval = [s for _, s in hits]
    candidates = [trials[i] for i in cand_orig_idx]
    await log(f"✓ Retrieval: {search_kind} → top {len(candidates)} candidates")

    # 4) RERANK (GPU) -----------------------------------------------------
    await emit("stage", {"stage": "rerank", "status": "active", "detail": f"Reranking top {len(candidates)} trials…"})
    await log(
        f"→ Reranking {len(candidates)} candidates · {settings.rerank_model} → "
        + (f"RunPod (lifeline-rerank)" if intend_flash else "local fallback")
    )
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
    await log(f"✓ Reranked → selected top {len(top_trials)} trials")
    await emit("stage", {"stage": "rerank", "status": "complete", "detail": f"Selected top {len(top_trials)}"})

    # 5) REASON (Claude / local) -----------------------------------------
    await emit("stage", {"stage": "reason", "status": "active", "detail": f"Reasoning over {len(top_trials)} trials…"})
    await log(f"→ Eligibility reasoning over {len(top_trials)} trials · {reason_engine}")
    eligs = await reason_batch(profile, top_trials)
    await log("✓ Eligibility verdicts ready")
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

    # 6) ENRICH (Bright Data SERP) — optional, non-blocking, fallback-safe -----
    if settings.use_brightdata_enrich and matched:
        try:
            from . import brightdata

            await log("→ Enriching top trials with web context via Bright Data SERP…")
            top = matched[:3]

            async def _enrich(m):
                q = f"{m.trial.nctId} {m.trial.briefTitle} clinical trial"
                return await brightdata.serp_context(q, n=2)

            results = await asyncio.wait_for(
                asyncio.gather(*(_enrich(m) for m in top), return_exceptions=True),
                timeout=20.0,
            )
            enriched = 0
            for m, res in zip(top, results):
                if isinstance(res, list) and res:
                    m.enrichment = {"provider": "Bright Data SERP", "items": res}
                    enriched += 1
            tracker.telemetry["enrichment"] = {
                "provider": "Bright Data SERP", "via": "Google", "enriched": enriched, "ok": enriched > 0,
            }
            if enriched:
                tracker.telemetry.setdefault("data_sources", []).append(
                    {"name": "Bright Data SERP", "via": "web search", "items": enriched, "ok": True}
                )
            await log(f"✓ Enriched {enriched} trial(s) with Bright Data web context")
        except Exception as exc:  # noqa: BLE001
            await log(f"⚠ Bright Data enrichment skipped ({exc})", level="warn")

    metrics = tracker.build()
    await log(
        f"✓ Done in {metrics.elapsed_s:.1f}s · {metrics.batch_count} GPU calls · "
        f"{metrics.gpu_work_items:,} vectors · est ${metrics.cost_est:.4f}"
    )
    await emit("done", {
        "results": [m.model_dump() for m in matched],
        "compute_metrics": metrics.model_dump(),
        "searched_count": total,
        "profile": profile.model_dump(),
    })
