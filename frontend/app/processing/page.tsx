"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import EfficiencyPanel from "@/components/dashboard/EfficiencyPanel";
import InfraPanel from "@/components/dashboard/InfraPanel";
import LiveLog from "@/components/dashboard/LiveLog";
import MetricTiles from "@/components/dashboard/MetricTiles";
import PipelineBar from "@/components/dashboard/PipelineBar";
import WorkerGrid from "@/components/dashboard/WorkerGrid";
import WorkerTimeline from "@/components/dashboard/WorkerTimeline";
import { fetchConfig, streamUrl } from "@/lib/api";
import type {
  DonePayload,
  EfficiencyComparison,
  LogEvent,
  StageEvent,
  Telemetry,
  TickEvent,
} from "@/lib/types";

interface Live {
  workers: number;
  peak: number;
  trialsProcessed: number;
  trialsTotal: number;
  vectors: number;
  gpuCalls: number;
  gpuSeconds: number;
  cost: number;
  elapsed: number;
}

const ZERO: Live = {
  workers: 0,
  peak: 0,
  trialsProcessed: 0,
  trialsTotal: 0,
  vectors: 0,
  gpuCalls: 0,
  gpuSeconds: 0,
  cost: 0,
  elapsed: 0,
};

function Processing() {
  const router = useRouter();
  const params = useSearchParams();
  const job = params.get("job");
  const view = params.get("view"); // "last" => render the frozen snapshot

  const [stages, setStages] = useState<Record<string, StageEvent["status"]>>({});
  const [detail, setDetail] = useState("Connecting to the matching engine…");
  const [ticks, setTicks] = useState<{ t: number; workers: number }[]>([]);
  const [live, setLive] = useState<Live>(ZERO);
  const [logs, setLogs] = useState<LogEvent[]>([]);
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null);
  const [efficiency, setEfficiency] = useState<EfficiencyComparison | null>(null);
  const [mode, setMode] = useState<DonePayload["compute_metrics"]["mode"] | null>(null);
  const [maxWorkers, setMaxWorkers] = useState(8);
  const [finished, setFinished] = useState(false);
  const [resultsCount, setResultsCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const doneRef = useRef(false);
  const maxWorkersRef = useRef(8);

  useEffect(() => {
    fetchConfig().then((cfg) => {
      if (cfg) {
        setMaxWorkers(cfg.max_workers);
        maxWorkersRef.current = cfg.max_workers;
        setMode((m) => m ?? (cfg.use_flash ? "flash_live" : "demo_simulated"));
      }
    });
  }, []);

  useEffect(() => {
    // Revisit mode: re-render the last completed run from its stored snapshot.
    if (view === "last" || !job) {
      try {
        const raw = sessionStorage.getItem("lifeline:dashboard");
        if (raw) {
          const s = JSON.parse(raw);
          setStages(s.stages);
          setTicks(s.ticks);
          setLive(s.live);
          setLogs(s.logs || []);
          setTelemetry(s.telemetry || null);
          setEfficiency(s.efficiency);
          setMode(s.mode);
          setMaxWorkers(s.maxWorkers);
          setResultsCount(s.resultsCount);
          setDetail("Final run snapshot — review the compute story below.");
          setFinished(true);
          doneRef.current = true;
          return;
        }
      } catch {
        /* ignore */
      }
      setError(
        job ? "No matching job specified." : "No previous run to show. Start a new search."
      );
      return;
    }

    const es = new EventSource(streamUrl(job));

    es.addEventListener("stage", (e) => {
      const d: StageEvent = JSON.parse((e as MessageEvent).data);
      setStages((s) => ({ ...s, [d.stage]: d.status }));
      setDetail(d.detail);
    });

    es.addEventListener("tick", (e) => {
      const d: TickEvent = JSON.parse((e as MessageEvent).data);
      setTicks((t) => [...t, { t: d.t, workers: d.workers }]);
      setLive((prev) => ({
        ...prev,
        workers: d.workers,
        peak: Math.max(prev.peak, d.peak_workers),
        trialsProcessed: Math.max(prev.trialsProcessed, d.trials_processed),
        vectors: Math.max(prev.vectors, d.gpu_work_items ?? 0),
        gpuCalls: Math.max(prev.gpuCalls, d.gpu_calls ?? 0),
        gpuSeconds: d.gpu_seconds_est,
        cost: d.cost_est,
        elapsed: d.elapsed,
      }));
    });

    es.addEventListener("log", (e) => {
      const d: LogEvent = JSON.parse((e as MessageEvent).data);
      setLogs((prev) => [...prev, d]);
    });

    es.addEventListener("done", (e) => {
      doneRef.current = true;
      const d: DonePayload = JSON.parse((e as MessageEvent).data);
      sessionStorage.setItem("lifeline:results", (e as MessageEvent).data);
      const cm = d.compute_metrics;
      const finalStages = {
        ingest: "complete" as const,
        embed: "complete" as const,
        rerank: "complete" as const,
        reason: "complete" as const,
        done: "complete" as const,
      };
      const finalLive: Live = {
        workers: 0,
        peak: cm.peak_workers,
        trialsProcessed: cm.trials_processed,
        trialsTotal: cm.trials_total_available,
        vectors: cm.gpu_work_items,
        gpuCalls: cm.batch_count,
        gpuSeconds: cm.gpu_seconds_est,
        cost: cm.cost_est,
        elapsed: cm.elapsed_s,
      };
      setMode(cm.mode);
      setEfficiency(cm.efficiency);
      setTelemetry(cm.telemetry);
      setStages(finalStages);
      setLive(finalLive);
      setResultsCount(d.results.length);
      setLogs((prevLogs) => {
        setTicks((t) => {
          const finalTicks = [...t, { t: cm.elapsed_s, workers: 0 }];
          // Snapshot the whole dashboard so it can be revisited (?view=last).
          sessionStorage.setItem(
            "lifeline:dashboard",
            JSON.stringify({
              stages: finalStages,
              ticks: finalTicks,
              live: finalLive,
              logs: prevLogs,
              telemetry: cm.telemetry,
              efficiency: cm.efficiency,
              mode: cm.mode,
              maxWorkers: maxWorkersRef.current,
              resultsCount: d.results.length,
            })
          );
          return finalTicks;
        });
        return prevLogs;
      });
      setFinished(true);
      es.close();
      // No auto-redirect — the user dwells on the compute story and clicks through.
    });

    es.addEventListener("error", (e) => {
      const me = e as MessageEvent;
      if (me.data) {
        setError(JSON.parse(me.data).message || "Matching failed.");
        doneRef.current = true;
        es.close();
      }
    });

    es.onerror = () => {
      if (doneRef.current) return;
      if (es.readyState === EventSource.CLOSED) {
        setError(
          "Lost connection to the matching service. Is the backend running on port 8000?"
        );
      }
    };

    return () => es.close();
  }, [job, view, router]);

  const isLive = mode === "flash_live";

  return (
    <main className="surface-dash text-d-text">
      <div className="mx-auto max-w-4xl px-5 py-8">
        {/* Header */}
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="font-display text-2xl font-semibold italic text-d-gpu">
              Lifeline
            </span>
            <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-d-dim">
              compute
            </span>
          </div>
          <div className="font-mono text-[13px] text-d-dim">
            elapsed{" "}
            <span className="text-d-text">{live.elapsed.toFixed(1)}s</span>
          </div>
        </div>

        {/* Mode banner */}
        <div
          className={`mb-5 flex items-center gap-3 rounded-2xl border px-4 py-3 ${
            isLive
              ? "border-d-gpu/40 bg-d-gpu/5"
              : "border-d-amber/40 bg-d-amber/5"
          }`}
        >
          <span
            className={`h-2.5 w-2.5 rounded-full ${
              isLive ? "bg-d-gpu animate-pulse-soft" : "bg-d-amber"
            }`}
          />
          <p className="m-0 text-[13px] leading-snug">
            {isLive ? (
              <>
                <span className="font-semibold text-d-gpu">
                  LIVE — real RunPod Flash workers.
                </span>{" "}
                Worker counts and timings below are live telemetry.
              </>
            ) : (
              <>
                <span className="font-semibold text-d-amber">
                  DEMO — representative Flash burst.
                </span>{" "}
                Trial counts and wall-clock are real; the worker animation is a
                representative profile. Add{" "}
                <span className="font-mono">RUNPOD_API_KEY</span> to light up live
                GPU workers.
              </>
            )}
          </p>
        </div>

        {/* When complete: stay here as long as you like, then click through. */}
        {finished && !error && (
          <Link
            href="/results"
            className="mb-5 flex items-center justify-center gap-2 rounded-2xl bg-d-gpu px-6 py-4 text-lg font-semibold text-d-bg transition hover:brightness-110 dash-glow"
          >
            See your {resultsCount} matched trials →
          </Link>
        )}

        {error ? (
          <div className="rounded-2xl border border-d-amber/40 bg-d-amber/5 p-6 text-center">
            <p className="font-semibold text-d-amber">{error}</p>
            <button
              onClick={() => router.push("/")}
              className="mt-4 rounded-xl border border-d-line px-4 py-2 text-sm text-d-text hover:bg-d-panel-2"
            >
              ← Back to search
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <PipelineBar stages={stages} />

            {/* Active detail */}
            <div className="flex items-center gap-2 px-1 font-mono text-[12px] text-d-dim">
              <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-d-gpu" />
              {finished
                ? "Complete — review the compute story below, then open your results."
                : detail}
            </div>

            <InfraPanel telemetry={telemetry} isLive={isLive} gpuCalls={live.gpuCalls} />

            <div className="grid gap-4 lg:grid-cols-2">
              <WorkerGrid
                workers={live.workers}
                maxWorkers={maxWorkers}
                finished={finished}
              />
              <WorkerTimeline ticks={ticks} maxWorkers={maxWorkers} />
            </div>

            <MetricTiles
              trialsProcessed={live.trialsProcessed}
              trialsTotal={live.trialsTotal}
              peakWorkers={live.peak}
              gpuSeconds={live.gpuSeconds}
              cost={live.cost}
              vectors={live.vectors}
              gpuCalls={live.gpuCalls}
            />

            <LiveLog logs={logs} />

            <EfficiencyPanel liveCost={live.cost} efficiency={efficiency} />
          </div>
        )}
      </div>
    </main>
  );
}

export default function ProcessingPage() {
  return (
    <Suspense
      fallback={
        <main className="surface-dash">
          <div className="px-5 py-24 text-center font-mono text-d-dim">
            Loading compute dashboard…
          </div>
        </main>
      }
    >
      <Processing />
    </Suspense>
  );
}
