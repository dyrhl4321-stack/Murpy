# -*- coding: utf-8 -*-
"""
Raise the back collar on a v2 top layer.

The Nanobanana top layer is clean overall, but the back/up frames leave too much
neck visible on the bald body. This post-process adds a small blue back collar
only to the up row.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from PIL import Image


def is_blue(px):
    r, g, b, a = px
    return a > 20 and 8 <= r <= 100 and 55 <= g <= 215 and 90 <= b <= 255 and b >= r + 35


def dominant_blue(cell):
    colors = Counter()
    px = cell.load()
    w, h = cell.size
    for y in range(int(h * 0.35), int(h * 0.58)):
        for x in range(w):
            p = px[x, y]
            if is_blue(p):
                colors[p] += 1
    return colors.most_common(1)[0][0] if colors else (53, 160, 220, 255)


def darken(px, amount=38):
    r, g, b, a = px
    return (max(0, r - amount), max(0, g - amount), max(0, b - amount), a)


def adjust(input_path: Path, output_path: Path, frame_w: int, frame_h: int) -> None:
    sheet = Image.open(input_path).convert("RGBA")
    out = sheet.copy()

    # Row 1 is up/back. Apply to all three animation columns.
    row = 1
    for col in range(3):
        x0 = col * frame_w
        y0 = row * frame_h
        cell = sheet.crop((x0, y0, x0 + frame_w, y0 + frame_h))
        base = dominant_blue(cell)
        shade = darken(base, 45)
        px = out.load()

        # Coordinates are frame-local. This is intentionally small: it raises
        # only the rear collar and avoids painting over the head/hair area.
        collar_rows = [
            (126, 130, 153),
            (127, 128, 155),
            (128, 126, 157),
            (129, 124, 159),
            (130, 122, 161),
            (131, 121, 162),
            (132, 120, 163),
            (133, 119, 164),
            (134, 118, 165),
            (135, 118, 165),
            (136, 118, 165),
            (137, 118, 165),
            (138, 119, 164),
            (139, 120, 163),
            (140, 121, 162),
            (141, 122, 161),
            (142, 123, 160),
            (143, 124, 159),
            (144, 125, 158),
            (145, 126, 157),
            (146, 127, 156),
        ]

        for yy, left, right in collar_rows:
            for xx in range(left, right + 1):
                # Dark rim at top/sides, blue fill inside.
                local_edge = yy in (134, 146) or xx in (left, right)
                px[x0 + xx, y0 + yy] = shade if local_edge else base

        # Blend a lower rear-neck band into the existing shirt. The visible
        # neck in the v2 bald body sits around y=225, well below the hair mass.
        for yy in range(229, 248):
            taper = max(0, abs(238 - yy) // 3)
            for xx in range(127 + taper, 157 - taper):
                local_edge = yy in (229, 247) or xx in (127 + taper, 156 - taper)
                px[x0 + xx, y0 + yy] = shade if local_edge else base

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(output_path)
    print(f"saved {output_path} {out.size}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--frame-width", type=int, default=282)
    ap.add_argument("--frame-height", type=int, default=448)
    args = ap.parse_args()
    adjust(Path(args.input), Path(args.output), args.frame_width, args.frame_height)


if __name__ == "__main__":
    main()
