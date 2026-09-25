from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import anyio
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import ocr

APP_NAME = "textrieve"
VERSION = "1.2.1"
MAX_BYTES = 12 * 1024 * 1024
ALLOWED = {"png", "jpg", "jpeg", "webp", "bmp", "tiff", "tif", "pdf"}

# Free-tier safety: bound how many ONNX inferences run at once and how many
# requests are allowed to queue. Beyond the queue we return 503 instead of
# letting memory grow until the process dies. Tune via TEXTRIEVE_PERMITS.
OCR_PERMITS = int(os.environ.get("TEXTRIEVE_PERMITS", "2"))
MAX_QUEUE = 60
_sem = anyio.Semaphore(OCR_PERMITS)
_inflight = 0

app = FastAPI(
    title=APP_NAME,
    version=VERSION,
    description="Free, fully-open image-to-text (OCR). CLI, REST API, and a clean web UI.",
)


@app.get("/api/health")
def health() -> dict:
    return {
        "app": APP_NAME,
        "version": VERSION,
        "status": "ok",
        "engine": ocr.ENGINE,
        "concurrency": {"permits": OCR_PERMITS, "inflight": _inflight},
    }


@app.post("/api/ocr")
async def ocr_endpoint(
    file: UploadFile = File(...),
    lang: str | None = Query(
        default=None,
        description="Optional language hint for the OCR engine (e.g. 'en', 'ch', 'japan', 'korea').",
    ),
) -> JSONResponse:
    global _inflight

    name = (file.filename or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in ALLOWED:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: .{ext}")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 12 MB).")

    if _inflight >= MAX_QUEUE:
        raise HTTPException(status_code=503, detail="Busy — too many requests right now, try again in a moment.")

    t0 = time.perf_counter()
    _inflight += 1
    try:
        async with _sem:  # limits concurrent CPU-bound OCR passes
            # OCR is blocking (numpy/ONNX): run it in the thread pool so the
            # event loop stays responsive.
            try:
                if ext == "pdf":
                    text, confidence, duration, pages = await anyio.to_thread.run_sync(ocr.ocr_pdf, data, lang)
                else:
                    pages = 0
                    text, confidence, duration = await anyio.to_thread.run_sync(ocr.ocr_image, data, lang)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        _inflight -= 1

    if confidence is None:
        confidence = 0.0
    total_ms = round((time.perf_counter() - t0) * 1000, 1)
    body: dict = {
        "text": text,
        "confidence": confidence,
        "engine": ocr.ENGINE,
        "duration_ms": total_ms,
    }
    if pages:
        body["pages"] = pages
    if not text.strip():
        body["text"] = ""
        body["confidence"] = 0.0
        body["note"] = "No text detected." if ext != "pdf" else "No text detected in any page."
    return JSONResponse(body)


# API routes are registered first; the static mount below is the catch-all.
# The web assets live next to this file (repo/Docker), but pip-installed copies
# ship them under the data dir, so search a few well-known locations.
def _web_dir() -> Path:
    here = Path(__file__).resolve().parent
    candidates = [
        Path(os.environ.get("TEXTRIEVE_WEB_DIR", "")),  # explicit override
        here / "web",  # repo / Docker layout
        Path(sys.prefix) / "textrieve_web",  # pip install (venv/system) layout
        Path(sys.prefix) / "data" / "textrieve_web",  # alternate pip layout
        Path.home() / ".local" / "textrieve_web",
        Path.home() / ".local" / "share" / "textrieve_web",
    ]
    for path in candidates:
        if path and (path / "index.html").is_file():
            return path
    return here / "web"


app.mount("/", StaticFiles(directory=_web_dir(), html=True), name="web")