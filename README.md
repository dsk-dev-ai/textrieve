<div align="center">

# textrieve

### Image & PDF → text, free & fully open source.

Drop in an image or a PDF — get clean text. **Offline OCR** on your own CPU, with a CLI, a REST API,
and a polished browser UI. No accounts, no API keys, no paywalls, nothing stored server-side.

[![Try it live](https://img.shields.io/badge/Try_it_live-textrieve.onrender.com-34d399?style=for-the-badge&logo=render&logoColor=white)](https://textrieve.onrender.com)
[![GitHub stars](https://img.shields.io/github/stars/dsk-dev-ai/textrieve?style=for-the-badge&logo=github&color=6c8cff)](https://github.com/dsk-dev-ai/textrieve)
[![Release](https://img.shields.io/github/v/release/dsk-dev-ai/textrieve?style=for-the-badge&color=0ea5e9)](https://github.com/dsk-dev-ai/textrieve/releases)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3178c6?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![CI](https://img.shields.io/github/actions/workflow/status/dsk-dev-ai/textrieve/ci.yml?branch=main&style=for-the-badge&logo=githubactions&label=CI)](https://github.com/dsk-dev-ai/textrieve/actions)
[![Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-6c8cff?style=for-the-badge)](LICENSE)

</div>

> **Status:** v1.2.0 — multi-page **PDF → text**, language hints, auto-expiring results (2 min), live progress bar.
> **Hosted:** [textrieve.onrender.com](https://textrieve.onrender.com) — UI + REST API on one free instance.

---

## Why textrieve?

| Pain point | textrieve solves it |
| --- | --- |
| Paid OCR APIs, usage quotas | **100% free** — RapidOCR (ONNX) runs locally, MIT-licensed engine, bundled models |
| Privacy leaks to third parties | Images never leave your machine / server — **no telemetry, no storage** |
| Account walls & signups | No accounts. `pip install`, run, done. |
| Janky one-off tools | A **real web UI**, a REST API, **and** a CLI in one repo |

---

## Contents

- [Quickstart](#quickstart)
- [Web UI](#web-ui)
- [REST API](#rest-api)
- [CLI](#cli)
- [Privacy & auto-expiry](#privacy--auto-expiry)
- [Free-tier deployment](#free-tier-deployment)
- [Memory management](#memory-management)
- [Tests](#tests)
- [Roadmap](#roadmap)
- [Support](#support)

---

## Quickstart

```bash
git clone https://github.com/dsk-dev-ai/textrieve
cd textrieve
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

uvicorn app:app --host 0.0.0.0 --port 8080
```

Open http://localhost:8080.

---

## Web UI

Drag and drop an image or PDF (or click to browse) → preview → **Extract text** → copy or download.

- Dark, responsive interface — works on desktop and mobile
- Live **progress bar** (percent + elapsed time) while text is extracted
- PDFs are extracted **page-by-page**, each one labelled `[Page N]`
- Live **2-minute countdown** on results; the page is wiped clean automatically
- Engine status indicator in the header; GitHub + Sponsor links in the footer
- No cookies, no tracking pixels, no third-party scripts

---

## REST API

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/health` | App version, OCR engine, live concurrency stats |
| `POST` | `/api/ocr` | Multipart `file` upload → text + confidence + timing |

```bash
curl -F "file=@photo.png" http://localhost:8080/api/ocr
curl -F "file=@scan.pdf" "http://localhost:8080/api/ocr?lang=en"   # PDF, language hint
```

```json
{
  "text": "HELLO TEXTRIEVE 2026",
  "confidence": 97.5,
  "engine": "RapidOCR (ONNX, CPU)",
  "duration_ms": 231.4
}
```

For PDFs the response also includes `"pages"` and the text is split with `[Page N]` markers.
The optional `lang` query hints the OCR engine (e.g. `en`, `ch`, `japan`, `korea`).

**Limits (free-tier friendly):** PNG / JPG / WEBP / BMP / TIFF / PDF · up to 12 MB · up to 25 PDF
pages · oversize or bad-type uploads rejected with clear HTTP errors (415 / 413 / 503 under load).

---

## CLI

```bash
python cli.py scans/receipt.jpg        # print extracted text
python cli.py scan.pdf --lang en       # OCR a PDF, hint the language
python cli.py a.png b.png --json      # machine-readable output
python cli.py ./documents/            # OCR every image/PDF in a folder
```

---

## Privacy & auto-expiry

- **Server-side:** each request is decoded, processed in memory, then released. Results are
  **never stored** — no database, no cache of extracted text.
- **Client-side:** extracted text is **automatically erased 2 minutes** after extraction
  (live countdown shown). Closing the tab clears everything.
- **Zero tracking:** no analytics scripts, no fingerprinting.

---

## Free-tier deployment

One free Render instance hosts **both** the web UI and the REST API — a static front-end
isn't needed.

### Render (UI + API in one service)

```
# 1. Use the included render.yaml
# 2. New → Blueprint → connect this repo → Deploy
```
Or manually: build `pip install -r requirements.txt`, start
`uvicorn app:app --host 0.0.0.0 --port $PORT --workers 1`, health check at `/api/health`.

`render.yaml` and a `Dockerfile` are included; the health check keeps the free instance awake
longer and restarts it cleanly after the idle timeout. The UI is plain HTML/CSS/JS served by
FastAPI — the front-end talks to the OCR API on the same origin.

**One-click deploy** (free tier):

[![Deploy to Render](https://img.shields.io/badge/Deploy_to-Render-46e3b7?style=for-the-badge&logo=render&logoColor=white)](https://render.com/deploy?repo=https://github.com/dsk-dev-ai/textrieve)

> **Honest note:** on Render's free tier a single CPU does roughly a few OCR passes per second
> max. The built-in concurrency guards (2 parallel inferences, bounded queue) keep it alive
> under bursts rather than letting memory pile up — a 1000-request/second crowd needs a paid
> instance, but a 1000+ **users** day flows through one free box fine. Free instances also spin
> down after ~15 minutes idle; the UI auto-retries the first cold request.

---

## Memory management

Optional — included by default:

- `ocr.py` releases the decoded image array immediately after inference and runs periodic GC
- Images larger than 4000 px or 4 Mpx are downscaled before OCR
- `app.py` limits concurrent ONNX inference to **2** and refuses (503) past a bounded queue —
  the process stays under ~512 MB on a busy day

---

## Tests

```bash
python -m pytest -q
```

The suite **generates its own fixture files** (no external sample downloads) and covers:
health, UI + favicon serving, real image and multi-page PDF OCR round-trips with confidence,
blank images, invalid/missing/oversized uploads, and CLI loading. Gated in CI (GitHub Actions, Python 3.11/3.12).

---

## Roadmap

- [ ] Batch queue in the web UI
- [ ] PaddleOCR engine switch (even higher accuracy)
- [ ] Searchable PDF export (text layer baked in)

---

## Support

Built by [@dsk-dev-ai](https://github.com/dsk-dev-ai). If textrieve saves you time,
sponsor the project:

[![Sponsor](https://img.shields.io/badge/Sponsor-GitHub%20Sponsors-34d399?style=for-the-badge&logo=github&logoColor=white)](https://github.com/sponsors/dsk-dev-ai)

---

## License

[Apache-2.0](LICENSE). The RapidOCR engine is MIT-licensed; its ONNX models are distributed on
an Apache-2.0 basis.