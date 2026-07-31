# -*- coding: utf-8 -*-
"""여러 아이템을 앱과 같은 z 순서로 합성해 조합 버그를 본다.

앱 레이어 순서: body → bottom → shoes → top → hair → hat → acc

    python char/diag_combo.py human top_redhood hair_ivyleague
    python char/diag_combo.py human top_redhood hair_ivyleague --row 1
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
CW, CH = 141, 224
ALPHA_BIN = 128
ROWS = ["정면", "후면", "좌", "우"]
BASEW = {"human": "walk.png", "human_f": "walk_female.png"}
SCALE = 5


def over(dst, src):
    out = dst.copy()
    m = src[:, :, 3] >= ALPHA_BIN
    out[m] = src[m]
    out[m, 3] = 255
    return out


def main():
    args = sys.argv[1:]
    rows = [0, 1, 2, 3]
    if "--row" in args:
        i = args.index("--row")
        rows = [int(args[i + 1])]
        args = args[:i] + args[i + 2:]       # 옵션과 그 값을 둘 다 뺀다
    body = args[0]
    items = args[1:]

    base = np.asarray(Image.open(os.path.join(HERE, BASEW[body])).convert("RGBA")).astype(int)
    layers = []
    for it in items:
        p = os.path.join(HERE, "items", it + ".png")
        layers.append((it, np.asarray(Image.open(p).convert("RGBA")).astype(int)))

    tiles = []
    for r in rows:
        for c in range(3):
            comp = base[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW].copy()
            for _n, arr in layers:
                comp = over(comp, arr[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW])
            tiles.append((f"{ROWS[r]}-{c}", comp))

    pad, lbl = 8, 24
    cols = 3
    rn = len(tiles) // 3
    W = (CW + pad) * cols + pad
    H = (CH + lbl + pad) * rn + pad
    canvas = Image.new("RGB", (W, H), (248, 248, 248))
    for i, (_t, a) in enumerate(tiles):
        rr, cc = divmod(i, 3)
        canvas.paste(Image.fromarray(a.astype(np.uint8), "RGBA").convert("RGB"),
                     (pad + cc * (CW + pad), pad + rr * (CH + lbl + pad) + lbl))
    big = canvas.resize((W * SCALE, H * SCALE), Image.NEAREST)
    d = ImageDraw.Draw(big)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 26)
    except OSError:
        font = ImageFont.load_default()
    for i, (t, _a) in enumerate(tiles):
        rr, cc = divmod(i, 3)
        d.text(((pad + cc * (CW + pad)) * SCALE, (pad + rr * (CH + lbl + pad)) * SCALE),
               t, fill=(20, 20, 20), font=font)
    p = os.path.join(HERE, "_diag", "combo_" + "_".join(items) + ".png")
    big.save(p)
    print(f"-> {p}   (z: base → {' → '.join(items)})")


if __name__ == "__main__":
    main()
