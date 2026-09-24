# textrieve

**Free, fully-open image-to-text (OCR).** Point `textrieve` at any image and get clean text back — via a
command-line tool, a REST API, or a browser UI. No accounts, no API keys, no paywalls, no third-party uploads.

OCR runs locally on CPU using **RapidOCR (ONNX)** — a free, MIT-licensed OCR engine with bundled models.

![engine](https://img.shields.io/badge/OCR-RapidOCR%20(ONNX)-34d399?style=flat-square)
![license](https://img.shields.io/badge/license-Apache--2.0-6c8cff?style=flat-square)
![python](https://img.shields.io/badge/python-3.10%2B-3178c6?style=flat-square)
![web](https://img.shields.io/badge/web-UI%20%2B%20API-38bdf8?style=flat-square)

## What you get

| Layer | What it does |
| --- | --- |
| **Web UI** | Drag-an-drop a browser UI — upload, live preview, one-click extract, copy / download |
| **REST API** | `POST /api/ocr` — send an image, get `text`, `confidence`, and timing as JSON |
| **CLI** | `textrieve photo.png` — reads one image, many images, or a folder; plain text or `--json` |
| **Engine** | RapidOCR (ONNX) on CPU — offline, free, no API key, bundled models (EN + Latin + CJK) |

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run the web app

```bash
uvicorn app:app --host 0.0.0.0 --port 8080
```

Open <http://localhost:8080>, drop an image, hit **Extract text**.

### Use the CLI

```bash
python cli.py receipts.jpg            # print text
python cli.py a.png b.png --json      # JSON output for two files
python cli.py ./scans/                # every image in a folder
```

### Call the API

```bash
curl -F "file=@photo.png" http://localhost:8080/api/ocr
```

```json
{
  "text": "HELLO TEXTRIEVE 2026",
  "confidence": 98.7,
  "engine": "RapidOCR (ONNX, CPU)",
  "duration_ms": 231.4
}
```

## API reference

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/health` | App version + OCR engine status |
| `POST` | `/api/ocr` | Multipart `file` upload → `{text, confidence, engine, duration_ms}` |

Uploads: PNG, JPG, JPEG, WEBP, BMP, TIFF — up to 12 MB. Large images are downscaled before OCR.

## How it works

```
image → Pillow (decode + normalise) → RapidOCR ONNX (det + rec) → text + confidence
```

The engine stays warm in memory after the first request (`lru_cache`), so consecutive calls are fast.

## Tests

```bash
pytest -q
```

The suite generates its own fixture images (no external samples needed) and covers health, UI serving,
OCR round-trip, blank images, and API validation — gated in CI on every push (Python 3.11 / 3.12).

## Privacy & cost

- **Zero cost** — everything runs locally on your CPU.
- **Zero tracking** — your images never leave your machine (only the web UI needs the app to be running on it).
- This README's status badges are GitHub-hosted image badges, not tracking.

## License

[Apache-2.0](LICENSE). The underlying RapidOCR engine is MIT-licensed and distributes its ONNX models
under the Apache-2.0 license.