"use client";

import type { StageEvent } from "@/lib/types";

type StageKey = "ingest" | "embed" | "rerank" | "reason" | "done";
type Status = "pending" | "active" | "complete";

const STEPS: {
  key: StageKey;
  label: string;
  kind: "cpu" | "gpu" | "claude" | "done";
  tag: string;
}[] = [
  { key: "ingest", label: "Ingest", kind: "cpu", tag: "CPU · API" },
  { key: "embed", label: "Embed", kind: "gpu", tag: "GPU burst" },
  { key: "rerank", label: "Rerank", kind: "gpu", tag: "GPU" },
  { key: "reason", label: "Reason", kind: "claude", tag: "Claude" },
  { key: "done", label: "Done", kind: "done", tag: "" },
];

const KIND_COLOR: Record<string, string> = {
  cpu: "text-d-cpu border-d-cpu/40",
  gpu: "text-d-gpu border-d-gpu/40",
  claude: "text-d-claude border-d-claude/40",
  done: "text-d-text border-d-line",
};
const KIND_DOT: Record<string, string> = {
  cpu: "bg-d-cpu",
  gpu: "bg-d-gpu",
  claude: "bg-d-claude",
  done: "bg-d-text",
};

export default function PipelineBar({
  stages,
}: {
  stages: Record<string, StageEvent["status"]>;
}) {
  function statusOf(key: StageKey): Status {
    return (stages[key] as Status) || "pending";
  }

  return (
    <div className="rounded-2xl border border-d-line bg-d-panel/60 p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-mono text-[12px] uppercase tracking-[0.2em] text-d-dim">
          Pipeline
        </h2>
        <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-wider text-d-dim">
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-sm bg-d-gpu" /> GPU
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-sm bg-d-cpu" /> CPU
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-sm bg-d-claude" /> Claude
          </span>
        </div>
      </div>

      <div className="flex items-stretch gap-2">
        {STEPS.map((step, i) => {
          const status = statusOf(step.key);
          const active = status === "active";
          const complete = status === "complete";
          return (
            <div key={step.key} className="flex flex-1 items-center gap-2">
              <div
                className={`flex-1 rounded-xl border px-3 py-3 transition-all duration-500 ${
                  active
                    ? `${KIND_COLOR[step.kind]} bg-d-panel-2 ${
                        step.kind === "gpu" ? "dash-glow" : ""
                      }`
                    : complete
                    ? "border-d-line/80 bg-d-panel-2 text-d-text"
                    : "border-d-line/40 bg-transparent text-d-dim"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`h-2 w-2 rounded-full ${
                      active
                        ? `${KIND_DOT[step.kind]} animate-pulse-soft`
                        : complete
                        ? "bg-d-gpu"
                        : "bg-d-line"
                    }`}
                  />
                  <span className="text-[14px] font-semibold">{step.label}</span>
                  {complete && <span className="ml-auto text-d-gpu">✓</span>}
                </div>
                {step.tag && (
                  <span className="mt-1 block font-mono text-[10px] uppercase tracking-wider opacity-80">
                    {step.tag}
                  </span>
                )}
              </div>
              {i < STEPS.length - 1 && (
                <span
                  className={`h-px w-3 ${
                    complete ? "bg-d-gpu/60" : "bg-d-line"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
