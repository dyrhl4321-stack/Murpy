# -*- coding: utf-8 -*-
"""두상 삐짐을 눈으로 본다 — 삐진 픽셀을 마젠타로 찍는다.

마젠타 = 두상 구간에서 base 실루엣이 헤어 밖으로 나온 자리.
대표가 본 '빡빡이가 왼쪽으로 튀어나옴' / '양옆으로 튀어나옴' 이 여기 찍힌다.

    python char/show_hair_overhang.py [헤어id ...]
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "items")
OUTDIR = os.path.join(HERE, "_diag")
os.makedirs(OUTDIR, exist_ok=True)
CW, CH = 141, 224
ROWNAME = ["정면", "후면", "좌", "우"]

HAIRS = {
    "hair_shaggy": ("더벅", "walk.png"),
    "hair_semileaf": ("세미리프", "walk.png"),
    "hair_ivyleague": ("아이비", "walk.png"),
    "hair_fem_bob": ("여-단발", "walk_female.png"),
    "hair_fem_long": ("여-생머리", "walk_female.png"),
}
want = sys.argv[1:] or list(HAIRS)


def body_mask(bc):
    m = bc[:, :, 3] >= 128
    lab, n = ndimage.label(m, np.ones((3, 3), bool))
    if n == 0:
        return m
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    return lab == (int(np.argmax(sizes)) + 1)


def overhang_mask(hm, bm, skull_h=42):
    out = np.zeros_like(bm)
    ys = np.where(bm.any(axis=1))[0]
    if not len(ys) or not hm.any():
        return out
    top = int(ys.min())
    lim = top + skull_h
    for y in range(top, min(lim + 1, bm.shape[0])):
        bx = np.where(bm[y])[0]
        if not len(bx):
            continue
        hx = np.where(hm[y])[0]
        if not len(hx):
            out[y, bx] = True; continue
        out[y, bx[bx < hx.min()]] = True
        out[y, bx[bx > hx.max()]] = True
    return out


def checker(w, h, s=6):
    im = Image.new("RGBA", (w, h), (242, 242, 246, 255))
    px = im.load()
    for y in range(h):
        for x in range(w):
            if ((x // s) + (y // s)) % 2:
                px[x, y] = (206, 206, 214, 255)
    return im


Z, G = 5, 6
for name in want:
    ko, basef = HAIRS[name]
    hair = np.asarray(Image.open(os.path.join(ITEMS, name + ".png")).convert("RGBA")).astype(int)
    base = np.asarray(Image.open(os.path.join(HERE, basef)).convert("RGBA")).astype(int)
    tiles = []
    print("■ %s (%s)" % (ko, name))
    for r in range(4):
        hc = hair[r * CH:(r + 1) * CH, 0:CW]
        bc = base[r * CH:(r + 1) * CH, 0:CW]
        hm = hc[:, :, 3] >= 128
        bm = body_mask(bc)
        oh = overhang_mask(hm, bm)
        ys = np.where(bm.any(axis=1))[0]
        hy = np.where(hm.any(axis=1))[0]
        print("   [%s] base 머리끝 y=%d / 헤어 최상단 y=%d %s | 삐짐 %d px" % (
            ROWNAME[r], int(ys.min()), int(hy.min()),
            "★헤어가 %dpx 낮다" % (int(hy.min()) - int(ys.min())) if int(hy.min()) > int(ys.min()) else "",
            int(oh.sum())))
        comp = checker(CW, CH)
        comp.alpha_composite(Image.fromarray(bc.astype(np.uint8), "RGBA"))
        comp.alpha_composite(Image.fromarray(hc.astype(np.uint8), "RGBA"))
        mark = np.asarray(comp).copy()
        mark[oh] = (255, 0, 200, 255)
        tiles.append(Image.fromarray(mark, "RGBA"))
    sheet = Image.new("RGBA", ((CW * Z + G) * 4 + G, CH * Z + G * 2), (18, 21, 30, 255))
    for i, t in enumerate(tiles):
        sheet.alpha_composite(t.resize((CW * Z, CH * Z), Image.NEAREST), (G + i * (CW * Z + G), G))
    p = os.path.join(OUTDIR, "overhang_" + name + ".png")
    sheet.save(p)
    print("   ->", os.path.relpath(p, HERE))

