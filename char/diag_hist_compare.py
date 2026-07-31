# -*- coding: utf-8 -*-
"""여러 버전의 헤어 레이어를 base 위에 합성해 정면 머리만 나란히 본다.

    python char/diag_hist_compare.py 671c2c5 9899720 43cbbeb a215d5b
버전 파일은 char/_diag/hist/<sha>.png 에 있어야 한다.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
CW, CH = 141, 224
ALPHA_BIN = 128
SCALE = 5
HEAD_H = 100          # 머리 부분만 (셀 위에서부터)


def cell(sheet, r, c):
    return sheet[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]


def over(dst, src):
    out = dst.copy()
    m = src[:, :, 3] >= ALPHA_BIN
    out[m] = src[m]
    out[m, 3] = 255
    return out


def main():
    args = sys.argv[1:]
    row, col = 0, 0
    if "--row" in args:
        i = args.index("--row"); row = int(args[i + 1]); args = args[:i] + args[i + 2:]
    if "--col" in args:
        i = args.index("--col"); col = int(args[i + 1]); args = args[:i] + args[i + 2:]
    shas = args or ["671c2c5", "43cbbeb", "a215d5b"]
    base = np.asarray(Image.open(os.path.join(HERE, "walk.png")).convert("RGBA")).astype(int)
    bc = cell(base, row, col)

    tiles = []
    for s in shas:
        p = os.path.join(HERE, "_diag", "hist", f"{s}.png")
        hs = np.asarray(Image.open(p).convert("RGBA")).astype(int)
        hc = cell(hs, row, col)
        comp = over(bc, hc)[:HEAD_H]
        tiles.append((s, Image.fromarray(comp.astype(np.uint8), "RGBA").convert("RGB")))

    pad, lbl = 6, 16
    W = (CW + pad) * len(tiles) + pad
    canvas = Image.new("RGB", (W, HEAD_H + lbl + pad * 2), (245, 245, 245))
    d = ImageDraw.Draw(canvas)
    for i, (s, im) in enumerate(tiles):
        x = pad + i * (CW + pad)
        canvas.paste(im, (x, lbl + pad))
        d.text((x, 3), s, fill=(0, 0, 0))
    out = os.path.join(HERE, "_diag", "hist_front_compare.png")
    canvas.resize((canvas.width * SCALE, canvas.height * SCALE), Image.NEAREST).save(out)
    print(f"-> {out}   ({' | '.join(s for s, _ in tiles)})")


if __name__ == "__main__":
    main()
