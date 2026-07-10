# -*- coding: utf-8 -*-
"""
Extract Murpy's basic outfit layers from a high-resolution full character sheet.

Outputs v2 layer sheets:
- top
- bottom
- shoes

This is a deterministic draft extractor for the current Murpy base outfit. It
does not edit app data.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


SLOTS = ("top", "bottom", "shoes")


def is_near_black(px):
    r, g, b, a = px
    return a < 20 or max(r, g, b) <= 10


def is_top_seed(px):
    r, g, b, a = px
    if a < 20:
        return False
    # Bright/cyan shirt pixels.
    return 10 <= r <= 95 and 70 <= g <= 205 and 105 <= b <= 245 and b >= r + 45 and g >= r + 25


def is_bottom_seed(px):
    r, g, b, a = px
    if a < 20:
        return False
    # Dark desaturated blue/gray shorts, separated from bright shirt blues.
    if b > 118 or g > 100:
        return False
    return 18 <= r <= 95 and 28 <= g <= 100 and 36 <= b <= 118 and b >= r + 6 and max(r, g, b) >= 42


def is_shoes_seed(px):
    r, g, b, a = px
    if a < 20:
        return False
    white = r >= 145 and g >= 135 and b >= 115 and max(r, g, b) - min(r, g, b) <= 70
    brown = 55 <= r <= 150 and 28 <= g <= 102 and 12 <= b <= 78 and r >= g + 12
    dark_upper = 16 <= r <= 70 and 16 <= g <= 68 and 16 <= b <= 78 and max(r, g, b) >= 34
    return white or brown or dark_upper


def is_outline_candidate(px):
    r, g, b, a = px
    if a < 20:
        return False
    mx = max(r, g, b)
    mn = min(r, g, b)
    # Keep dark colored outlines, but avoid swallowing pure black background.
    return 12 <= mx <= 48 and (mx - mn) <= 26


def has_seed_near(seed, x, y, radius):
    h = len(seed)
    w = len(seed[0])
    for yy in range(max(0, y - radius), min(h, y + radius + 1)):
        for xx in range(max(0, x - radius), min(w, x + radius + 1)):
            if seed[yy][xx]:
                return True
    return False


def mask_cell(cell: Image.Image, slot: str) -> Image.Image:
    cell = cell.convert("RGBA")
    w, h = cell.size
    cp = cell.load()
    out = Image.new("RGBA", cell.size, (0, 0, 0, 0))
    op = out.load()

    if slot == "top":
        y0, y1 = int(h * 0.33), int(h * 0.72)
        judge = is_top_seed
        outline_radius = 2
    elif slot == "bottom":
        y0, y1 = int(h * 0.60), int(h * 0.76)
        judge = is_bottom_seed
        outline_radius = 2
    elif slot == "shoes":
        y0, y1 = int(h * 0.78), h
        judge = is_shoes_seed
        outline_radius = 2
    else:
        raise ValueError(slot)

    seed = [[False] * w for _ in range(h)]
    for y in range(y0, y1):
        for x in range(w):
            if not is_near_black(cp[x, y]) and judge(cp[x, y]):
                seed[y][x] = True
                op[x, y] = cp[x, y]

    # Add a thin outline only around real colored item pixels.
    for y in range(max(0, y0 - outline_radius), min(h, y1 + outline_radius)):
        for x in range(w):
            if op[x, y][3] == 0 and is_outline_candidate(cp[x, y]) and has_seed_near(seed, x, y, outline_radius):
                op[x, y] = cp[x, y]

    return out


def extract(src: Image.Image, slot: str, cols: int, rows: int, frame_w: int, frame_h: int) -> Image.Image:
    src = src.convert("RGBA")
    source_w, source_h = src.size
    out = Image.new("RGBA", (cols * frame_w, rows * frame_h), (0, 0, 0, 0))

    for row in range(rows):
        for col in range(cols):
            left = round(source_w * col / cols)
            top = round(source_h * row / rows)
            right = round(source_w * (col + 1) / cols)
            bottom = round(source_h * (row + 1) / rows)
            cell = src.crop((left, top, right, bottom))
            if cell.size != (frame_w, frame_h):
                cell = cell.resize((frame_w, frame_h), Image.Resampling.LANCZOS)
            layer = mask_cell(cell, slot)
            out.alpha_composite(layer, (col * frame_w, row * frame_h))

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output_dir")
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--rows", type=int, default=4)
    ap.add_argument("--frame-width", type=int, default=282)
    ap.add_argument("--frame-height", type=int, default=448)
    args = ap.parse_args()

    src = Image.open(args.input)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for slot in SLOTS:
        out = extract(src, slot, args.cols, args.rows, args.frame_width, args.frame_height)
        out_path = out_dir / f"v2_{slot}_basic_candidate.png"
        out.save(out_path)
        print(f"saved {out_path} {out.size}")


if __name__ == "__main__":
    main()
