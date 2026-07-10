# -*- coding: utf-8 -*-
"""
Create v2 default hair variants by tuning only the back/up row.

The current v2 hair works from the front/side but the back silhouette is too
round. This tool keeps every other row unchanged and applies small transparent
cuts to the back row so variants can be compared quickly.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def cut_ellipse(px, x, y, cx, cy, rx, ry):
    if rx <= 0 or ry <= 0:
        return False
    dx = (x - cx) / rx
    dy = (y - cy) / ry
    return dx * dx + dy * dy <= 1


def tune_back_row(src: Image.Image, mode: str, frame_w: int, frame_h: int) -> Image.Image:
    out = src.convert("RGBA").copy()
    px = out.load()
    row_y = frame_h

    for col in range(3):
        x0 = col * frame_w
        y0 = row_y

        for y in range(frame_h):
            for x in range(frame_w):
                gx, gy = x0 + x, y0 + y
                r, g, b, a = px[gx, gy]
                if a < 20:
                    continue

                remove = False

                if mode == "trim_bottom":
                    remove = 228 <= y <= 270 and 98 <= x <= 184
                elif mode == "slim_sides":
                    remove = (
                        cut_ellipse(px, x, y, 47, 145, 23, 74)
                        or cut_ellipse(px, x, y, 235, 145, 23, 74)
                    )
                elif mode == "flatter":
                    remove = (
                        (218 <= y <= 276 and 103 <= x <= 179)
                        or cut_ellipse(px, x, y, 45, 145, 20, 68)
                        or cut_ellipse(px, x, y, 237, 145, 20, 68)
                    )
                elif mode == "neck_gap":
                    remove = 213 <= y <= 282 and 112 <= x <= 170
                else:
                    raise ValueError(mode)

                if remove:
                    px[gx, gy] = (0, 0, 0, 0)

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--mode", choices=["trim_bottom", "slim_sides", "flatter", "neck_gap"], required=True)
    ap.add_argument("--frame-width", type=int, default=282)
    ap.add_argument("--frame-height", type=int, default=448)
    args = ap.parse_args()

    src = Image.open(args.input)
    out = tune_back_row(src, args.mode, args.frame_width, args.frame_height)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.save(args.output)
    print(f"saved {args.output} {out.size}")


if __name__ == "__main__":
    main()
