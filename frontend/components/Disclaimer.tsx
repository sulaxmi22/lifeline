export default function Disclaimer() {
  return (
    <div
      role="note"
      aria-label="Medical disclaimer"
      className="sticky top-0 z-50 border-b border-pine-deep/30 bg-pine-deep text-paper-2"
    >
      <div className="mx-auto flex max-w-5xl items-center gap-3 px-5 py-2.5 text-[13px] leading-snug">
        <span
          aria-hidden
          className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-apricot-soft/60 text-apricot-soft"
        >
          !
        </span>
        <p className="m-0">
          <span className="font-semibold text-apricot-soft">
            Lifeline is an information tool, not medical advice.
          </span>{" "}
          Always confirm eligibility and decisions with a licensed clinician. We
          never diagnose or recommend treatment — only surface options to discuss
          with your doctor.
        </p>
      </div>
    </div>
  );
}
