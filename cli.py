#!/usr/bin/env python3
"""textrieve CLI — image-to-text on the command line.

Usage:
    textrieve path/to/image.png
    textrieve a.png b.jpg --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import ocr

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}


def extract(path: Path) -> dict:
    data = path.read_bytes()
    text, confidence, duration_ms = ocr.ocr_image(data)
    return {
        "file": str(path),
        "text": text,
        "confidence": confidence,
        "duration_ms": duration_ms,
        "engine": ocr.ENGINE,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="textrieve",
        description="Image-to-text (OCR) on the command line.",
        epilog="Reads text from any image. Powered by free, offline OCR (no API keys).",
    )
    parser.add_argument("images", nargs="+", metavar="IMAGE", help="image file(s) to read")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of plain text")
    args = parser.parse_args()

    srcs: list[Path] = []
    for raw in args.images:
        path = Path(raw)
        if path.is_dir():
            srcs.extend(p for p in sorted(path.iterdir()) if p.suffix.lower() in IMAGE_EXTS)
        elif path.is_file():
            srcs.append(path)
        else:
            print(f"textrieve: no such file: {raw}", file=sys.stderr)
            return 1

    if not srcs:
        print("textrieve: no image files found", file=sys.stderr)
        return 1

    results = [extract(p) for p in srcs]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    for res in results:
        header = res["file"]
        if res["confidence"] is None:
            header += "  (no text detected)"
        else:
            header += f"  ({res['confidence']}% conf, {res['duration_ms']:.0f} ms)"
        print(header)
        if res["text"]:
            print(res["text"])
        print("-" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())