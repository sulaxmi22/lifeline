# Lifeline → RunPod Flash: Go-Live Guide

This flips Lifeline's embed + rerank from the labeled **DEMO simulated burst** to **real RunPod
Flash GPU workers**, so the dashboard shows a genuine 0→8→0 scale-up. Follow top to bottom.

> The app already works end-to-end without any of this (DEMO mode). This guide is only to make
> RunPod *actually get hit* for the live demo.

---

## TL;DR (the whole sequence)

```bash
# from repo root: /Users/sulaxmi/Desktop/Claude Certification/Lifeline
source .venv/bin/activate
pip install runpod-flash                 # already done in this venv
export RUNPOD_API_KEY=rpa_xxxxxxxx       # your key (also put it in .env)
export FLASH_APP=lifeline FLASH_ENV=production
flash deploy                             # deploys lifeline-embed + lifeline-rerank
flash dev --auto-provision &             # pre-warm so first call isn't a cold start
python scripts/verify_flash.py           # GATE: must print ✅ PASS (mode=flash_live)
# edit .env -> DEMO_MODE=false, then restart the backend:
uvicorn backend.main:app --port 8000
```

---

## 1. Prerequisites (account side — only you can do these)

- **Add balance.** RunPod console → Billing → add ~$10. A full run costs ≈ **$0.003**, so this lasts
  the whole hackathon. **Flash will not start a worker at $0.00.**
- **Create an API key.** Console → Settings → **API keys** → Create → copy it.
- **Confirm Serverless/Flash is enabled** on the account (sign-up URL mentioned "early-access"). If
  `flash deploy` says it's not enabled, that's the toggle to find.

### Why the API key (not just `flash login`)
Lifeline's live-path switch is `use_flash = bool(RUNPOD_API_KEY) and not DEMO_MODE`
(see `backend/config.py`). So **`flash login` alone will NOT turn on the backend's live path** — the
backend keys off the `RUNPOD_API_KEY` env var. Setting `RUNPOD_API_KEY` does double duty: it flips our
switch **and** authenticates both the `flash` CLI (deploy) and the runtime SDK. Use the API key.

Put it in **`.env`** so the backend (uvicorn) sees it, and `export` it in whatever shell runs
`flash deploy`:

```bash
# .env
RUNPOD_API_KEY=rpa_xxxxxxxx
DEMO_MODE=false          # flip to false to go live (true = safe simulated demo)
FLASH_APP=lifeline
FLASH_ENV=production
```

Never paste the key into chat or commit `.env`.

---

## 2. Install the SDK (done, but for a fresh machine)

```bash
source .venv/bin/activate
pip install runpod-flash       # gives the `flash` CLI + the runpod_flash SDK
flash --version                # expect: Runpod Flash CLI v1.18.x
```
Until this is installed, `FLASH_AVAILABLE` is False and **everything falls back regardless of keys.**

---

## 3. Deploy the endpoints

```bash
export RUNPOD_API_KEY=rpa_xxxxxxxx
export FLASH_APP=lifeline FLASH_ENV=production
flash deploy
```

`flash deploy` scans the project for `@Endpoint` functions, finds **`lifeline-embed`** (RTX 4090,
0→8 workers) and **`lifeline-rerank`** (0→2 workers), bakes `sentence-transformers`+`torch` into the
worker image, and deploys both. Note the endpoint names/IDs it prints.

> **App/env consistency is the #1 silent failure.** The names `FLASH_APP`/`FLASH_ENV` used at deploy
> time MUST match what the backend uses at runtime (`.env`), because the SDK routes `await
> embed_batch()` by **implicit resolution** of app+env. Mismatch → the call silently falls back to
> local/tfidf and you'll wonder why the dashboard says DEMO.

---

## 4. Beat the cold start (important for a live demo)

A freshly-spun worker downloads the model weights (~440 MB for bge-base) on its **first** call —
that's 20–40s of dead air if it happens on stage. Two ways to avoid it:

- **Recommended — pre-warm, keep scale-to-zero:** run `flash dev --auto-provision` (or just run
  `scripts/verify_flash.py`) **within ~60s before** you demo. Flash's idle timeout is ~60s, so warm it
  right before. This preserves the satisfying scale-to-**zero** finale on the dashboard.
