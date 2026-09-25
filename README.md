<div align="center">

# textrieve

### Image → text, free & fully open source.

Drop in an image — get clean text. **Offline OCR** on your own CPU, with a CLI, a REST API,
and a polished browser UI. No accounts, no API keys, no paywalls, nothing stored server-side.

![OCR](https://img.shields.io/badge/OCR-RapidOCR%20(ONNX)-34d399?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-Apache--2.0-6c8cff?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10%2B-3178c6?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![No API keys](https://img.shields.io/badge/No%20API%20keys-Yes-38bdf8?style=for-the-badge)

</div>

> **Status:** v1.1.0 — add auto-expiring results (2 min), free-tier memory guards, favicon + UI polish.

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

- [Quickstart](#-quickstart)
- [Web UI](#-web-ui)
- [REST API](#-rest-api)
- [CLI](#-cli)
- [Privacy & auto-expiry](#-privacy--auto-expiry)
- [Free-tier deployment](#-free-tier-deployment)
- [Memory management](#-memory-management)
- [Tests](#-tests)
- [Roadmap](#-roadmap)
- [Support](#-support)

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

Drag and drop an image (or click to browse) → preview → **Extract text** → copy or download.

- Dark, responsive interface — works on desktop and mobile
- Live **2-minute countdown** on results; text is wiped from the page automatically
- Engine status indicator in the header
- No cookies, no tracking pixels, no third-party scripts

---

## REST API

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/health` | App version, OCR engine, live concurrency stats |
| `POST` | `/api/ocr` | Multipart `file` upload → text + confidence + timing |

```bash
curl -F "file=@photo.png" http://localhost:8080/api/ocr
```

```json
{
  "text": "HELLO TEXTRIEVE 2026",
  "confidence": 97.5,
  "engine": "RapidOCR (ONNX, CPU)",
  "duration_ms": 231.4
}
```

**Limits (free-tier friendly):** PNG / JPG / WEBP / BMP / TIFF · up to 12 MB · oversize or
bad-type uploads rejected with clear HTTP errors (415 / 413 / 503 under load).

---

## CLI

```bash
python cli.py scans/receipt.jpg        # print extracted text
python cli.py a.png b.png --json      # machine-readable output
python cli.py ./documents/            # OCR every image in a folder
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

Perfect for Render (free tier, 512 MB) and Vercel.

### Render (API + full app)

```
# 1. Use the included render.yaml
# 2. New → Blueprint → connect this repo → Deploy
```
Or manually: build `pip install -r requirements.txt`, start
`uvicorn app:app --host 0.0.0.0 --port $PORT --workers 1`, health check at `/api/health`.

`render.yaml` and a `Dockerfile` are included; the health check keeps the free instance awake
longer and restarts it cleanly after the idle timeout.

### Vercel (static front-end only)

The web folder is plain HTML/CSS/JS — point a Vercel static project at `web/` for the UI, and
point `app.js` at a hosted instance for the OCR API.

> **Honest note:** on Render's free tier a single CPU does roughly a few OCR passes per second
> max. The built-in concurrency guards (2 parallel inferences, bounded queue) keep it alive
> under bursts rather than letting memory pile up — a 1000-request/second crowd needs a paid
> instance, but a 1000+ **users** day flows through one free box fine.

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
pytest -q
```

The suite **generates its own fixture images** (no external sample downloads) and covers:
health, UI + favicon serving, real OCR round-trip with confidence, blank images,
invalid/missing/oversized uploads, and CLI loading. Gated in CI (GitHub Actions, Python 3.11/3.12).

---

## Roadmap

- [ ] PDF → text (multi-page)
- [ ] Language hints + CJK/Latin switches
- [ ] Batch queue in the web UI
- [ ] PaddleOCR engine switch (even higher accuracy)

---

## Support

Built by [@dsk-dev-ai](https://github.com/dsk-dev-ai). If textrieve saves you time,
sponsor the project:

[![Sponsor](https://img.shields.io/badge/Sponsor-GitHub%20Sponsors-34d399?style=for-the-badge&logo=github&logoColor=white)](https://github.com/sponsors/dsk-dev-ai)

---

## License

[Apache-2.0](LICENSE). The RapidOCR engine is MIT-licensed; its ONNX models are distributed on
an Apache-2.0 basis.