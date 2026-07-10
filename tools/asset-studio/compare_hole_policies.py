# -*- coding: utf-8 -*-
"""
구멍 채우기 정책 3종을 같은 입력으로 비교한다. 앱 파일은 건드리지 않는다.

  LEGACY        : 구멍이면 무조건 옷 색으로 채움 (현행 customizer_cli)
  FIX+fillUNK   : 변하지 않은 몸(body hole)만 안 채우고, 애매한 살색 구멍(UNK)은 채움
  FIX-keepUNK   : body hole 도 UNK hole 도 안 채움 (사람이 판정)

사용: python tools/asset-studio/compare_hole_policies.py [item_id ...]
출력: tools/asset-studio/out/<item>_policies.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import trimap as T

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "tools" / "character-customizer" / "review_queue"
OUT = Path(__file__).resolve().parent / "out"
BASE = ROOT / "char" / "v2" / "body_bald.png"

CASES = {
    "top_ringer": ("top", "top_ringer_20260709-155747"),
    "top_jersey": ("top", "top_jersey_20260709-154511"),
    "top_redhood": ("top", "top_redhood_20260709-143848"),
    "bottom_trainpt": ("bottom", "bottom_trainpt_20260709-154335"),
    "bottom_bermuda": ("bottom", "bottom_bermuda_20260709-124346"),
    "hat_ladodgers": ("hat", "hat_ladodgers_20260709-114647"),
    "hat_beanie_v2": ("hat", "hat_beanie_v2_20260709-115729"),
    "shoes_white": ("shoes", "shoes_white_20260709-140215"),
}

FW, FH = T.FRAME_W, T.FRAME_H
BG = (30, 34, 44, 255)
PAD = 12
DIRS = ["down", "up", "left", "right"]


def composite(base: Image.Image, item: Image.Image, row: int, col: int = 0) -> Image.Image:
    cell = base.crop((col * FW, row * FH, col * FW + FW, row * FH + FH)).copy()
    cell.alpha_composite(item.crop((col * FW, row * FH, col * FW + FW, row * FH + FH)))
    out = Image.new("RGBA", (FW, FH), BG)
    out.alpha_composite(cell)
    return out


def label(img: Image.Image, text: str) -> Image.Image:
    band = Image.new("RGBA", (img.width, 20), BG)
    ImageDraw.Draw(band).text((4, 4), text, fill=(190, 200, 220, 255))
    out = Image.new("RGBA", (img.width, img.height + 20), BG)
    out.alpha_composite(band, (0, 0))
    out.alpha_composite(img, (0, 20))
    return out


def grid(rows: list[list[Image.Image]]) -> Image.Image:
    w = max(sum(c.width for c in r) + PAD * (len(r) + 1) for r in rows)
    h = sum(max(c.height for c in r) for r in rows) + PAD * (len(rows) + 1)
    canvas = Image.new("RGBA", (w, h), BG)
    y = PAD
    for r in rows:
        x = PAD
        for c in r:
            canvas.alpha_composite(c, (x, y))
            x += c.width + PAD
        y += max(c.height for c in r) + PAD
    return canvas


def run(item_id: str) -> dict | None:
    slot, qname = CASES[item_id]
    worn_path = QUEUE / qname / "source_normalized_v2.png"
    if not worn_path.exists():
        print(f"skip {item_id}: {worn_path} 없음")
        return None

    base = Image.open(BASE).convert("RGBA")
    worn = Image.open(worn_path).convert("RGBA")

    variants = [
        ("LEGACY(현행)", T.extract(base, worn, slot, legacy_holes=True)),
        ("TRIMAP(수정)", T.extract(base, worn, slot)),
    ]

    rows = []
    for r, name in enumerate(DIRS):
        rows.append([label(composite(base, v["item"], r), f"{name} · {tag}") for tag, v in variants])
    grid(rows).save(OUT / f"{item_id}_policies.png")

    s = {tag: v["stats"] for tag, v in variants}
    return {
        "item": item_id,
        "slot": slot,
        "legacy_filled": s["LEGACY(현행)"]["holesFilled"],
        "legacy_bodyPaint": s["LEGACY(현행)"]["bodyOverpaintPx"],
        "fix_filled": s["TRIMAP(수정)"]["holesFilled"],
        "fix_bodySkipped": s["TRIMAP(수정)"]["bodyHolesSkipped"],
        "unkTotal": s["TRIMAP(수정)"]["unkPixels"],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    items = sys.argv[1:] or list(CASES)
    report = [r for r in (run(i) for i in items) if r]

    hdr = (f"{'item':16}{'slot':9}{'LEG fill':>10}{'LEG bodyPaint':>15}"
           f"{'FIX fill':>10}{'FIX bodySkip':>14}{'UNK total':>11}")
    print("\n" + hdr)
    print("-" * len(hdr))
    for r in report:
        print(f"{r['item']:16}{r['slot']:9}{r['legacy_filled']:>10}{r['legacy_bodyPaint']:>15}"
              f"{r['fix_filled']:>10}{r['fix_bodySkipped']:>14}{r['unkTotal']:>11}")
    print("\nLEG bodyPaint : base·worn 둘 다 살색인데 옷 색으로 칠한 픽셀 → 겨드랑이·목덜미")
    print("FIX bodySkip  : 수정본이 그걸 살려둔 수 (LEG bodyPaint 와 같아야 함)")


if __name__ == "__main__":
    main()
