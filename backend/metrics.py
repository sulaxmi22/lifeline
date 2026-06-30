"""ComputeTracker — the honest accounting behind the live dashboard.

Honesty rules (from the spec):
  * trial counts and wall-clock are REAL.
  * GPU-seconds and cost are clearly-labeled ESTIMATES (Flash doesn't expose
    exact per-call GPU time).
  * In demo/local mode we never fake live worker telemetry — the dashboard
    labels the burst as a representative simulation.

Why summed call-durations == GPU-seconds: embedding batches run concurrently
on separate workers, so the sum of per-call wall-clock is total GPU busy-time
across the fleet (not the elapsed wall-clock, which would undercount).
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager

from .config import Settings
from .models import ComputeMetrics, EfficiencyComparison


class ComputeTracker:
    def __init__(self, settings: Settings) -> None:
        self.s = settings
        self.max_workers = settings.max_workers
        self.gpu_cost_per_second = settings.gpu_cost_per_second

        self.mode = "demo_simulated"
        self.in_flight = 0
        self.peak_workers = 0
        self.gpu_seconds = 0.0
        self.batch_count = 0
        self.trials_processed = 0
        self.trials_total = 0
        self.timeline: list[dict] = []

        self._t0 = time.perf_counter()
        self._gpu_stage_seconds = 0.0  # wall-clock spent in GPU stages

    # --- timing ---------------------------------------------------------
    def reset_clock(self) -> None:
        self._t0 = time.perf_counter()

    def elapsed(self) -> float:
        return time.perf_counter() - self._t0

    def active_workers(self) -> int:
        return min(self.in_flight, self.max_workers)

    # --- live GPU call tracking ----------------------------------------
    @asynccontextmanager
    async def gpu_call(self, n_items: int):
        """Wrap one real Flash call: counts in-flight workers + GPU-seconds."""
        self.in_flight += 1
        self.batch_count += 1
        self.peak_workers = max(self.peak_workers, self.active_workers())
        start = time.perf_counter()
        try:
            yield
        finally:
            dur = time.perf_counter() - start
            self.gpu_seconds += dur
            self._gpu_stage_seconds = max(self._gpu_stage_seconds, self.elapsed())
            self.trials_processed += n_items
            self.in_flight -= 1

    def add_tick(self, workers: int | None = None) -> dict:
        tick = {
            "t": round(self.elapsed(), 2),
            "workers": self.active_workers() if workers is None else workers,
        }
        self.timeline.append(tick)
        return tick

    # --- simulated burst (demo / local CPU path) -----------------------
    def record_sim_seconds(self, workers: int, dt: float) -> None:
        """Accumulate GPU-seconds for a representative simulated tick."""
        self.gpu_seconds += workers * dt
        self.peak_workers = max(self.peak_workers, workers)
        self._gpu_stage_seconds += dt

    # --- final metrics --------------------------------------------------
    def _utilization(self) -> float:
        denom = self.peak_workers * max(self._gpu_stage_seconds, 1e-6)
        if denom <= 0:
            return 0.0
        return min(self.gpu_seconds / denom, 1.0)

    def build(self) -> ComputeMetrics:
        cost = self.gpu_seconds * self.gpu_cost_per_second
        util = self._utilization()
        util_pct = round(util * 100, 1)

        # Cost per *useful* GPU-second: always-on idles ~98%, Flash ~90% used.
        eff = EfficiencyComparison()
        always_on_per_sec = eff.always_on_cost_per_day / 86400.0
        always_on_active = max(1.0 - eff.always_on_idle_pct / 100.0, 1e-6)
        flash_active = max(util, 1e-6)
        cost_per_useful_alwayson = always_on_per_sec / always_on_active
        cost_per_useful_flash = self.gpu_cost_per_second / flash_active
        cheaper = cost_per_useful_alwayson / max(cost_per_useful_flash, 1e-9)

        eff.flash_run_cost = round(cost, 6)
        eff.flash_utilization_pct = util_pct
        eff.cheaper_factor = round(cheaper, 1)

        return ComputeMetrics(
            mode=self.mode,
            trials_total_available=self.trials_total,
            trials_processed=self.trials_processed,
            batch_count=self.batch_count,
            peak_workers=self.peak_workers,
            gpu_seconds_est=round(self.gpu_seconds, 3),
            cost_est=round(cost, 6),
            elapsed_s=round(self.elapsed(), 2),
            timeline=self.timeline,
            efficiency=eff,
        )
