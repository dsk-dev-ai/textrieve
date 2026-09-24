from __future__ import annotations

import io
import time
from functools import lru_cache

import numpy as np
from PIL import Image

ENGINE = "RapidOCR (ONNX, CPU)"

MAX_SIDE = 4000


@lru_cache(maxsize=1)
def _engine():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def _normalise(data: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(data))
    if img.width > MAX_SIDE or img.height > MAX_SIDE:
        img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return np.asarray(img)


def ocr_image(data: bytes) -> tuple[str, float | None, float]:
    """Run OCR on raw image bytes.

    Returns ``(text, mean_confidence_0_100, duration_ms)``. Confidence is
    ``None`` when no text is detected.
    """
    t0 = time.perf_counter()
    engine = _engine()
    array = _normalise(data)
    result, _elapse = engine(array)

    texts: list[str] = []
    scores: list[float] = []
    for block in result or []:
        box, text, score = block[0], block[1], block[2]
        texts.append(text)
        scores.append(float(score))

    duration = round((time.perf_counter() - t0) * 1000, 1)
    text = "\n".join(item for item in texts if item)
    confidence = round(100.0 * float(np.mean(scores)), 1) if scores else None
    return text, confidence, duration