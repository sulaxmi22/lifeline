"use client";

import type { Telemetry } from "@/lib/types";

function Row({ k, v, accent = "text-d-text" }: { k: string; v: React.ReactNode; accent?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1.5">
      <span className="font-mono text-[11px] uppercase tracking-wider text-d-dim">{k}</span>
      <span className={`text-right font-mono text-[12px] ${accent}`}>{v}</span>
    </div>
  );
}

/** "How are we using RunPod?" — live infra facts + data provenance. */
export default function InfraPanel({
  telemetry,
  isLive,
  gpuCalls,
}: {
  telemetry: Telemetry | null;
  isLive: boolean;
  gpuCalls: number;
}) {
  const t = telemetry || {};
  const sources = t.data_sources || [];

  return (
    <div className="rounded-2xl border border-d-runpod/30 bg-d-runpod/5 p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-mono text-[12px] uppercase tracking-[0.2em] text-d-runpod">
          RunPod Serverless · infrastructure
        </h2>
        <span
          className={`rounded-full px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${
            isLive
              ? "bg-d-runpod/20 text-d-runpod"
              : "bg-d-amber/15 text-d-amber"
          }`}
        >
          {isLive ? "● live" : "○ simulated"}
        </span>
      </div>

      <div className="grid gap-x-6 sm:grid-cols-2">
        <div>
          <Row k="Provider" v={t.provider || "RunPod Serverless"} accent="text-d-runpod" />
          <Row k="Calling" v={t.endpoint_host || "api.runpod.ai"} />
          <Row k="GPU" v={t.gpu || "RTX 4090"} accent="text-d-gpu" />
          <Row k="GPU calls" v={gpuCalls.toLocaleString()} accent="text-d-gpu" />
        </div>
        <div>
          <Row
            k="Embed"
            v={
              <>
                {t.embed_endpoint || "lifeline-embed"}
                {t.embed_endpoint_id && (
                  <span className="text-d-dim"> · {t.embed_endpoint_id}</span>
                )}
              </>
            }
            accent="text-d-gpu"
          />
          <Row
            k="Rerank"
            v={
              <>
                {t.rerank_endpoint || "lifeline-rerank"}
                {t.rerank_endpoint_id && (
                  <span className="text-d-dim"> · {t.rerank_endpoint_id}</span>
                )}
              </>
            }
            accent="text-d-gpu"
          />
          <Row k="Embed model" v={t.embed_model || "bge-base-en-v1.5"} />
          <Row
            k="Vectors"
            v={t.vector_dim ? `${t.vector_dim}-dim` : "—"}
          />
        </div>
      </div>

      {/* Data sources / provenance */}
      <div className="mt-3 border-t border-d-line/60 pt-3">
        <span className="font-mono text-[10px] uppercase tracking-wider text-d-dim">
          Data sources
        </span>
        <div className="mt-2 flex flex-wrap gap-2">
          {sources.length === 0 && (
            <span className="font-mono text-[11px] text-d-dim">connecting…</span>
          )}
          {sources.map((s) => (
            <span
              key={s.name}
              className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 font-mono text-[11px] ${
                s.via.toLowerCase().includes("bright")
                  ? "border-d-bright/40 bg-d-bright/10 text-d-bright"
                  : "border-d-cpu/30 bg-d-cpu/5 text-d-cpu"
              }`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${s.ok ? "bg-current" : "bg-d-dim"}`} />
              {s.name}
              <span className="text-d-dim">· {s.items.toLocaleString()} via {s.via}</span>
            </span>
          ))}
          <span className="inline-flex items-center gap-1.5 rounded-lg border border-d-claude/30 bg-d-claude/5 px-2.5 py-1 font-mono text-[11px] text-d-claude">
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            {t.reason_engine || "Reasoning"}
          </span>
        </div>
      </div>
    </div>
  );
}
