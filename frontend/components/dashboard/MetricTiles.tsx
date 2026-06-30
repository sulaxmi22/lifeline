"use client";

function Tile({
  label,
  value,
  sub,
  est,
  accent = "text-d-text",
}: {
  label: string;
  value: string;
  sub?: string;
  est?: boolean;
  accent?: string;
}) {
  return (
    <div className="rounded-2xl border border-d-line bg-d-panel/60 p-4">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[11px] uppercase tracking-wider text-d-dim">
          {label}
        </span>
        {est && (
          <span className="rounded bg-d-amber/15 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-d-amber">
            est.
          </span>
        )}
      </div>
      <div className={`mt-2 font-mono text-3xl font-semibold tabular-nums ${accent}`}>
        {value}
      </div>
      {sub && <div className="mt-0.5 font-mono text-[11px] text-d-dim">{sub}</div>}
    </div>
  );
}

export default function MetricTiles({
  trialsProcessed,
  trialsTotal,
  peakWorkers,
  gpuSeconds,
  cost,
}: {
  trialsProcessed: number;
  trialsTotal: number;
  peakWorkers: number;
  gpuSeconds: number;
  cost: number;
}) {
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Tile
        label="Trials processed"
        value={trialsProcessed.toLocaleString()}
        sub={trialsTotal ? `of ${trialsTotal.toLocaleString()} available` : "real count"}
        accent="text-d-gpu"
      />
      <Tile label="Peak GPU workers" value={peakWorkers.toString()} sub="parallel" />
      <Tile
        label="GPU-seconds"
        value={gpuSeconds.toFixed(1)}
        sub="busy-time across fleet"
        est
      />
      <Tile
        label="Run cost"
        value={`$${cost.toFixed(4)}`}
        sub="this query"
        est
        accent="text-d-amber"
      />
    </div>
  );
}
