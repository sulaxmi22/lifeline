"use client";

import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { startMatch } from "@/lib/api";
import { SEED_PROFILES, type SeedProfile } from "@/lib/seedProfiles";
import type { PatientProfile } from "@/lib/types";

const QUICK_CONDITIONS = ["breast cancer", "epilepsy", "type 2 diabetes"];

const fieldClass =
  "w-full rounded-xl border border-line bg-paper-2 px-4 py-3 text-ink placeholder:text-ink-soft/50 transition focus:border-pine focus:bg-white";
const labelClass = "mb-1.5 block text-sm font-semibold text-ink";

export default function IntakeForm() {
  const router = useRouter();
  const [age, setAge] = useState("");
  const [sex, setSex] = useState("");
  const [condition, setCondition] = useState("");
  const [location, setLocation] = useState("");
  const [treatments, setTreatments] = useState<string[]>([]);
  const [treatmentInput, setTreatmentInput] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function applySeed(seed: SeedProfile) {
    setAge(seed.age?.toString() ?? "");
    setSex(seed.sex ?? "");
    setCondition(seed.condition);
    setLocation(seed.location ?? "");
    setTreatments(seed.priorTreatments);
    setNotes(seed.notes ?? "");
    setError(null);
  }

  function addTreatment() {
    const t = treatmentInput.trim();
    if (t && !treatments.includes(t)) setTreatments([...treatments, t]);
    setTreatmentInput("");
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!condition.trim()) {
      setError("Please enter a condition to search for.");
      return;
    }
    setSubmitting(true);
    setError(null);
    const profile: PatientProfile = {
      age: age ? parseInt(age, 10) : null,
      sex: sex || null,
      condition: condition.trim(),
      location: location.trim() || null,
      priorTreatments: treatments,
      notes: notes.trim() || null,
    };
    try {
      sessionStorage.setItem("lifeline:profile", JSON.stringify(profile));
      const jobId = await startMatch(profile);
      router.push(`/processing?job=${jobId}`);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not reach the matching service. Is the backend running?"
      );
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-7">
      {/* Seed profiles */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.05 }}
      >
        <p className="mb-2.5 text-sm font-semibold uppercase tracking-wide text-ink-soft">
          Try an example
        </p>
        <div className="grid gap-3 sm:grid-cols-3">
          {SEED_PROFILES.map((seed) => (
            <button
              key={seed.label}
              type="button"
              onClick={() => applySeed(seed)}
              className="group rounded-2xl border border-line bg-paper-2 p-4 text-left transition hover:border-pine hover:bg-white hover:shadow-sm"
            >
              <span className="block font-display text-[15px] font-semibold leading-tight text-pine-deep">
                {seed.label}
              </span>
              <span className="mt-1 block text-[13px] text-ink-soft">
                {seed.blurb}
              </span>
            </button>
          ))}
        </div>
      </motion.div>

      <motion.form
        onSubmit={handleSubmit}
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.12 }}
        className="rounded-3xl border border-line bg-white/70 p-6 shadow-sm backdrop-blur-sm sm:p-8"
      >
        <div className="grid gap-5 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label className={labelClass} htmlFor="condition">
              Condition or diagnosis
            </label>
            <input
              id="condition"
              className={fieldClass}
              placeholder="e.g. breast cancer"
              value={condition}
              onChange={(e) => setCondition(e.target.value)}
              required
            />
            <div className="mt-2 flex flex-wrap gap-2">
              {QUICK_CONDITIONS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setCondition(c)}
                  className="rounded-full border border-line bg-paper px-3 py-1 text-[13px] text-ink-soft transition hover:border-sage hover:text-pine-deep"
                >
                  {c}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className={labelClass} htmlFor="age">
              Age
            </label>
            <input
              id="age"
              type="number"
              min={0}
              max={120}
              className={fieldClass}
              placeholder="e.g. 54"
              value={age}
              onChange={(e) => setAge(e.target.value)}
            />
          </div>

          <div>
            <label className={labelClass} htmlFor="sex">
              Sex
            </label>
            <select
              id="sex"
              className={fieldClass}
              value={sex}
              onChange={(e) => setSex(e.target.value)}
            >
              <option value="">Prefer not to say</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div className="sm:col-span-2">
            <label className={labelClass} htmlFor="location">
              Location
            </label>
            <input
              id="location"
              className={fieldClass}
              placeholder="e.g. San Jose, California"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            />
          </div>

          <div className="sm:col-span-2">
            <label className={labelClass} htmlFor="treatment">
              Prior treatments
            </label>
            <div className="flex gap-2">
              <input
                id="treatment"
                className={fieldClass}
                placeholder="Type a treatment and press Enter"
                value={treatmentInput}
                onChange={(e) => setTreatmentInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addTreatment();
                  }
                }}
              />
              <button
                type="button"
                onClick={addTreatment}
                className="shrink-0 rounded-xl border border-line bg-paper px-4 text-sm font-semibold text-pine-deep transition hover:border-pine"
              >
                Add
              </button>
            </div>
            {treatments.length > 0 && (
              <div className="mt-2.5 flex flex-wrap gap-2">
                {treatments.map((t) => (
                  <span
                    key={t}
                    className="inline-flex items-center gap-1.5 rounded-full bg-pine/10 px-3 py-1 text-[13px] font-medium text-pine-deep"
                  >
                    {t}
                    <button
                      type="button"
                      aria-label={`Remove ${t}`}
                      onClick={() =>
                        setTreatments(treatments.filter((x) => x !== t))
                      }
                      className="text-pine/60 hover:text-pine-deep"
                    >
                      ✕
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="sm:col-span-2">
            <label className={labelClass} htmlFor="notes">
              Key health notes
            </label>
            <textarea
              id="notes"
              rows={3}
              className={`${fieldClass} resize-none`}
              placeholder="Anything relevant — stage, biomarkers, other conditions…"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
        </div>

        {error && (
          <p className="mt-4 rounded-xl bg-apricot/10 px-4 py-3 text-sm text-apricot">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="mt-6 flex w-full items-center justify-center gap-2 rounded-2xl bg-pine px-6 py-4 text-lg font-semibold text-paper-2 transition hover:bg-pine-deep disabled:opacity-60"
        >
          {submitting ? "Searching trials…" : "Find my trials"}
          {!submitting && <span aria-hidden>→</span>}
        </button>
        <p className="mt-3 text-center text-[13px] text-ink-soft">
          We search live, currently-recruiting trials. Takes about 90 seconds.
        </p>
      </motion.form>
    </div>
  );
}
