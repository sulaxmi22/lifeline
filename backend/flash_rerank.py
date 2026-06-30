"""RunPod Flash reranking endpoint + tiered client wrapper.

Tier 1: Flash GPU CrossEncoder (BAAI/bge-reranker-base).
Tier 2: local CPU CrossEncoder (if installed).
Tier 3: None -> caller keeps retrieval order/scores.
"""
from __future__ import annotations

from typing import Optional

from .config import get_settings
from .metrics import ComputeTracker

try:
    from runpod_flash import Endpoint, GpuType

    FLASH_AVAILABLE = True
except Exception:  # noqa: BLE001
    FLASH_AVAILABLE = False


_RERANK_MODEL_NAME = get_settings().rerank_model

if FLASH_AVAILABLE:

    @Endpoint(
        name="lifeline-rerank",
        gpu=GpuType.NVIDIA_GEFORCE_RTX_4090,
        workers=(get_settings().flash_min_workers, 2),
        dependencies=["sentence-transformers", "torch"],
    )
    async def rerank_batch(query: str, texts: list[str]) -> list[float]:
        from sentence_transformers import CrossEncoder

        global _RERANKER  # noqa: PLW0603
        try:
            _RERANKER  # type: ignore[has-type]
        except NameError:
            _RERANKER = CrossEncoder(_RERANK_MODEL_NAME)  # type: ignore[name-defined]

        pairs = [[query, t] for t in texts]
        scores = _RERANKER.predict(pairs)  # type: ignore[name-defined]
        return [float(s) for s in scores]


# --- Tier 2: local CPU CrossEncoder ---------------------------------------
_LOCAL_RERANKER = None


def _local_reranker():
    global _LOCAL_RERANKER  # noqa: PLW0603
    if _LOCAL_RERANKER is None:
        from sentence_transformers import CrossEncoder  # may raise

        _LOCAL_RERANKER = CrossEncoder(get_settings().rerank_model)
    return _LOCAL_RERANKER


def _rerank_local_cpu(query: str, texts: list[str]) -> Optional[list[float]]:
    try:
        model = _local_reranker()
    except Exception:
        return None
    pairs = [[query, t] for t in texts]
    return [float(s) for s in model.predict(pairs)]


async def rerank(
    query: str, texts: list[str], tracker: ComputeTracker
) -> tuple[Optional[list[float]], str]:
    """Return (scores | None, mode). None => caller keeps retrieval order."""
    if not texts:
        return [], "empty"

    settings = get_settings()
    if settings.use_flash and FLASH_AVAILABLE:
        try:
            async with tracker.gpu_call(len(texts)):
                scores = await rerank_batch(query, texts)  # type: ignore[name-defined]
            return scores, "flash_live"
        except Exception as exc:  # noqa: BLE001
            print(f"[rerank] Flash path failed ({exc!r}); falling back")

    scores = _rerank_local_cpu(query, texts)
    if scores is not None:
        return scores, "local_cpu"

    return None, "retrieval_only"
