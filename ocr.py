from __future__ import annotations

import gc
import io
import time

import numpy as np
from PIL import Image

ENGINE = "RapidOCR (ONNX, CPU)"

MAX_SIDE = 4000
# Images larger than this (in pixels of surface area) are downscaled before OCR,
# keeping peak memory bounded on small free-tier instances.
MAX_PIXELS = 4_000_000

MAX_PDF_PAGES = 25
PDF_DPI = 110  # ~3400 px page width at A3; safely bounded for CPU OCR.


def _build(lang=None):
    from rapidocr_onnxruntime import RapidOCR

    if lang is None:
        return RapidOCR()
    try:
        # RapidOCR accepts a str or list of language codes (e.g. "ch", "en",
        # "japan", "korea", ...). Some builds reject params; fall back to the
        # default (multi-language) engine rather than crashing.
        return RapidOCR(lang=lang)
    except TypeError:
        return RapidOCR()


# Lazy engines keyed by language hint so the default stays untouched while an
# explicit language, when used, gets its own (bounded) engine.
_engines: dict[tuple, object] = {}


def _engine(lang=None):
    key = (str(lang),) if lang else ("ch+en",)
    engine = _engines.get(key)
    if engine is None:
        engine = _build(lang)
        _engines[key] = engine
    return engine


def _normalise(data: bytes) -> np.ndarray:
    try:
        img = Image.open(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001 - unreadable/corrupt image bytes
        raise ValueError("The uploaded bytes are not a readable image.") from exc
    if img.mode != "RGB":
        img = img.convert("RGB")
    return _fit(np.asarray(img))


def _fit(array: np.ndarray) -> np.ndarray:
    h, w = array.shape[:2]
    if max(w, h) > MAX_SIDE or w * h > MAX_PIXELS:
        img = Image.fromarray(array)
        img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        array = np.asarray(img)
    return array


def _infer(engine, array: np.ndarray) -> tuple[list[str], list[float]]:
    try:
        result, _elapse = engine(array)
    finally:
        del array
    if result is not None:
        gc.collect()

    texts: list[str] = []
    scores: list[float] = []
    for block in result or []:
        _box, text, score = block[0], block[1], block[2]
        texts.append(text)
        scores.append(float(score))
    return texts, scores


def ocr_image(data: bytes, lang=None) -> tuple[str, float | None, float]:
    """Run OCR on raw image bytes.

    Returns ``(text, mean_confidence_0_100, duration_ms)``. Confidence is
    ``None`` when no text is detected.

    Memory: the decoded image is released immediately after inference and a
    periodic GC run keeps the process bounded on small instances. Nothing is
    retained between calls except the (lazy, cached) ONNX engines.
    """
    t0 = time.perf_counter()
    texts, scores = _infer(_engine(lang), _normalise(data))
    duration = round((time.perf_counter() - t0) * 1000, 1)
    text = "\n".join(item for item in texts if item)
    confidence = round(100.0 * float(np.mean(scores)), 1) if scores else None
    return text, confidence, duration


def ocr_pdf(data: bytes, lang=None, max_pages: int = MAX_PDF_PAGES) -> tuple[str, float | None, float, int]:
    """Run OCR on a PDF (rendered page-by-page, no text layer required).

    Returns ``(text, mean_confidence_0_100, duration_ms, pages)``. Each page's
    text is separated by a ``[Page N]`` marker. ``max_pages`` bounds CPU work on
    small instances.
    """
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:  # pragma: no cover - packaging slip
        raise ValueError("The uploaded bytes are not a readable image.") from exc

    t0 = time.perf_counter()
    doc = pdfium.PdfDocument(data)
    if len(doc) == 0:
        doc.close()
        raise ValueError("The PDF appears to be empty.")
    try:
        total = min(len(doc), max_pages)
        pages: list[str] = []
        confs: list[float] = []
        for i in range(total):
            page = doc[i]
            bitmap = page.render(scale=PDF_DPI / 72.0, may_draw_forms=True)
            array = _fit(np.asarray(bitmap.to_pil().convert("RGB")))
            texts, scores = _infer(_engine(lang), array)
            page_text = "\n".join(item for item in texts if item)
            pages.append(f"[Page {i + 1}]\n{page_text}".strip() if page_text else f"[Page {i + 1}]\n")
            confs.extend(scores)
    finally:
        doc.close()

    text = "\n\n".join(pages)
    duration = round((time.perf_counter() - t0) * 1000, 1)
    confidence = round(100.0 * float(np.mean(confs)), 1) if confs else None
    return text, confidence, duration, total