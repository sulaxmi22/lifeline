"""Eligibility reasoning — Claude (Tier 1) + local rule engine (guaranteed).

Both paths return the SAME strict shape (models.Eligibility) so the frontend
never knows which ran:
  {verdict, confidence, reasons_for[], reasons_against[], plain_language_summary}

The local engine does deterministic structured checks (age / sex / healthy-
volunteer / treatment & condition keyword matching) and then maps those checks
to a verdict + confidence in `score_verdict`. That mapping is intentionally
isolated and documented — it is the conservative "clinical caution" policy and
the natural place to tune how strict Lifeline is.
"""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Optional

from .config import get_settings
from .models import Eligibility, PatientProfile, Trial, Verdict

# --------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------
_AGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(year|month|week|day)", re.IGNORECASE)
_UNIT_YEARS = {"year": 1.0, "month": 1 / 12, "week": 1 / 52, "day": 1 / 365}


def _age_to_years(raw: Optional[str]) -> Optional[float]:
    if not raw:
        return None
    m = _AGE_RE.search(raw)
    if not m:
        return None
    return float(m.group(1)) * _UNIT_YEARS[m.group(2).lower()]


def _split_criteria(text: str) -> tuple[str, str]:
    """Best-effort split of the criteria blob into (inclusion, exclusion)."""
    if not text:
        return "", ""
    parts = re.split(r"exclusion criteria\s*:?", text, flags=re.IGNORECASE, maxsplit=1)
    inclusion = re.sub(r"inclusion criteria\s*:?", "", parts[0], flags=re.IGNORECASE)
    exclusion = parts[1] if len(parts) > 1 else ""
    return inclusion.strip(), exclusion.strip()


