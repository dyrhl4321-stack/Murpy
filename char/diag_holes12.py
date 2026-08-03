# -*- coding: utf-8 -*-
"""12프레임 전부에서 내부 구멍을 찾는다 (귀는 제외)."""
import sys, io, os
import numpy as np
from PIL import Image
from scipy import ndimage
sys.path.insert(0, r"C:\Users\allys\Murpy\char")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from base_regions import regions as regions_of

H = r"C:\Users\allys\Murpy\char"
CW, CH, AB = 141, 224, 128
ROWS = ["정면", "후면", "좌", "우"]
BASEW = {"human": "walk.png", "human_f": "walk_female.png"}

name = sys.argv[1]
body = sys.argv[2] if len(sys.argv) > 2 else "human_f"
base = np.asarray(Image.open(os.path.join(H, BASEW[body])).convert("RGBA")).astype(int)
a = np.asarray(Image.open(os.path.join(H, "items", name)).convert("RGBA")).astype(int)

print(f"■ {name} — 12프레임 내부 구멍 (귀 제외)")
for r in range(4):
    for c in range(3):
        bc = base[r*CH:(r+1)*CH, c*CW:(c+1)*CW]
        h = a[r*CH:(r+1)*CH, c*CW:(c+1)*CW, 3] >= AB
        if not h.any():
            continue
        allh = ndimage.binary_fill_holes(h) & ~h
        _must, keep = regions_of(bc, r, BASEW[body], c)
        holes = allh & ~keep
        if not holes.any():
            continue
        lab, n = ndimage.label(holes, np.ones((3, 3), bool))
        spots = []
        for i in range(1, n+1):
            m = lab == i
            if m.sum() < 3:
                continue
            ys, xs = np.where(m)
            spots.append((int(m.sum()), int(xs.mean()), int(ys.mean())))
        if spots:
            spots.sort(reverse=True)
            s = " · ".join(f"{p}px@x{x},y{y}" for p, x, y in spots[:4])
            print(f"   {ROWS[r]:2s} col{c}  {len(spots)}곳 {int(holes.sum())}px   {s}")
