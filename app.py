from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import ocr

APP_NAME = "textrieve"
VERSION = "1.0.0"
MAX_BYTES = 12 * 1024 * 1024
ALLOWED = {"png", "jpg", "jpeg", "webp", "bmp", "tiff", "tif"}

app = FastAPI(
    title=APP_NAME,
    version=VERSION,
    description="Free, fully-open image-to-text (OCR). CLI, REST API, and a clean web UI.",
)


@app.get("/api/health")
def health() -> dict:
    return {"app": APP_NAME, "version": VERSION, "status": "ok", "engine": ocr.ENGINE}


@app.post("/api/ocr")
async def ocr_endpoint(file: UploadFile = File(...)) -> JSONResponse:
    name = (file.filename or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in ALLOWED:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: .{ext}")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 12 MB).")

    t0 = time.perf_counter()
    try:
        text, confidence, duration = ocr.ocr_image(data)
        if confidence is None:
            confidence = 0.0
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"OCR failed: {exc}") from exc

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