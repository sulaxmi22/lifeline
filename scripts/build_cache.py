"""Fetch live recruiting trials for the seed conditions and cache them.

Run once before demoing so DEMO_MODE has real data to serve:
    python scripts/build_cache.py

The live ClinicalTrials.gov path was verified during planning; this just
persists a snapshot per seed condition to backend/cache/trials_<cond>.json.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running as a plain script (python scripts/build_cache.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.ingest import fetch_live, write_cache  # noqa: E402

SEED_CONDITIONS = [
    ("breast cancer", None),
    ("epilepsy", None),
    ("type 2 diabetes", None),
]

# Keep caches lean enough to ship but big enough to be a real corpus.
MAX_PER_CONDITION = 800


async def main() -> None:
    for condition, location in SEED_CONDITIONS:
        print(f"\n=== {condition} ===")
        try:
            trials, total = await fetch_live(
                condition, location, max_trials=MAX_PER_CONDITION
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  FAILED: {exc!r}")
            continue
        path = write_cache(condition, trials, total)
        print(f"  totalCount={total}  cached={len(trials)}  -> {path}")


if __name__ == "__main__":
    asyncio.run(main())
