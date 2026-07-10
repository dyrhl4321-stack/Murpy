# -*- coding: utf-8 -*-
"""
기존 diff(버그 포함) vs trimap diff(수정본) 을 같은 입력으로 돌려 나란히 비교한다.
앱 파일은 건드리지 않는다. 증거 이미지만 만든다.

사용: python tools/asset-studio/compare_legacy_vs_trimap.py
출력: tools/asset-studio/out/<item>_compare.png  +  콘솔 통계표
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import trimap as T

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "tools" / "character-customizer" / "review_queue"
OUT = Path(__file__).resolve().parent / "out"

BASE = ROOT / "char" / "v2" / "body_bald.png"

CASES = [
    ("top_ringer", "top", QUEUE / "top_ringer_20260709-155747"),
    ("top_jersey", "top", QUEUE / "top_jersey_20260709-154511"),
    ("bottom_trainpt", "bottom", QUEUE / "bottom_trainpt_20260709-154335"),
    ("hat_ladodgers", "hat", QUEUE / "hat_ladodgers_20260709-114647"),
]

FW, FH = T.FRAME_W, T.FRAME_H
BG = (30, 34, 44, 255)
PAD = 14


def composite(base: Image.Image, item: Image.Image, row: int, col: int = 0) -> Image.Image:
    cell = base.crop((col * FW, row * FH, col * FW + FW, row * FH + FH)).copy()
    cell.alpha_composite(item.crop((col * FW, row * FH, col * FW + FW, row * FH + FH)))
    out = Image.new("RGBA", (FW, FH), BG)
    out.alpha_composite(cell)
    return out


def delta_view(base: Image.Image, legacy_mask, fixed_mask, row: int, col: int = 0) -> Image.Image:
    """legacy 가 칠했지만 trimap 은 안 칠한 픽셀 = 빨강 (팔에 페인트된 옷)."""
    cell = base.crop((col * FW, row * FH, col * FW + FW, row * FH + FH)).convert("RGBA")
    arr = np.array(cell)
    ys = slice(row * FH, (row + 1) * FH)
    xs = slice(col * FW, (col + 1) * FW)
    only_legacy = legacy_mask[ys, xs] & ~fixed_mask[ys, xs]
    arr[only_legacy] = [255, 40, 40, 255]
    out = Image.new("RGBA", (FW, FH), BG)
    out.alpha_composite(Image.fromarray(arr))
    return out


def label(img: Image.Image, text: str) -> Image.Image:
    from PIL import ImageDraw
    band = Image.new("RGBA", (img.width, 22), BG)
    ImageDraw.Draw(band).text((4, 5), text, fill=(200, 208, 224, 255))
    out = Image.new("RGBA", (img.width, img.height + 22), BG)
    out.alpha_composite(band, (0, 0))
    out.alpha_composite(img, (0, 22))
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


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = Image.open(BASE).convert("RGBA")
    rows_report = []

    for item_id, slot, qdir in CASES:
        worn_path = qdir / "source_normalized_v2.png"
        if not worn_path.exists():
            print(f"skip {item_id}: {worn_path} 없음")
            continue
        worn = Image.open(worn_path).convert("RGBA")

        legacy = T.extract(base, worn, slot, legacy_holes=True)
        fixed = T.extract(base, worn, slot)

        ls, fs = legacy["stats"], fixed["stats"]
        rows_report.append({
            "item": item_id,
            "slot": slot,
            "legacy_holesFilled": ls["holesFilled"],
            "legacy_bodyOverpaint": ls["bodyOverpaintPx"],
            "legacy_unkOverpaint": ls["unkOverpaintPx"],
            "fixed_holesFilled": fs["holesFilled"],
            "fixed_bodyHolesSkipped": fs["bodyHolesSkipped"],
            "fixed_unkHolesSkipped": fs["unkHolesSkipped"],
            "unkPixels": fs["unkPixels"],
            "fgPixels_legacy": ls["fgPixels"],
            "fgPixels_fixed": fs["fgPixels"],
        })

        band_rows = []
        for dir_row, name in enumerate(["down", "up", "left", "right"]):
            band_rows.append([
                label(composite(base, legacy["item"], dir_row), f"{name} · LEGACY(현행)"),
                label(composite(base, fixed["item"], dir_row), f"{name} · TRIMAP(수정)"),
                label(delta_view(base, legacy["mask"], fixed["mask"], dir_row), f"{name} · 빨강=팔에칠한옷"),
            ])
        img = grid(band_rows)
        p = OUT / f"{item_id}_compare.png"
        img.save(p)
        print(f"saved {p}")

    print()
    hdr = (f"{'item':16}{'slot':9}{'LEG holes':>10}{'LEG bodyPaint':>15}{'LEG unkPaint':>14}"
           f"{'FIX holes':>11}{'FIX bodySkip':>14}{'FIX unkSkip':>13}{'UNK total':>11}")
    print(hdr)
    print("-" * len(hdr))
    for r in rows_report:
        print(f"{r['item']:16}{r['slot']:9}{r['legacy_holesFilled']:>10}{r['legacy_bodyOverpaint']:>15}"
              f"{r['legacy_unkOverpaint']:>14}{r['fixed_holesFilled']:>11}{r['fixed_bodyHolesSkipped']:>14}"
              f"{r['fixed_unkHolesSkipped']:>13}{r['unkPixels']:>11}")
    print("\nLEG bodyPaint = 변하지도 않은 몸 픽셀을 아이템 색으로 칠한 수 (기존 버그)")
    print("FIX bodySkip  = 그걸 살려둔 수 (같아야 정상)")

    (OUT / "compare_report.json").write_text(json.dumps(rows_report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nsaved {OUT / 'compare_report.json'}")


if __name__ == "__main__":
    main()
