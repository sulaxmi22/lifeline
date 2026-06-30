"""ClinicalTrials.gov v2 ingestion + cache.

Live path verified during planning:
    GET https://clinicaltrials.gov/api/v2/studies
        ?query.cond=breast+cancer&filter.overallStatus=RECRUITING
        &pageSize=1000&countTotal=true&format=json
    -> {"totalCount": 2481, "studies": [...], "nextPageToken": "..."}

Resilience: any failure/timeout (or DEMO_MODE) falls back to a cached
backend/cache/trials_<condition>.json file shipped for the seed conditions.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

# NOTE: we use curl_cffi, NOT httpx/requests, for ClinicalTrials.gov.
# Its CDN blocks plain Python clients at the TLS-fingerprint (JA3) level —
# httpx gets a 403 challenge page even with a spoofed User-Agent. curl_cffi
# impersonates a real Chrome TLS handshake and is allowed through.
from curl_cffi.requests import AsyncSession

from .config import get_settings
from .models import Trial, TrialContact, TrialLocation

CTGOV_URL = "https://clinicaltrials.gov/api/v2/studies"
IMPERSONATE = "chrome"


def slugify(condition: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", condition.lower()).strip("_")
    return s or "unknown"


def cache_path(condition: str) -> Path:
    return get_settings().cache_dir / f"trials_{slugify(condition)}.json"


# --------------------------------------------------------------------------
# Flattening
# --------------------------------------------------------------------------
def _flatten_study(study: dict) -> Optional[Trial]:
    """Flatten one raw CT.gov study into our clean Trial model. Defensive."""
    ps = (study or {}).get("protocolSection") or {}
    ident = ps.get("identificationModule") or {}
    nct_id = ident.get("nctId")
    if not nct_id:
        return None

    status_mod = ps.get("statusModule") or {}
    design = ps.get("designModule") or {}
    conditions_mod = ps.get("conditionsModule") or {}
    elig = ps.get("eligibilityModule") or {}
    cl = ps.get("contactsLocationsModule") or {}
    desc = ps.get("descriptionModule") or {}

    phases = design.get("phases") or []
    phase = ", ".join(phases) if phases else None

    locations = []
    for loc in cl.get("locations") or []:
        if not isinstance(loc, dict):
            continue
        locations.append(
            TrialLocation(
                facility=loc.get("facility"),
                city=loc.get("city"),
                state=loc.get("state"),
                country=loc.get("country"),
            )
        )

    contacts = []
    for c in cl.get("centralContacts") or []:
        if not isinstance(c, dict):
            continue
        contacts.append(
            TrialContact(
                name=c.get("name"),
                phone=c.get("phone"),
                email=c.get("email"),
            )
        )

    hv = elig.get("healthyVolunteers")
    if isinstance(hv, str):
        hv = hv.strip().lower() in {"y", "yes", "true"}

    return Trial(
        nctId=nct_id,
        briefTitle=ident.get("briefTitle") or "",
        conditions=[c for c in (conditions_mod.get("conditions") or []) if c],
        phase=phase,
        status=status_mod.get("overallStatus"),
        eligibilityCriteria=elig.get("eligibilityCriteria") or "",
        minAge=elig.get("minimumAge"),
        maxAge=elig.get("maximumAge"),
        sex=elig.get("sex"),
        healthyVolunteers=hv if isinstance(hv, bool) else None,
        locations=locations,
        briefSummary=desc.get("briefSummary") or "",
        contacts=contacts,
    )


# --------------------------------------------------------------------------
# Live fetch
# --------------------------------------------------------------------------
async def fetch_live(
    condition: str,
    location: Optional[str] = None,
    max_trials: Optional[int] = None,
) -> tuple[list[Trial], int]:
    """Fetch recruiting trials live. Returns (trials, totalCount). Raises on failure."""
    settings = get_settings()
    max_trials = max_trials or settings.max_trials
    trials: list[Trial] = []
    total_count = 0
    page_token: Optional[str] = None

    async with AsyncSession() as client:
        while len(trials) < max_trials:
            params: dict[str, str] = {
                "query.cond": condition,
                "filter.overallStatus": "RECRUITING",
                "pageSize": "1000",
                "countTotal": "true",
                "format": "json",
            }
            if location:
                params["query.locn"] = location
            if page_token:
                params["pageToken"] = page_token

            resp = await client.get(
                CTGOV_URL,
                params=params,
                impersonate=IMPERSONATE,
                timeout=settings.ctgov_timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            if not total_count:
                total_count = int(data.get("totalCount") or 0)

            for study in data.get("studies") or []:
                t = _flatten_study(study)
                if t is not None:
                    trials.append(t)

            page_token = data.get("nextPageToken")
            if not page_token:
                break

    return trials[:max_trials], total_count


# --------------------------------------------------------------------------
# Cache
# --------------------------------------------------------------------------
def write_cache(condition: str, trials: list[Trial], total_count: int) -> Path:
    path = cache_path(condition)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "condition": condition,
        "totalCount": total_count,
        "trials": [t.model_dump() for t in trials],
    }
    path.write_text(json.dumps(payload, indent=2))
    return path


def read_cache(condition: str) -> Optional[tuple[list[Trial], int]]:
    path = cache_path(condition)
    if not path.exists():
        # Fall back to any available cache so a demo never hard-fails.
        existing = sorted(get_settings().cache_dir.glob("trials_*.json"))
        if not existing:
            return None
        path = existing[0]
    try:
        data = json.loads(path.read_text())
    except Exception:
        return None
    trials = [Trial(**t) for t in data.get("trials", [])]
    return trials, int(data.get("totalCount") or len(trials))


# --------------------------------------------------------------------------
# Public entrypoint used by the pipeline
# --------------------------------------------------------------------------
async def get_trials(
    condition: str,
    location: Optional[str] = None,
) -> tuple[list[Trial], int, str]:
    """Return (trials, totalCount, source). source = 'live' | 'cache'.

    Honors DEMO_MODE (forces cache) and degrades to cache on any live failure.
    """
    settings = get_settings()

    # Tier 0: Bright Data Web Unlocker (sponsor path) — additive, falls through.
    if settings.use_brightdata_fetch:
        try:
            from . import brightdata  # lazy import avoids a circular dependency

            trials, total = await brightdata.fetch_ctgov(condition, location)
            if trials:
                if not location:  # never let a location-filtered fetch clobber the broad cache
                    try:
                        write_cache(condition, trials, total)
                    except Exception:
                        pass
                return trials, total, "brightdata"
        except Exception as exc:  # noqa: BLE001 - degrade to direct live
            print(f"[ingest] Bright Data fetch failed ({exc!r}); falling back to direct live")

    if settings.use_live_ingest:
        try:
            trials, total = await fetch_live(condition, location)
            if trials:
                # Refresh the cache opportunistically — but only for broad (no-location)
                # queries, so a location-filtered fetch can't clobber the seed corpus.
                if not location:
                    try:
                        write_cache(condition, trials, total)
                    except Exception:
                        pass
                return trials, total, "live"
        except Exception as exc:  # noqa: BLE001 - degrade gracefully
            print(f"[ingest] live fetch failed ({exc!r}); falling back to cache")

    cached = read_cache(condition)
    if cached is None:
        return [], 0, "empty"
    trials, total = cached
    return trials, total, "cache"
