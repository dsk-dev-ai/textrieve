from __future__ import annotations

import time
from pathlib import Path

import anyio
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import ocr

APP_NAME = "textrieve"
VERSION = "1.1.0"
MAX_BYTES = 12 * 1024 * 1024
ALLOWED = {"png", "jpg", "jpeg", "webp", "bmp", "tiff", "tif"}

# Free-tier safety: bound how many ONNX inferences run at once and how many
# requests are allowed to queue. Beyond the queue we return 503 instead of
# letting memory grow until the process dies.
OCR_PERMITS = 2
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
async def ocr_endpoint(file: UploadFile = File(...)) -> JSONResponse:
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
                text, confidence, duration = await anyio.to_thread.run_sync(ocr.ocr_image, data)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        _inflight -= 1

    if confidence is None:
        confidence = 0.0
    total_ms = round((time.perf_counter() - t0) * 1000, 1)
    if not text.strip():
        return JSONResponse(
            {
                "text": "",
                "confidence": 0.0,
                "engine": ocr.ENGINE,
                "duration_ms": total_ms,
                "note": "No text detected in this image.",
            }
        )
    return JSONResponse(
        {
            "text": text,
            "confidence": confidence,
            "engine": ocr.ENGINE,
            "duration_ms": total_ms,
        }
    )


# API routes are registered first; the static mount below is the catch-all.
WEB_DIR = Path(__file__).resolve().parent / "web"
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")