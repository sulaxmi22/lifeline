"""Bright Data integration — additive, fully fallback-safe.

Two uses (both optional; either degrades to nothing if unconfigured/failing):
  1. Fetch layer  — pull ClinicalTrials.gov through the Web Unlocker API
     (api.brightdata.com/request), getting past anti-bot defenses.
  2. Enrichment   — SERP API lookups to attach recent web context to top trials.

Requires a Bright Data API key + the matching ZONE names from your dashboard
(BRIGHTDATA_ZONE for Web Unlocker, BRIGHTDATA_SERP_ZONE for SERP). If a zone is
wrong or a call fails, every function returns None / raises and the caller falls
back to the existing path — nothing breaks.
"""
from __future__ import annotations

import json
from typing import Optional
from urllib.parse import quote_plus, urlencode

from curl_cffi.requests import AsyncSession

from .config import get_settings
from .ingest import CTGOV_URL, _flatten_study
from .models import Trial

BRIGHTDATA_URL = "https://api.brightdata.com/request"


async def _request(zone: str, url: str, timeout: float = 30.0) -> Optional[str]:
    """Single Web Unlocker / SERP request. Returns raw body or None on any failure."""
    s = get_settings()
    if not (s.brightdata_api_key and zone):
        return None
    payload = {"zone": zone, "url": url, "format": "raw"}
    headers = {
        "Authorization": f"Bearer {s.brightdata_api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with AsyncSession() as client:
            r = await client.post(BRIGHTDATA_URL, json=payload, headers=headers, timeout=timeout)
        if r.status_code != 200 or not r.text:
            return None
        return r.text
    except Exception:  # noqa: BLE001 - degrade silently; caller falls back
        return None


# --------------------------------------------------------------------------
# 1) Fetch layer — CT.gov via Web Unlocker
# --------------------------------------------------------------------------
async def fetch_ctgov(
    condition: str,
    location: Optional[str] = None,
    max_trials: Optional[int] = None,
) -> tuple[list[Trial], int]:
    """Fetch recruiting trials via Bright Data. Raises on failure (caller falls back)."""
    s = get_settings()
    max_trials = max_trials or s.max_trials
    trials: list[Trial] = []
    total = 0
    page_token: Optional[str] = None

    while len(trials) < max_trials:
        params = {
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

        raw = await _request(s.brightdata_zone, f"{CTGOV_URL}?{urlencode(params)}")
        if raw is None:
            raise RuntimeError("Bright Data Web Unlocker request failed")
        data = json.loads(raw)

        if not total:
            total = int(data.get("totalCount") or 0)
        for study in data.get("studies") or []:
            t = _flatten_study(study)
            if t is not None:
                trials.append(t)

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    if not trials:
        raise RuntimeError("Bright Data returned no trials")
    return trials[:max_trials], total


# --------------------------------------------------------------------------
# 2) Enrichment — SERP context for a trial
# --------------------------------------------------------------------------
async def serp_context(query: str, n: int = 2) -> Optional[list[dict]]:
    """Top organic web results for `query` via Bright Data SERP. None on failure."""
    s = get_settings()
    if not (s.brightdata_api_key and s.brightdata_serp_zone):
        return None
    # brd_json=1 asks the SERP API for structured JSON instead of raw HTML.
    url = f"https://www.google.com/search?q={quote_plus(query)}&brd_json=1&num=10"
    raw = await _request(s.brightdata_serp_zone, url, timeout=25.0)
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except Exception:  # noqa: BLE001
        return None
    organic = data.get("organic") or data.get("organic_results") or []
    out: list[dict] = []
    for item in organic[:n]:
        link = item.get("link") or item.get("url")
        title = item.get("title")
        if not (link and title):
            continue
        out.append({
            "title": title,
            "link": link,
            "snippet": item.get("description") or item.get("snippet") or "",
        })
    return out or None
