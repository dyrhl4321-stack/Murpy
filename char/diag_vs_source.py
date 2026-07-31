# -*- coding: utf-8 -*-
"""원본 시트(정규화)와 현재 앱 상태를 방향별로 나란히 크게 본다.

대표가 "원본이랑 비슷하게 해달라"고 할 때 **무엇이 다른지 먼저 눈으로 확인**하려고 쓴다.

    python char/diag_vs_source.py hair_f_long.png human_f 0 1
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_hair_layer import (BALD_M, BALD_F, MHAIR, NUKKI, FBASIC, CW, CH,   # noqa: E402
                              ALPHA_BIN, Norm, load, pad_img, binarize)

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = ["정면", "후면", "좌", "우"]
BASEW = {"human": "walk.png", "human_f": "walk_female.png"}
BALD = {"human": BALD_M, "human_f": BALD_F}
SOURCE = {
    "hair_f_long.png": os.path.join(NUKKI, "여자 검정생머리_clean-Photoroom.png"),
    "hair_f_bob_bang.png": os.path.join(NUKKI, "여자 검정단발머리_clean-Photoroom.png"),
    "hair_f_basic.png": os.path.join(FBASIC, "여자기본머리_clean-Photoroom.png"),
    "hair_m_basic.png": os.path.join(MHAIR, "남자기본헤어_clean-Photoroom.png"),
    "hair_m_semileaf.png": os.path.join(MHAIR, "세미리프컷_clean-Photoroom.png"),
}
SCALE = 5


def over(dst, src):
    out = dst.copy()
    m = src[:, :, 3] >= ALPHA_BIN
    out[m] = src[m]
    out[m, 3] = 255
    return out


def main():
    name, body = sys.argv[1], sys.argv[2]
    rows = [int(x) for x in sys.argv[3:]] or [0, 1, 2, 3]
    walk = np.asarray(Image.open(os.path.join(HERE, BASEW[body])).convert("RGBA")).astype(int)
    cur = np.asarray(Image.open(os.path.join(HERE, "items", name)).convert("RGBA")).astype(int)
    norm = Norm(load(BALD[body]))
    src_pad = pad_img(load(SOURCE[name]))

    tiles = []
    for r in rows:
        worn = binarize(norm.cell(src_pad, r, 0))
        bc = walk[r * CH:(r + 1) * CH, 0:CW]
        tiles.append((f"{ROWS[r]} 원본", worn))
        tiles.append((f"{ROWS[r]} 현재", over(bc, cur[r * CH:(r + 1) * CH, 0:CW])))

    pad, lbl = 8, 28
    canvas = Image.new("RGB", ((CW + pad) * len(tiles) + pad, CH + lbl + pad * 2), (248, 248, 248))
    for i, (_t, a) in enumerate(tiles):
        canvas.paste(Image.fromarray(a.astype(np.uint8), "RGBA").convert("RGB"),
                     (pad + i * (CW + pad), lbl + pad))
    big = canvas.resize((canvas.width * SCALE, canvas.height * SCALE), Image.NEAREST)
    d = ImageDraw.Draw(big)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 32)
    except OSError:
        font = ImageFont.load_default()
    for i, (t, _a) in enumerate(tiles):
        d.text(((pad + i * (CW + pad)) * SCALE, 8), t, fill=(20, 20, 20), font=font)
    p = os.path.join(HERE, "_diag", f"vs_source_{name}")
    big.save(p)
    print(f"-> {p}")


if __name__ == "__main__":
    main()
