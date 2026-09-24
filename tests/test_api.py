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
    assert "IMAGE" in proc.stdout