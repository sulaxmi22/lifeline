"use client";

import type { EfficiencyComparison } from "@/lib/types";

export default function EfficiencyPanel({
  liveCost,
  efficiency,
}: {
  liveCost: number;
  efficiency: EfficiencyComparison | null;
}) {
  const alwaysOn = efficiency?.always_on_cost_per_day ?? 17;
  const idle = efficiency?.always_on_idle_pct ?? 98;
  const util = efficiency?.flash_utilization_pct ?? 0;
  const cheaper = efficiency?.cheaper_factor ?? 0;
  const flashCost = efficiency?.flash_run_cost ?? liveCost;

  return (
    <div className="rounded-2xl border border-d-line bg-d-panel/60 p-5">
      <h2 className="mb-4 font-mono text-[12px] uppercase tracking-[0.2em] text-d-dim">
        Efficiency
      </h2>

      <div className="grid gap-3 sm:grid-cols-2">
        {/* Always-on */}
        <div className="rounded-xl border border-d-line/60 bg-d-bg-2 p-4">
          <p className="font-mono text-[11px] uppercase tracking-wider text-d-dim">
            Always-on GPU (traditional)
          </p>
          <p className="mt-2 font-mono text-2xl font-semibold text-d-text">
            ~${alwaysOn.toFixed(0)}
            <span className="text-sm text-d-dim">/day</span>
          </p>
          <div className="mt-3">
            <div className="mb-1 flex justify-between font-mono text-[10px] text-d-dim">
              <span>idle</span>
              <span>{idle.toFixed(0)}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-d-line">
              <div
                className="h-full rounded-full bg-d-amber/50"
                style={{ width: `${100 - idle}%` }}
              />
            </div>
            <p className="mt-1.5 font-mono text-[10px] text-d-dim">
              billed 24/7 — wasted while idle
            </p>
          </div>
        </div>

        {/* Flash */}
        <div className="rounded-xl border border-d-gpu/40 bg-d-panel-2 p-4 dash-glow">
          <p className="font-mono text-[11px] uppercase tracking-wider text-d-gpu">
            RunPod Flash (this run)
          </p>
          <p className="mt-2 font-mono text-2xl font-semibold text-d-gpu">
            ${flashCost.toFixed(4)}
          </p>
          <div className="mt-3">
            <div className="mb-1 flex justify-between font-mono text-[10px] text-d-dim">
              <span>utilization while active</span>
              <span className="text-d-gpu">
                {util > 0 ? `${util.toFixed(0)}%` : "…"}
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-d-line">
              <div
                className="h-full rounded-full bg-d-gpu transition-all duration-700"
                style={{ width: `${util}%` }}
              />
            </div>
            <p className="mt-1.5 font-mono text-[10px] text-d-gpu/80">
              scaled to zero — $0 while idle
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-center gap-3 rounded-xl border border-d-gpu/30 bg-d-gpu/5 px-4 py-3">
        <span className="font-mono text-[12px] uppercase tracking-wider text-d-dim">
          For this workload
        </span>
        <span className="font-mono text-2xl font-semibold text-d-gpu">
          {cheaper > 0 ? `≈${cheaper.toFixed(0)}× cheaper` : "computing…"}
        </span>
      </div>
    </div>
  );
}
