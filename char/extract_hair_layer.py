# -*- coding: utf-8 -*-
"""
Extract a hair-only transparent layer from a generated sprite sheet.

This is intentionally pixel/mask based, not generative. It keeps brown hair
pixels plus dark outline pixels connected to the hair, and drops checkerboard
backgrounds, white guide bodies, skin, clothes, and stray body outlines.
"""
from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

from PIL import Image


def is_hair_fill(px):
    r, g, b, a = px
    if a < 20:
        return False
    # Brown hair range: warm, not skin-bright, enough red dominance.
    if 32 <= r <= 125 and 18 <= g <= 86 and 8 <= b <= 64 and r >= g + 8 and g >= b - 6:
        return True
    # Dark brown shadow.
    if 18 <= r <= 72 and 10 <= g <= 48 and 6 <= b <= 38 and r >= g - 2:
        return True
    return False


def is_hair_outline_candidate(px):
    r, g, b, a = px
    if a < 20:
        return False
    mx = max(r, g, b)
    mn = min(r, g, b)
    # Very dark outline, roughly neutral or warm.
    return mx <= 42 and (mx - mn) <= 24


def is_skin_like(px):
    r, g, b, a = px
    if a < 20:
        return False
    if r >= 120 and g >= 60 and b >= 35 and r > g + 28 and g > b + 8:
        return True
    return False


def is_face_dark_like(px):
    r, g, b, a = px
    if a < 20:
        return False
    # Deep eye/face outlines tend to be nearly black. Keep dark purple/brown
    # hair shadows, but drop neutral black details that are not hair colored.
    return max(r, g, b) <= 24 and abs(r - g) <= 10 and abs(g - b) <= 10


def component_from_seeds(seed_mask, passable):
    h = len(seed_mask)
    w = len(seed_mask[0])
    keep = [[False] * w for _ in range(h)]
    q = deque()
    for y in range(h):
        for x in range(w):
            if seed_mask[y][x]:
                keep[y][x] = True
                q.append((x, y))

    while q:
        x, y = q.popleft()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and not keep[ny][nx] and passable[ny][nx]:
                    keep[ny][nx] = True
                    q.append((nx, ny))
    return keep


def extract_hair(src: Image.Image, cols: int, rows: int, frame_width: int | None, frame_height: int | None) -> Image.Image:
    src = src.convert("RGBA")
    w, h = src.size
    source_fw, source_fh = w // cols, h // rows
    target_fw = frame_width or source_fw
    target_fh = frame_height or source_fh
    out = Image.new("RGBA", (target_fw * cols, target_fh * rows), (0, 0, 0, 0))

    for row in range(rows):
        for col in range(cols):
            sx0, sy0 = col * source_fw, row * source_fh
            tx0, ty0 = col * target_fw, row * target_fh
            cell = src.crop((sx0, sy0, sx0 + source_fw, sy0 + source_fh))
            if cell.size != (target_fw, target_fh):
                cell = cell.resize((target_fw, target_fh), Image.Resampling.LANCZOS)
            cp = cell.load()

            # Hair lives in the upper part of each frame. This prevents black
            # body guide lines around arms/legs from joining the kept mask.
            y_limit = int(target_fh * 0.50)
            seed = [[False] * target_fw for _ in range(target_fh)]
            passable = [[False] * target_fw for _ in range(target_fh)]

            for y in range(y_limit):
                for x in range(target_fw):
                    p = cp[x, y]
                    fill = is_hair_fill(p)
                    outline = is_hair_outline_candidate(p)
                    seed[y][x] = fill
                    passable[y][x] = fill or outline

            keep = component_from_seeds(seed, passable)

            for y in range(y_limit):
                for x in range(target_fw):
                    if keep[y][x] and not is_skin_like(cp[x, y]) and not is_face_dark_like(cp[x, y]):
                        out.putpixel((tx0 + x, ty0 + y), cp[x, y])

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="Source sprite sheet")
    ap.add_argument("output", help="Transparent hair layer output")
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--rows", type=int, default=4)
    ap.add_argument("--frame-width", type=int)
    ap.add_argument("--frame-height", type=int)
    args = ap.parse_args()

    src = Image.open(args.input)
    out = extract_hair(src, args.cols, args.rows, args.frame_width, args.frame_height)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.save(args.output)
    print(f"saved {args.output} {out.size}")


if __name__ == "__main__":
    main()
