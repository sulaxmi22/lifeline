"use client";

import { motion } from "framer-motion";
import VerdictBadge from "./VerdictBadge";
import type { MatchedTrial, TrialLocation } from "@/lib/types";

function locationLabel(loc: TrialLocation | null): string | null {
  if (!loc) return null;
  const parts = [loc.city, loc.state, loc.country].filter(Boolean);
  return parts.length ? parts.join(", ") : loc.facility || null;
}

export default function TrialCard({
  match,
  index,
}: {
  match: MatchedTrial;
  index: number;
}) {
  const { trial, eligibility, nearest_location } = match;
  const loc = locationLabel(nearest_location);
  const contact = trial.contacts.find((c) => c.phone || c.email);

  return (
    <motion.article
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: Math.min(index * 0.06, 0.5) }}
      className="overflow-hidden rounded-3xl border border-line bg-white shadow-sm"
    >
      <div className="grid gap-6 p-6 sm:grid-cols-[1fr_minmax(180px,220px)] sm:p-7">
        {/* Left: content */}
        <div className="min-w-0">
          <p className="mb-3 text-balance text-[15px] leading-relaxed text-ink">
            {eligibility.plain_language_summary}
          </p>

          <h2 className="font-display text-xl font-semibold leading-snug text-pine-deep">
            {trial.briefTitle}
          </h2>

          <div className="mt-2.5 flex flex-wrap items-center gap-2 text-[13px]">
            {trial.phase && trial.phase !== "NA" && (
              <span className="rounded-full bg-pine/10 px-2.5 py-0.5 font-medium text-pine-deep">
                {trial.phase.replace(/PHASE/gi, "Phase ")}
              </span>
            )}
            <span className="inline-flex items-center gap-1.5 rounded-full bg-eligible-bg px-2.5 py-0.5 font-medium text-eligible">
              <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-eligible" />
              Recruiting
            </span>
            {loc && <span className="text-ink-soft">📍 {loc}</span>}
          </div>

          {eligibility.reasons_for.length > 0 && (
            <div className="mt-5">
              <p className="text-[13px] font-semibold uppercase tracking-wide text-eligible">
                Why you might qualify
              </p>
              <ul className="mt-1.5 space-y-1.5">
                {eligibility.reasons_for.map((r, i) => (
                  <li key={i} className="flex gap-2 text-[14px] text-ink">
                    <span className="mt-0.5 shrink-0 text-eligible">✓</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {eligibility.reasons_against.length > 0 && (
            <div className="mt-4">
              <p className="text-[13px] font-semibold uppercase tracking-wide text-possible">
                Why you might not
              </p>
              <ul className="mt-1.5 space-y-1.5">
                {eligibility.reasons_against.map((r, i) => (
                  <li key={i} className="flex gap-2 text-[14px] text-ink-soft">
                    <span className="mt-0.5 shrink-0 text-possible">!</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {match.enrichment?.items?.length ? (
            <div className="mt-5 rounded-2xl border border-line bg-paper/60 p-4">
              <p className="flex items-center gap-1.5 text-[12px] font-semibold uppercase tracking-wide text-ink-soft">
                Recent context
                <span className="rounded bg-sage/20 px-1.5 py-0.5 text-[10px] font-medium normal-case text-pine-deep">
                  via Bright Data
                </span>
              </p>
              <ul className="mt-2 space-y-2">
                {match.enrichment.items.map((it, i) => (
                  <li key={i} className="text-[13px] leading-snug">
                    <a
                      href={it.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-medium text-pine underline-offset-2 hover:underline"
                    >
                      {it.title}
                    </a>
                    {it.snippet && (
                      <p className="mt-0.5 line-clamp-2 text-ink-soft">{it.snippet}</p>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>

        {/* Right: verdict + next steps */}
        <div className="flex flex-col gap-4 border-t border-line pt-5 sm:border-l sm:border-t-0 sm:pl-6 sm:pt-0">
          <VerdictBadge
            verdict={eligibility.verdict}
            confidence={eligibility.confidence}
          />

          <div className="rounded-2xl bg-paper p-4">
            <p className="text-[13px] font-semibold text-ink">What to do next</p>
            <p className="mt-1 text-[13px] leading-relaxed text-ink-soft">
              Bring this trial to your doctor to confirm whether it&apos;s right
              for you.
            </p>
            <a
              href={`https://clinicaltrials.gov/study/${trial.nctId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 flex items-center justify-center gap-1.5 rounded-xl bg-pine px-3 py-2.5 text-[13px] font-semibold text-paper-2 transition hover:bg-pine-deep"
            >
              View official trial page →
            </a>
            <p className="mt-2 text-center font-mono text-[11px] text-ink-soft">
              {trial.nctId}
            </p>
            {contact && (
              <div className="mt-3 border-t border-line pt-3 text-[12px] text-ink-soft">
                <p className="font-semibold text-ink">Study contact</p>
                {contact.name && <p>{contact.name}</p>}
                {contact.phone && <p className="font-mono">{contact.phone}</p>}
                {contact.email && (
                  <p className="truncate font-mono">{contact.email}</p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.article>
  );
}
