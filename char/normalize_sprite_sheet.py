# -*- coding: utf-8 -*-
"""
Normalize a generated 3x4 sprite sheet to Murpy's current app grid.

This is useful for draft previews when AI returns a larger sprite sheet.
It preserves row/column order and can remove neutral checkerboard backgrounds
connected to the sheet edges.
"""
from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

from PIL import Image


def is_checker_like(px):
    r, g, b, a = px
    if a < 20:
        return True
    if max(r, g, b) - min(r, g, b) <= 8 and min(r, g, b) >= 145:
        return True
    return False


def remove_edge_checker(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    w, h = image.size
    px = image.load()
    seen = [[False] * w for _ in range(h)]
    q = deque()

    for x in range(w):
        for y in (0, h - 1):
            if is_checker_like(px[x, y]) and not seen[y][x]:
                seen[y][x] = True
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if is_checker_like(px[x, y]) and not seen[y][x]:
                seen[y][x] = True
                q.append((x, y))

    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and is_checker_like(px[nx, ny]):
                seen[ny][nx] = True
                q.append((nx, ny))

    out = image.copy()
    op = out.load()
    for y in range(h):
        for x in range(w):
            if seen[y][x]:
                op[x, y] = (0, 0, 0, 0)
    return out


def normalize(src: Image.Image, cols: int, rows: int, frame_width: int, frame_height: int, remove_checker: bool) -> Image.Image:
    src = src.convert("RGBA")
    source_w, source_h = src.size
    out = Image.new("RGBA", (cols * frame_width, rows * frame_height), (0, 0, 0, 0))

    for row in range(rows):
        for col in range(cols):
            left = round(source_w * col / cols)
            top = round(source_h * row / rows)
            right = round(source_w * (col + 1) / cols)
            bottom = round(source_h * (row + 1) / rows)
            cell = src.crop((left, top, right, bottom))
            cell = cell.resize((frame_width, frame_height), Image.Resampling.LANCZOS)
            if remove_checker:
                cell = remove_edge_checker(cell)
            out.alpha_composite(cell, (col * frame_width, row * frame_height))

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--rows", type=int, default=4)
    ap.add_argument("--frame-width", type=int, default=141)
    ap.add_argument("--frame-height", type=int, default=224)
    ap.add_argument("--remove-checker", action="store_true")
    args = ap.parse_args()

    src = Image.open(args.input)
    out = normalize(src, args.cols, args.rows, args.frame_width, args.frame_height, args.remove_checker)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.save(args.output)
    print(f"saved {args.output} {out.size}")


if __name__ == "__main__":
    main()
