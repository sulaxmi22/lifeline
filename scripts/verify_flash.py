"""Pre-demo gate: prove RunPod Flash is REALLY being hit.

Run this BEFORE you go on stage. It calls the same embed + rerank client
wrappers the app uses and checks the returned `mode`:

    mode == "flash_live"   -> ✅ real RunPod GPU workers
    mode == "local_cpu"    -> running sentence-transformers locally (not RunPod)
    mode == "tfidf"        -> lightweight fallback (no model at all)

Exit code 0 only when BOTH embed and rerank report flash_live, so you can
trust it as a hard gate.

    source .venv/bin/activate
    python scripts/verify_flash.py
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

# Allow running as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import flash_embed  # noqa: E402
from backend.config import get_settings  # noqa: E402
from backend.flash_embed import embed_texts  # noqa: E402
from backend.flash_rerank import rerank  # noqa: E402
from backend.metrics import ComputeTracker  # noqa: E402

# Small, realistic trial-like corpus so the embed call does real work.
SAMPLE_TRIALS = [
    "Title: Trastuzumab Deruxtecan in HER2-Positive Metastatic Breast Cancer. "
    "Eligibility: adults with HER2+ metastatic breast cancer who progressed on "
    "prior trastuzumab-based therapy. Phase: PHASE2.",
    "Title: Pembrolizumab for Triple-Negative Breast Cancer. Eligibility: women "
    "18+ with TNBC, no prior immunotherapy. Phase: PHASE3.",
    "Title: Adjuvant Endocrine Therapy in ER-Positive Breast Cancer. "
    "Eligibility: postmenopausal women with hormone-receptor-positive disease.",
    "Title: Levetiracetam Add-On for Drug-Resistant Focal Epilepsy in Children. "
    "Eligibility: pediatric patients 4-17 with refractory focal seizures.",
    "Title: GLP-1 Agonist for Type 2 Diabetes and Obesity. Eligibility: adults "
    "with T2DM and BMI > 30 on metformin.",
]
QUERY = (
    "Condition: breast cancer. Age: 54. Sex: female. "
    "Prior treatments: trastuzumab, chemotherapy. Notes: metastatic HER2+."
)


def _preflight(settings) -> bool:
    """Print preconditions; return True if the live path is even possible."""
    print("── Preflight ───────────────────────────────────────────────")
    print(f"  runpod-flash installed (FLASH_AVAILABLE): {flash_embed.FLASH_AVAILABLE}")
    print(f"  RUNPOD_API_KEY set:                       {bool(settings.runpod_api_key)}")
    print(f"  DEMO_MODE:                                {settings.demo_mode}")
    print(f"  -> use_flash (will attempt RunPod):       {settings.use_flash}")
    print(f"  embed model:                              {settings.embed_model}")
    print(f"  FLASH_APP / FLASH_ENV:                    {settings.flash_app} / {settings.flash_env}")
    ok = True
    if not flash_embed.FLASH_AVAILABLE:
        print("  ✗ FIX: pip install runpod-flash")
        ok = False
    if not settings.runpod_api_key:
        print("  ✗ FIX: set RUNPOD_API_KEY in .env (this is the switch that enables the live path)")
        ok = False
    if settings.demo_mode:
        print("  ✗ FIX: set DEMO_MODE=false in .env")
        ok = False
    print("────────────────────────────────────────────────────────────")
    return ok


async def main() -> int:
    settings = get_settings()
    possible = _preflight(settings)

    tracker = ComputeTracker(settings)

    print("\nEmbedding 5 sample trials…")
    t0 = time.time()
    emb, emode = await embed_texts(SAMPLE_TRIALS, tracker)
    embed_dt = time.time() - t0
    dim = None if emb is None else int(emb.shape[1])
    print(f"  embed mode = {emode!r}  | dim = {dim}  | {embed_dt:.2f}s")

    print("\nReranking the 5 trials against the patient query…")
    t1 = time.time()
    scores, rmode = await rerank(QUERY, SAMPLE_TRIALS, tracker)
    rerank_dt = time.time() - t1
    top = max(scores) if scores else None
    print(f"  rerank mode = {rmode!r} | top score = {top} | {rerank_dt:.2f}s")

    live = emode == "flash_live" and rmode == "flash_live"
    print("\n══════════════════════════════════════════════════════════════")
    if live:
        print("  ✅ PASS — RunPod Flash is genuinely being hit. Demo is live.")
        print("  The dashboard will show real worker scale-up (0→N→0).")
        return 0

    print("  ❌ NOT LIVE — the app is running on the fallback path, not RunPod.")
    if not possible:
        print("  Fix the preflight items above, then re-run.")
    else:
        print("  Preflight looked OK but calls still fell back. Check:")
        print("   • `flash deploy` actually deployed lifeline-embed + lifeline-rerank")
        print("   • FLASH_APP/FLASH_ENV match between the deploy shell and this run")
        print("   • RunPod balance > $0 and Serverless/Flash enabled on the account")
    print("  (Demo still works safely in the labeled DEMO/simulated mode.)")
    print("══════════════════════════════════════════════════════════════")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
