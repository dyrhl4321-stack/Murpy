# -*- coding: utf-8 -*-
"""
Extract a cleaner v2 Murpy basic top layer from a high-resolution full character sheet.

This focuses only on the blue shirt. It uses blue pixels as seeds, keeps nearby
shirt outlines, and fills the lower torso area so the base underwear does not
show through under the shirt.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from PIL import Image


def is_bg(px):
    r, g, b, a = px
    return a < 20 or max(r, g, b) <= 8


def is_blue_shirt(px):
    r, g, b, a = px
    if a < 20:
        return False
    return 8 <= r <= 95 and 62 <= g <= 210 and 95 <= b <= 250 and b >= r + 42 and g >= r + 22


def is_blue_shadow(px):
    r, g, b, a = px
    if a < 20:
        return False
    return 6 <= r <= 70 and 35 <= g <= 135 and 55 <= b <= 170 and b >= r + 28


def is_outline(px):
    r, g, b, a = px
    if a < 20:
        return False
    mx = max(r, g, b)
    mn = min(r, g, b)
    return 12 <= mx <= 52 and (mx - mn) <= 30


def dominant_blue(cell, keep):
    cp = cell.load()
    colors = Counter()
    for y, row in enumerate(keep):
        for x, value in enumerate(row):
            if value and is_blue_shirt(cp[x, y]):
                colors[cp[x, y]] += 1
    return colors.most_common(1)[0][0] if colors else (43, 158, 221, 255)


def near_mask(mask, x, y, radius):
    h = len(mask)
    w = len(mask[0])
    for yy in range(max(0, y - radius), min(h, y + radius + 1)):
        for xx in range(max(0, x - radius), min(w, x + radius + 1)):
            if mask[yy][xx]:
                return True
    return False


def clean_cell(cell: Image.Image) -> Image.Image:
    cell = cell.convert("RGBA")
    w, h = cell.size
    cp = cell.load()
    y0 = int(h * 0.32)
    y1 = int(h * 0.70)
    seed = [[False] * w for _ in range(h)]

    for y in range(y0, y1):
        for x in range(w):
            p = cp[x, y]
            if is_bg(p):
                continue
            seed[y][x] = is_blue_shirt(p) or is_blue_shadow(p)

    keep = [row[:] for row in seed]
    fill = dominant_blue(cell, keep)

    # Keep a thin shirt outline, but only when it is directly beside blue shirt
    # pixels. This prevents hair/face outlines from climbing into the layer.
    for y in range(y0, y1):
        for x in range(w):
            if not keep[y][x] and is_outline(cp[x, y]) and near_mask(seed, x, y, radius=2):
                keep[y][x] = True

    # Fill the shirt torso and sleeves only below the neck. This prevents the
    # bald body's undergarment from showing through without painting the chin.
    torso_y0 = int(h * 0.40)
    torso_y1 = int(h * 0.64)
    for y in range(torso_y0, torso_y1):
        xs = [x for x in range(w) if keep[y][x]]
        if len(xs) < 8:
            continue
        left, right = min(xs), max(xs)
        pad = max(1, round(w * 0.015))
        for x in range(left + pad, right - pad + 1):
            if not keep[y][x] and not is_bg(cp[x, y]):
                if near_mask(keep, x, y, radius=7):
                    keep[y][x] = True

    out = Image.new("RGBA", cell.size, (0, 0, 0, 0))
    op = out.load()
    for y in range(y0, y1):
        for x in range(w):
            if keep[y][x]:
                p = cp[x, y]
                if is_blue_shirt(p) or is_blue_shadow(p) or is_outline(p):
                    op[x, y] = p
                else:
                    op[x, y] = fill
    return out


def extract(src: Image.Image, cols: int, rows: int, frame_w: int, frame_h: int) -> Image.Image:
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
            out.alpha_composite(clean_cell(cell), (col * frame_w, row * frame_h))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--rows", type=int, default=4)
    ap.add_argument("--frame-width", type=int, default=282)
    ap.add_argument("--frame-height", type=int, default=448)
    args = ap.parse_args()

    src = Image.open(args.input)
    out = extract(src, args.cols, args.rows, args.frame_width, args.frame_height)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.save(args.output)
    print(f"saved {args.output} {out.size}")


if __name__ == "__main__":
    main()
