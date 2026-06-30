"use client";

// Per-bar load jitter so lit workers look alive, not uniform. Deterministic by index.
const JITTER = [0.92, 0.78, 1.0, 0.85, 0.95, 0.72, 0.88, 0.81, 0.9, 0.76, 0.97, 0.83];

export default function WorkerGrid({
  workers,
  maxWorkers,
  finished,
}: {
  workers: number;
  maxWorkers: number;
  finished: boolean;
}) {
  const bars = Array.from({ length: maxWorkers });
  const scaledToZero = finished && workers === 0;

  return (
    <div className="rounded-2xl border border-d-line bg-d-panel/60 p-5">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="font-mono text-[12px] uppercase tracking-[0.2em] text-d-dim">
          GPU workers
        </h2>
        <span className="font-mono text-[13px] text-d-gpu">
          {workers} / {maxWorkers} active
        </span>
      </div>

      <div className="flex h-32 items-end gap-2">
        {bars.map((_, i) => {
          const lit = i < workers;
          const height = lit ? `${Math.round(JITTER[i % JITTER.length] * 100)}%` : "6%";
          return (
            <div
              key={i}
              className="relative flex-1 overflow-hidden rounded-md bg-d-bg-2"
              style={{ height: "100%" }}
            >
              <div
                className={`absolute bottom-0 left-0 right-0 rounded-md transition-all duration-300 ease-out ${
                  lit ? "bg-d-gpu dash-glow" : "bg-d-line"
                }`}
                style={{ height }}
              />
              <span className="absolute bottom-1 left-0 right-0 text-center font-mono text-[9px] text-d-bg">
                {i}
              </span>
            </div>
          );
        })}
      </div>

      <p
        className={`mt-3 text-center font-mono text-[12px] transition-colors ${
          scaledToZero ? "text-d-gpu" : "text-d-dim"
        }`}
      >
        {scaledToZero
          ? "▼ workers scaled to zero — you pay nothing while idle"
          : workers > 0
          ? "scaling up to absorb the embedding burst…"
          : "idle — 0 workers, $0/sec"}
      </p>
    </div>
  );
}
