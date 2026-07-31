# -*- coding: utf-8 -*-
"""옛 버전과 현재 버전이 방향(row)별로 얼마나 다른지 — 되돌릴 범위를 정하려고 잰다.

    python char/diag_row_diff.py 671c2c5
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
CW, CH = 141, 224
ALPHA_BIN = 128
ROWS = ["정면", "후면", "좌", "우"]


def cell(s, r, c):
    return s[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]


def over(dst, src):
    out = dst.copy()
    m = src[:, :, 3] >= ALPHA_BIN
    out[m] = src[m]
    out[m, 3] = 255
    return out


def main():
    sha = sys.argv[1] if len(sys.argv) > 1 else "671c2c5"
    base = np.asarray(Image.open(os.path.join(HERE, "walk.png")).convert("RGBA")).astype(int)
    old = np.asarray(Image.open(os.path.join(HERE, "_diag", "hist", f"{sha}.png"))
                     .convert("RGBA")).astype(int)
    cur = np.asarray(Image.open(os.path.join(HERE, "items", "hair_m_semileaf.png"))
                     .convert("RGBA")).astype(int)
    print(f"{sha} vs 현재")
    for r in range(4):
        tot_a, tot_v = 0, 0
        for c in range(3):
            bc = cell(base, r, c)
            ho = cell(old, r, c)[:, :, 3] >= ALPHA_BIN
            hc = cell(cur, r, c)[:, :, 3] >= ALPHA_BIN
            tot_a += int((ho ^ hc).sum())
            co, cc = over(bc, cell(old, r, c)), over(bc, cell(cur, r, c))
            tot_v += int((np.abs(co[:, :, :3] - cc[:, :, :3]).sum(axis=2) > 24).sum())
        print(f"  {ROWS[r]:2s}  알파 차이 {tot_a:5d}px   화면 차이 {tot_v:5d}px")


if __name__ == "__main__":
    main()
