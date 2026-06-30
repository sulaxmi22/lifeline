"""Central runtime configuration for Lifeline.

Every module asks *this* object which tier to run — never `os.getenv` directly.
That is what makes "one codebase, two modes" work: when RUNPOD_API_KEY or
ANTHROPIC_API_KEY appear, the live (Tier 1) paths light up automatically; with
no keys we fall through to the guaranteed DEMO tiers. See the tiered-fallback
table in the project plan.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

# Load .env if python-dotenv is available (optional dependency).
try:  # pragma: no cover - trivial
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Resolved settings + tier selectors."""

    def __init__(self) -> None:
        self.runpod_api_key: str = os.getenv("RUNPOD_API_KEY", "").strip()
        self.anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self.flash_app: str = os.getenv("FLASH_APP", "lifeline")
        self.flash_env: str = os.getenv("FLASH_ENV", "production")
        # Deployed RunPod endpoint IDs (shown on the dashboard; override per redeploy).
        self.flash_embed_endpoint: str = os.getenv("FLASH_EMBED_ENDPOINT", "5fucn5wwhv0e0d")
        self.flash_rerank_endpoint: str = os.getenv("FLASH_RERANK_ENDPOINT", "ownywjzmaay4yy")
        self.flash_gpu: str = os.getenv("FLASH_GPU", "NVIDIA RTX 4090")

        # Bright Data (web extraction). Fetch layer needs a Web Unlocker zone;
        # everything degrades gracefully to curl_cffi / no-enrichment if unset.
        self.brightdata_api_key: str = os.getenv("BRIGHTDATA_API_KEY", "").strip()
        self.brightdata_zone: str = os.getenv("BRIGHTDATA_ZONE", "web_unlocker1").strip()
        self.brightdata_serp_zone: str = os.getenv("BRIGHTDATA_SERP_ZONE", "serp_api1").strip()
        self.gpu_cost_per_second: float = float(
            os.getenv("GPU_COST_PER_SECOND", "0.00012")
        )
        self.demo_mode: bool = _as_bool(os.getenv("DEMO_MODE"), default=False)

        # Models (defaults chosen for speed; switch to -large for quality).
        self.embed_model: str = os.getenv("EMBED_MODEL", "BAAI/bge-base-en-v1.5")
        self.rerank_model: str = os.getenv(
            "RERANK_MODEL", "BAAI/bge-reranker-base"
        )
        self.claude_model: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

        # Pipeline sizing.
        self.max_workers: int = int(os.getenv("MAX_GPU_WORKERS", "8"))
        # Min warm GPU workers. Default 0 keeps the scale-to-zero story intact.
        # Set to 1 just before a live demo to avoid first-call cold-start lag
        # (trade-off: the dashboard won't show a true scale-to-ZERO finale).
        self.flash_min_workers: int = int(os.getenv("FLASH_MIN_WORKERS", "0"))
        self.embed_batch_size: int = int(os.getenv("EMBED_BATCH_SIZE", "48"))
        self.retrieve_top_k: int = int(os.getenv("RETRIEVE_TOP_K", "50"))
        self.rerank_top_k: int = int(os.getenv("RERANK_TOP_K", "15"))
        self.max_trials: int = int(os.getenv("MAX_TRIALS", "1200"))

        # Network timeouts (seconds).
        self.ctgov_timeout: float = float(os.getenv("CTGOV_TIMEOUT", "20"))

        self.cache_dir: Path = Path(__file__).resolve().parent / "cache"

    # --- Tier selectors -------------------------------------------------
    @property
    def use_flash(self) -> bool:
        """True when we should attempt the live RunPod Flash GPU path."""
        return bool(self.runpod_api_key) and not self.demo_mode

    @property
    def use_claude(self) -> bool:
        """True when Claude should do eligibility reasoning."""
        return bool(self.anthropic_api_key)

    @property
    def use_live_ingest(self) -> bool:
        """True when we should hit the live ClinicalTrials.gov API."""
        return not self.demo_mode

    @property
    def use_brightdata_fetch(self) -> bool:
        """Route live CT.gov fetch through Bright Data Web Unlocker."""
        return bool(self.brightdata_api_key and self.brightdata_zone) and not self.demo_mode

    @property
    def use_brightdata_enrich(self) -> bool:
        """Enrich top results with Bright Data (SERP). Non-blocking, optional."""
        return bool(self.brightdata_api_key and self.brightdata_serp_zone)

    def describe(self) -> dict:
        return {
            "demo_mode": self.demo_mode,
            "use_flash": self.use_flash,
            "use_claude": self.use_claude,
            "use_live_ingest": self.use_live_ingest,
            "embed_model": self.embed_model,
            "rerank_model": self.rerank_model,
            "max_workers": self.max_workers,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
