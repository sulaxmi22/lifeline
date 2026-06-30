import Disclaimer from "@/components/Disclaimer";
import IntakeForm from "@/components/IntakeForm";

export default function HomePage() {
  return (
    <main className="surface-paper">
      <Disclaimer />
      <div className="mx-auto max-w-3xl px-5 pb-20 pt-10 sm:pt-16">
        <header className="mb-10 text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-line bg-paper-2 px-4 py-1.5 text-[13px] font-medium text-pine-deep">
            <span className="h-2 w-2 rounded-full bg-eligible" />
            Live from ClinicalTrials.gov · 500,000+ studies
          </div>
          <h1 className="font-display text-5xl font-semibold leading-[1.05] tracking-tight text-ink sm:text-6xl">
            <span className="italic text-pine">Lifeline</span>
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-balance text-lg leading-relaxed text-ink-soft">
            Thousands of clinical trials. Dense, doctor-facing criteria. One
            specific person. Lifeline reads through it all and hands you a short,
            plain-language shortlist of trials you might qualify for —{" "}
            <span className="font-semibold text-ink">
              in under 90 seconds, instead of weeks.
            </span>
          </p>
        </header>

        <IntakeForm />

        <p className="mx-auto mt-10 max-w-lg text-center text-[13px] leading-relaxed text-ink-soft">
          Lifeline surfaces options to bring to your care team. It does not
          diagnose, treat, or replace professional medical judgment.
        </p>
      </div>
    </main>
  );
}