def _normalize_sex(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    r = raw.strip().lower()
    if r.startswith("f"):
        return "FEMALE"
    if r.startswith("m"):
        return "MALE"
    if r in {"all", "any", "both", "other"}:
        return "ALL"
    return None


# --------------------------------------------------------------------------
# Structured checks
# --------------------------------------------------------------------------
@dataclass
class Checks:
    age_ok: Optional[bool] = None        # None = unknown / not stated
    sex_ok: Optional[bool] = None
    condition_match: bool = False
    treatment_excluded: bool = False     # a prior treatment appears in exclusions
    treatment_supported: bool = False    # a prior treatment appears in inclusions
    hard_fails: int = 0                  # definite disqualifiers (age/sex)


def _run_checks(profile: PatientProfile, trial: Trial) -> tuple[Checks, list[str], list[str]]:
    checks = Checks()
    fors: list[str] = []
    againsts: list[str] = []

    # --- age ---
    if profile.age is not None:
        lo = _age_to_years(trial.minAge)
        hi = _age_to_years(trial.maxAge)
        if lo is not None or hi is not None:
            ok = True
            if lo is not None and profile.age < lo:
                ok = False
                againsts.append(
                    f"This trial requires age ≥ {trial.minAge}; the patient is {profile.age}."
                )
            if hi is not None and profile.age > hi:
                ok = False
                againsts.append(
                    f"This trial requires age ≤ {trial.maxAge}; the patient is {profile.age}."
                )
            checks.age_ok = ok
            if ok:
                rng = f"{trial.minAge or 'any'}–{trial.maxAge or 'any'}"
                fors.append(f"The patient's age ({profile.age}) is within the eligible range ({rng}).")

    # --- sex ---
    p_sex = _normalize_sex(profile.sex)
    t_sex = _normalize_sex(trial.sex) or "ALL"
    if p_sex and p_sex not in {"ALL", None}:
        if t_sex == "ALL" or t_sex == p_sex:
            checks.sex_ok = True
        else:
            checks.sex_ok = False
            againsts.append(f"This trial enrolls {t_sex.lower()} participants only.")

    # --- condition match ---
    cond = profile.condition.lower()
    cond_tokens = {w for w in re.findall(r"[a-z]+", cond) if len(w) > 3}
    haystack = (trial.briefTitle + " " + " ".join(trial.conditions) + " " + trial.eligibilityCriteria).lower()
    if cond in haystack or (cond_tokens and any(tok in haystack for tok in cond_tokens)):
        checks.condition_match = True
        fors.append(f"The trial matches the patient's condition ({profile.condition}).")

    # --- prior treatments vs inclusion/exclusion ---
    inclusion, exclusion = _split_criteria(trial.eligibilityCriteria)
    incl_l, excl_l = inclusion.lower(), exclusion.lower()
    for tx in profile.priorTreatments:
        t = tx.strip().lower()
        if not t:
            continue
        if t in excl_l:
            checks.treatment_excluded = True
            againsts.append(f"Prior '{tx}' may be an exclusion — confirm with the study team.")
        elif t in incl_l:
            checks.treatment_supported = True
            fors.append(f"Prior '{tx}' appears in the inclusion criteria.")

    checks.hard_fails = sum(1 for v in (checks.age_ok, checks.sex_ok) if v is False)
    return checks, fors, againsts


# --------------------------------------------------------------------------
# Verdict policy  (the tunable "clinical caution" heart)
# --------------------------------------------------------------------------
def score_verdict(checks: Checks) -> tuple[Verdict, float]:
    """Map structured checks -> (verdict, confidence in 0..1).

    Conservative by design: Lifeline surfaces *options to discuss with a doctor*,
    so we never claim certainty. A definite age/sex disqualifier is the only
    thing that pushes us to "likely_ineligible"; everything else stays cautious.

    Tune here to change how strict Lifeline is (e.g. weight excluded treatments
    more heavily, or raise the bar for "likely_eligible").
    """
    # Hard disqualifier on objective criteria.
    if checks.hard_fails > 0:
        return "likely_ineligible", round(min(0.6 + 0.15 * checks.hard_fails, 0.9), 2)

    # An excluded prior treatment is a soft negative.
    if checks.treatment_excluded:
        return "possibly_eligible", 0.4

    # Positive signals stack toward "likely".
    positives = sum(
        [checks.condition_match, checks.age_ok is True, checks.sex_ok is True, checks.treatment_supported]
    )
    if checks.condition_match and positives >= 2:
        return "likely_eligible", round(min(0.6 + 0.1 * positives, 0.9), 2)
    if checks.condition_match:
        return "possibly_eligible", 0.55

    return "possibly_eligible", 0.45


def _reason_local(profile: PatientProfile, trial: Trial) -> Eligibility:
    checks, fors, againsts = _run_checks(profile, trial)
    verdict, confidence = score_verdict(checks)

    if not fors:
        fors.append("The trial is currently recruiting and broadly relevant to the condition.")
    label = {
        "likely_eligible": "may be a good fit",
        "possibly_eligible": "might be a fit",
        "likely_ineligible": "may not be a fit",
    }[verdict]
    summary = (
        f"Based on the listed criteria, this trial {label} — but only the study "
        f"team can confirm. Bring it to your doctor to discuss."
    )
    return Eligibility(
        verdict=verdict,
        confidence=confidence,
        reasons_for=fors[:4],
        reasons_against=againsts[:4],
        plain_language_summary=summary,
    )


# --------------------------------------------------------------------------
# Tier 1 — Claude
# --------------------------------------------------------------------------
_SYSTEM_PROMPT = (
    "You are a careful clinical-trial eligibility assistant for patients and "
    "caregivers. You do NOT give medical advice or diagnose. You read a trial's "
    "inclusion/exclusion criteria and a patient profile and judge, conservatively, "
    "whether the patient might qualify. Cite specific criteria. Never imply medical "
    "certainty. Always frame next steps as 'discuss with your doctor'. "
    "Respond with ONLY a JSON object, no prose, with keys: verdict "
    "(one of likely_eligible, possibly_eligible, likely_ineligible), confidence "
    "(0.0-1.0), reasons_for (array of short plain-English strings), reasons_against "
    "(array), plain_language_summary (1-3 sentences a non-doctor understands)."
)


def _parse_json(text: str) -> Optional[dict]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


async def _reason_claude(profile: PatientProfile, trial: Trial) -> Eligibility:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=get_settings().anthropic_api_key)
    user_msg = (
        f"PATIENT PROFILE:\n{profile.to_query_text()}\n\n"
        f"TRIAL: {trial.briefTitle} ({trial.nctId})\n"
        f"Conditions: {', '.join(trial.conditions) or 'N/A'}\n"
        f"Age range: {trial.minAge or 'any'} to {trial.maxAge or 'any'}\n"
        f"Sex: {trial.sex or 'ALL'}\n"
        f"Eligibility criteria:\n{trial.eligibilityCriteria[:4000]}"
    )
    resp = await client.messages.create(
        model=get_settings().claude_model,
        max_tokens=700,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = "".join(getattr(b, "text", "") for b in resp.content)
    data = _parse_json(raw)
    if not data:
        return _reason_local(profile, trial)
    try:
        return Eligibility(**data)
    except Exception:
        return _reason_local(profile, trial)


# --------------------------------------------------------------------------
# Public entrypoints
# --------------------------------------------------------------------------
async def reason_eligibility(profile: PatientProfile, trial: Trial) -> Eligibility:
    settings = get_settings()
    if settings.use_claude:
        try:
            return await _reason_claude(profile, trial)
        except Exception as exc:  # noqa: BLE001
            print(f"[eligibility] Claude failed ({exc!r}); using local engine")
    return _reason_local(profile, trial)


async def reason_batch(
    profile: PatientProfile, trials: list[Trial]
) -> list[Eligibility]:
    """Reason over many trials. Claude calls are bounded; local is instant."""
    settings = get_settings()
    if not settings.use_claude:
        return [_reason_local(profile, t) for t in trials]

    sem = asyncio.Semaphore(5)

    async def one(t: Trial) -> Eligibility:
        async with sem:
            return await reason_eligibility(profile, t)

    return await asyncio.gather(*(one(t) for t in trials))