- **Safest — force a warm worker:** set `FLASH_MIN_WORKERS=1` in `.env` and restart. No cold start
  ever, but the dashboard won't drop to a true zero at the end (it bottoms out at 1). If you choose
  this, narrate "…and it scales to zero when idle" verbally. Set it back to `0` after the demo.

---

## 5. VERIFY — the pre-demo gate

```bash
python scripts/verify_flash.py
```

It calls the real embed + rerank wrappers and must print:

```
✅ PASS — RunPod Flash is genuinely being hit. Demo is live.
```

If it prints ❌ NOT LIVE, it tells you exactly what to fix. **Do not go on stage until this passes**
(or until you've consciously decided to demo in safe DEMO mode).

---

## 6. Flip live and run

```bash
# .env: DEMO_MODE=false  (RUNPOD_API_KEY set)
uvicorn backend.main:app --port 8000
# in another shell:
cd frontend && PORT=3000 npm run dev
```

Run a seed profile from the UI. On `/processing` you should now see the **live** banner (no "DEMO —
representative" label) and real worker bars lighting up. Confirm `compute_metrics.mode == "flash_live"`.

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `verify_flash.py` → mode `tfidf`/`local_cpu`, preflight shows `RUNPOD_API_KEY set: False` | env var not loaded | put key in `.env` AND restart the shell/uvicorn |
| Preflight OK but still falls back | endpoints not deployed, or app/env mismatch | re-run `flash deploy`; ensure `FLASH_APP`/`FLASH_ENV` identical at deploy + runtime |
| First call hangs ~30s then works | cold start (model download) | pre-warm (§4) right before demoing |
| `flash deploy` auth/enable error | not logged in / Serverless not enabled / $0 balance | set `RUNPOD_API_KEY`, add balance, enable Serverless |
| Backend errors on a Flash call | endpoint error | it auto-falls-back; dashboard shows the labeled simulated path — demo still runs |

### If implicit `await` routing doesn't work on your SDK build
Swap the call in `backend/flash_embed.py` (`embed_batch`) / `backend/flash_rerank.py` (`rerank_batch`)
for the explicit client:

```python
from runpod_flash import Endpoint
ep = Endpoint(name="lifeline-embed")          # or id="<deployed-id>"
out = await ep.run({"texts": batch})          # shape per your handler
```

### Worst case
Leave `DEMO_MODE=true`. The dashboard stays **honest** (clearly labeled simulated burst, real trial
counts + wall-clock). The demo never hard-fails.

---

## 8. Pre-demo 60-second checklist

1. `python scripts/verify_flash.py` → ✅ PASS (run it <60s before going up).
2. Backend up (`/api/health` shows `use_flash: true`), frontend up.
3. Browser on the intake page, seed profile visible.
4. Balance still > $0.

## 9. The 3-minute demo script

1. **(20s) Problem.** "ClinicalTrials.gov has 500,000 studies. A family facing a diagnosis can't read
   thousands of doctor-facing eligibility criteria. No human can reason over all of it for one person."
2. **(10s) One click.** Click the *Metastatic HER2+ breast cancer* seed profile → **Find my trials**.
3. **(45s) The compute story — point at the dashboard.** "Ingest is CPU. The embedding burst runs on
   RunPod Flash — watch it scale 0→8 GPU workers in parallel, then back to zero. We use GPUs only for
   the heavy embed/rerank, and Claude reasons over just the final 15. Right hardware per stage."
4. **(30s) The payoff — results.** "In seconds, a scared family gets a ranked, plain-language shortlist
   — why they might qualify, why not, the nearest site, and a link to bring to their doctor."
5. **(20s) The kill shot — efficiency panel.** "An always-on GPU is ~$17/day, idle 98% of the time.
   This run cost **$0.003** and scaled to zero. That's the workload Flash is built for — bursty,
   spiky, idle most of the time."

### One-liner if a judge asks "why RunPod, can't an LLM do this?"
> "Claude can't embed — it's a generator, not an encoder, and dumping thousands of trials into it is
> ~1M tokens per query. RunPod runs the right *encoder* model on GPUs to do breadth cheaply and in
> parallel, scales to zero when idle, and we reserve the expensive LLM for depth on the final 15."
