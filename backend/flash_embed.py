"""RunPod Flash embedding endpoint + tiered client wrapper.

Tier 1: Flash GPU (BAAI/bge-base-en-v1.5 via sentence-transformers) — the star.
Tier 2: local CPU sentence-transformers (if installed, no keys).
Tier 3: signal None -> caller uses TF-IDF retrieval (guaranteed, light).

The @Endpoint function fans out one call per batch; the client awaits them
concurrently, which is what triggers Flash's parallel worker scale-up.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from .config import get_settings
from .metrics import ComputeTracker

# bge retrieval works best when the *query* carries this instruction.
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

# --------------------------------------------------------------------------
# Tier 1 — RunPod Flash GPU endpoint
# --------------------------------------------------------------------------
try:
    from runpod_flash import Endpoint, GpuType

    FLASH_AVAILABLE = True
except Exception:  # noqa: BLE001 - SDK optional
    FLASH_AVAILABLE = False


_EMBED_MODEL_NAME = get_settings().embed_model

if FLASH_AVAILABLE:

    @Endpoint(
        name="lifeline-embed",
        gpu=GpuType.NVIDIA_GEFORCE_RTX_4090,
        workers=(get_settings().flash_min_workers, get_settings().max_workers),
        dependencies=["sentence-transformers", "torch"],
    )
    async def embed_batch(texts: list[str]) -> list[list[float]]:
        # Heavy imports MUST be inside the function body for Flash.
        from sentence_transformers import SentenceTransformer

        # Load once per warm worker (module global persists across calls).
        global _MODEL  # noqa: PLW0603
        try:
            _MODEL  # type: ignore[has-type]
        except NameError:
            _MODEL = SentenceTransformer(_EMBED_MODEL_NAME)  # type: ignore[name-defined]

        vecs = _MODEL.encode(  # type: ignore[name-defined]
            texts, normalize_embeddings=True, show_progress_bar=False
        )
        return [v.tolist() for v in vecs]


# --------------------------------------------------------------------------
# Tier 2 — local CPU sentence-transformers
# --------------------------------------------------------------------------
_LOCAL_MODEL = None


def _local_model():
    global _LOCAL_MODEL  # noqa: PLW0603
    if _LOCAL_MODEL is None:
        from sentence_transformers import SentenceTransformer  # may raise

        _LOCAL_MODEL = SentenceTransformer(get_settings().embed_model)
    return _LOCAL_MODEL


def _embed_local_cpu(texts: list[str]) -> Optional[np.ndarray]:
    try:
        model = _local_model()
    except Exception:
        return None
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vecs, dtype=np.float32)


# --------------------------------------------------------------------------
# Public client wrapper (tier selection)
# --------------------------------------------------------------------------
def _batched(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


async def _embed_flash(texts: list[str], tracker: ComputeTracker) -> np.ndarray:
    import asyncio

    batches = list(_batched(texts, get_settings().embed_batch_size))

    async def run_batch(batch: list[str]) -> list[list[float]]:
        async with tracker.gpu_call(len(batch)):
            return await embed_batch(batch)  # type: ignore[name-defined]

    # Fan out concurrently -> visible GPU worker burst.
    results = await asyncio.gather(*(run_batch(b) for b in batches))
    flat = [vec for batch in results for vec in batch]
    return np.asarray(flat, dtype=np.float32)


async def embed_texts(
    texts: list[str], tracker: ComputeTracker, is_query: bool = False
) -> tuple[Optional[np.ndarray], str]:
    """Return (embeddings | None, mode). None => caller should use TF-IDF."""
    settings = get_settings()
    payload = (
        [QUERY_INSTRUCTION + t for t in texts] if is_query else list(texts)
    )

    if settings.use_flash and FLASH_AVAILABLE:
        try:
            emb = await _embed_flash(payload, tracker)
            return emb, "flash_live"
        except Exception as exc:  # noqa: BLE001
            print(f"[embed] Flash path failed ({exc!r}); falling back to CPU/TF-IDF")

    emb = _embed_local_cpu(payload)
    if emb is not None:
        return emb, "local_cpu"

    return None, "tfidf"
