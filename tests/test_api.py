from __future__ import annotations

import io

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

import app as app_module
from app import app

client = TestClient(app_module.app)

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SAMPLE_TEXT = "HELLO TEXTRIEVE 2026"


def make_fixture_png(text: str = SAMPLE_TEXT, w: int = 900, h: int = 220) -> bytes:
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_PATH, 64)
    draw.rectangle([0, 0, w - 1, h - 1], outline="black", width=4)
    draw.text((40, 72), text, font=font, fill="black")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def make_fixture_pdf() -> bytes:
    page1 = Image.new("RGB", (900, 220), "white")
    d1 = ImageDraw.Draw(page1)
    d1.text((40, 72), "HELLO TEXTRIEVE 2026", font=ImageFont.truetype(FONT_PATH, 64), fill="black")
    page2 = Image.new("RGB", (900, 220), "white")
    d2 = ImageDraw.Draw(page2)
    d2.text((40, 72), "PAGE TWO PDF OCR", font=ImageFont.truetype(FONT_PATH, 64), fill="black")
    buf = io.BytesIO()
    page1.save(buf, "PDF", save_all=True, append_images=[page2], resolution=140)
    return buf.getvalue()


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["app"] == "textrieve"
    assert body["version"] == app_module.VERSION
    assert body["status"] == "ok"


def test_index_served():
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "textrieve" in res.text


def test_ocr_roundtrip():
    png = make_fixture_png()
    res = client.post(
        "/api/ocr",
        files={"file": ("sample.png", png, "image/png")},
    )
    assert res.status_code == 200
    body = res.json()
    assert "text" in body
    assert body["text"].lower().replace("\n", " ").find("textrieve") != -1
    assert 0 <= body["confidence"] <= 100
    assert body["duration_ms"] >= 0


def test_ocr_blank_image_reports_zero_confidence():
    img = Image.new("RGB", (300, 120), "white")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    res = client.post("/api/ocr", files={"file": ("blank.png", buf.getvalue(), "image/png")})
    assert res.status_code == 200
    body = res.json()
    assert body["text"] == ""
    assert body["confidence"] == 0.0


def test_ocr_missing_file_rejected():
    res = client.post("/api/ocr")
    assert res.status_code == 422


def test_ocr_pdf_roundtrip():
    pdf = make_fixture_pdf()
    res = client.post("/api/ocr", files={"file": ("scan.pdf", pdf, "application/pdf")})
    assert res.status_code == 200
    body = res.json()
    assert "text" in body
    assert "textrieve" in body["text"].lower().replace("\n", " ")
    assert "page two" in body["text"].lower().replace("\n", " ")
    assert body["pages"] == 2
    assert 0 <= body["confidence"] <= 100
    assert body["duration_ms"] >= 0


def test_ocr_pdf_lang_hint_accepted():
    pdf = make_fixture_pdf()
    res = client.post(
        "/api/ocr?lang=en",
        files={"file": ("scan.pdf", pdf, "application/pdf")},
    )
    assert res.status_code == 200
    assert "textrieve" in res.json()["text"].lower().replace("\n", " ")


def test_ocr_oversized_image_rejected():
    big = b"\xff" * (12 * 1024 * 1024 + 1024)  # just over the 12 MB cap
    res = client.post("/api/ocr", files={"file": ("huge.png", big, "image/png")})
    assert res.status_code == 413


def test_ocr_corrupt_image_rejected():
    res = client.post("/api/ocr", files={"file": ("broken.png", b"not an image at all", "image/png")})
    assert res.status_code == 400


def test_favicon_served():
    res = client.get("/favicon.svg")
    assert res.status_code == 200
    assert "image/svg" in res.headers["content-type"]


def test_ocr_bad_extension_rejected():
    png = make_fixture_png()
    res = client.post(
        "/api/ocr",
        files={"file": ("notes.txt", png, "text/plain")},
    )
    assert res.status_code == 415


def test_cli_module_imports_and_help():
    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, "-m", "cli", "--help"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "FILE" in proc.stdout