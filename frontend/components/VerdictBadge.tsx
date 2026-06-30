import type { Verdict } from "@/lib/types";

const CONFIG: Record<
  Verdict,
  { label: string; text: string; bg: string; dot: string }
> = {
  likely_eligible: {
    label: "Likely eligible",
    text: "text-eligible",
    bg: "bg-eligible-bg",
    dot: "bg-eligible",
  },
  possibly_eligible: {
    label: "Possibly eligible",
    text: "text-possible",
    bg: "bg-possible-bg",
    dot: "bg-possible",
  },
  likely_ineligible: {
    label: "Likely not a fit",
    text: "text-unlikely",
    bg: "bg-unlikely-bg",
    dot: "bg-unlikely",
  },
};

export default function VerdictBadge({
  verdict,
  confidence,
}: {
  verdict: Verdict;
  confidence: number;
}) {
  const c = CONFIG[verdict];
  const pct = Math.round(confidence * 100);
  return (
    <div className={`rounded-2xl ${c.bg} px-4 py-3`}>
      <div className={`flex items-center gap-2 ${c.text}`}>
        <span className={`h-2.5 w-2.5 rounded-full ${c.dot}`} />
        <span className="font-display text-lg font-semibold leading-none">
          {c.label}
        </span>
      </div>
      <div className="mt-2.5">
        <div className="flex items-center justify-between text-[11px] font-medium uppercase tracking-wide opacity-70">
          <span className={c.text}>Confidence</span>
          <span className={`font-mono ${c.text}`}>{pct}%</span>
        </div>
        <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-black/10">
          <div
            className={`h-full rounded-full ${c.dot}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  );
}
