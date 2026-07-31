# -*- coding: utf-8 -*-
"""한 아이템의 12프레임(4방향×3열)을 전부 펼쳐 걸음 중 어긋남을 눈으로 본다.

대표(7-31): "오른쪽으로 이동할 때 이마나 입이 계속 튀어나온다. 걸을 때 왔다갔다 한다."

헤어는 방향당 1프레임을 3열에 복제하고 **두상 기준점**으로만 정렬한다. 그런데 base 는
걸음 프레임마다 얼굴 요소(코·입)가 두상과 다르게 움직일 수 있다. 그러면 헤어가 덮어야 할
이마가 열리거나 얼굴이 헤어 밖으로 나온다.

    python char/diag_walk_frames.py hair_m_basic.png human
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_regions import regions as base_regions, skinmask   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CW, CH = 141, 224
ALPHA_BIN = 128
ROWS = ["정면", "후면", "좌", "우"]
BASEW = {"human": "walk.png", "human_f": "walk_female.png"}
SCALE = 5
HEAD_H = 110       # 머리 부분만 크게


def over(dst, src):
    out = dst.copy()
    m = src[:, :, 3] >= ALPHA_BIN
    out[m] = src[m]
    out[m, 3] = 255
    return out


def main():
    name = sys.argv[1]
    body = sys.argv[2] if len(sys.argv) > 2 else "human"
    base_name = BASEW[body]
    base = np.asarray(Image.open(os.path.join(HERE, base_name)).convert("RGBA")).astype(int)
    hair = np.asarray(Image.open(os.path.join(HERE, "items", name)).convert("RGBA")).astype(int)

    print(f"■ {name}  ({base_name})")
    tiles = []
    for r in range(4):
        for c in range(3):
            bc = base[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
            hc = hair[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
            comp = over(bc, hc)
            h = hc[:, :, 3] >= ALPHA_BIN
            must, _keep = base_regions(bc, r, base_name, c)
            bare = must & ~h                       # 머리카락이 덮어야 하는데 열린 곳
            vis = comp.copy()
            vis[bare] = [255, 0, 255, 255]
            tiles.append((f"{ROWS[r]}-{c}", vis[:HEAD_H], int(bare.sum())))
        row_vals = [t[2] for t in tiles[-3:]]
        print(f"   {ROWS[r]:2s}  덮여야 하는데 열린 픽셀  col0 {row_vals[0]:4d} · "
              f"col1 {row_vals[1]:4d} · col2 {row_vals[2]:4d}"
              f"   {'★열별 차이 큼' if max(row_vals) - min(row_vals) > 20 else ''}")

    pad, lbl = 6, 22
    cols = 3
    rows_n = 4
    W = (CW + pad) * cols + pad
    H = (HEAD_H + lbl + pad) * rows_n + pad
    canvas = Image.new("RGB", (W, H), (248, 248, 248))
    for i, (t, a, _n) in enumerate(tiles):
        r, c = divmod(i, 3)
        x = pad + c * (CW + pad)
        y = pad + r * (HEAD_H + lbl + pad) + lbl
        canvas.paste(Image.fromarray(a.astype(np.uint8), "RGBA").convert("RGB"), (x, y))
    big = canvas.resize((W * SCALE, H * SCALE), Image.NEAREST)
    d = ImageDraw.Draw(big)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 26)
    except OSError:
        font = ImageFont.load_default()
    for i, (t, _a, n) in enumerate(tiles):
        r, c = divmod(i, 3)
        x = (pad + c * (CW + pad)) * SCALE
        y = (pad + r * (HEAD_H + lbl + pad)) * SCALE
        d.text((x, y), f"{t}  열린 {n}px", fill=(20, 20, 20), font=font)
    p = os.path.join(HERE, "_diag", f"walk_{name}")
    big.save(p)
    print(f"   -> {p}  (마젠타 = 머리카락이 덮어야 하는데 열린 곳)")


if __name__ == "__main__":
    main()
