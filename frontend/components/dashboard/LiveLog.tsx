"use client";

import { useEffect, useRef } from "react";
import type { LogEvent } from "@/lib/types";

const LEVEL_COLOR: Record<string, string> = {
  info: "text-d-text",
  warn: "text-d-amber",
  error: "text-red-400",
};

/** Terminal-style live feed of exactly what the pipeline is doing, with real values. */
export default function LiveLog({ logs }: { logs: LogEvent[] }) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [logs.length]);

  return (
    <div className="rounded-2xl border border-d-line bg-black/40 p-4">
      <div className="mb-2 flex items-center gap-2">
        <span className="h-2 w-2 rounded-full bg-d-gpu animate-pulse-soft" />
        <h2 className="font-mono text-[12px] uppercase tracking-[0.2em] text-d-dim">
          Activity log
        </h2>
        <span className="ml-auto font-mono text-[10px] text-d-dim">
          {logs.length} events
        </span>
      </div>
      <div className="max-h-44 overflow-y-auto pr-1 font-mono text-[11.5px] leading-relaxed">
        {logs.length === 0 ? (
          <div className="text-d-dim">waiting for pipeline…</div>
        ) : (
          logs.map((l, i) => (
            <div key={i} className="flex gap-2 whitespace-pre-wrap">
              <span className="shrink-0 tabular-nums text-d-dim">
                {l.t.toFixed(1).padStart(5)}s
              </span>
              <span className={LEVEL_COLOR[l.level] || "text-d-text"}>{l.msg}</span>
            </div>
          ))
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}
