"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { useEffect, useState } from "react";
import Disclaimer from "@/components/Disclaimer";
import TrialCard from "@/components/TrialCard";
import type { DonePayload } from "@/lib/types";

export default function ResultsPage() {
  const [data, setData] = useState<DonePayload | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("lifeline:results");
      if (raw) setData(JSON.parse(raw));
    } catch {
      /* ignore */
    }
    setLoaded(true);
  }, []);

  if (loaded && !data) {
    return (
      <main className="surface-paper">
        <Disclaimer />
        <div className="mx-auto max-w-2xl px-5 py-24 text-center">
          <h1 className="font-display text-3xl font-semibold text-ink">
            No results to show yet
          </h1>
          <p className="mt-3 text-ink-soft">
            Start a new search to find trials you might qualify for.
          </p>
          <Link
            href="/"
            className="mt-6 inline-block rounded-2xl bg-pine px-6 py-3 font-semibold text-paper-2 transition hover:bg-pine-deep"
          >
            ← Start a new search
          </Link>
        </div>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="surface-paper">
        <Disclaimer />
        <div className="mx-auto max-w-2xl px-5 py-24 text-center text-ink-soft">
          Loading your results…
        </div>
      </main>
    );
  }

  const { results, searched_count, profile } = data;

  return (
    <main className="surface-paper">
      <Disclaimer />
      <div className="mx-auto max-w-4xl px-5 pb-24 pt-10">
        <motion.header
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-8"
        >
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="text-[13px] font-medium text-pine-deep hover:underline"
            >
              ← New search
            </Link>
            <Link
              href="/processing?view=last"
              className="text-[13px] font-medium text-ink-soft hover:text-pine-deep hover:underline"
            >
              View compute dashboard ↗
            </Link>
          </div>
          <h1 className="mt-3 text-balance font-display text-3xl font-semibold leading-tight text-ink sm:text-4xl">
            We searched{" "}
            <span className="text-pine">
              {searched_count.toLocaleString()} active trials
            </span>{" "}
            and found these {results.length} to ask your doctor about.
          </h1>
          {profile?.condition && (
            <p className="mt-3 text-ink-soft">
              For {profile.age ? `${profile.age}-year-old ` : ""}
              {profile.sex && profile.sex !== "other" ? `${profile.sex}, ` : ""}
              {profile.condition}
              {profile.location ? ` · near ${profile.location}` : ""}
            </p>
          )}
        </motion.header>

        <div className="space-y-5">
          {results.map((m, i) => (
            <TrialCard key={m.trial.nctId} match={m} index={i} />
          ))}
        </div>

        <p className="mx-auto mt-10 max-w-xl text-center text-[13px] leading-relaxed text-ink-soft">
          These matches are a starting point, not medical advice. Eligibility is
          decided by each study&apos;s team — confirm with a licensed clinician
          before making any decisions.
        </p>
      </div>
    </main>
  );
}
