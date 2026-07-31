# -*- coding: utf-8 -*-
"""원본 시트를 base 변환으로 정규화해 base 와 나란히 본다 (추출 전 상태 확인용).

    python char/diag_src_sheet.py "여캐/회색후드집업_clean-Photoroom.png" human_f
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_hair_layer import (BALD_M, BALD_F, DESK, CW, CH, ALPHA_BIN,   # noqa: E402
                              Norm, load, pad_img, binarize)

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = ["정면", "후면", "좌", "우"]
BASEW = {"human": "walk.png", "human_f": "walk_female.png"}
BALD = {"human": BALD_M, "human_f": BALD_F}
NUKKI_ROOT = os.path.join(DESK, "머피_로고삭제툴_에셋보관")
SCALE = 4


def main():
    rel = sys.argv[1]
    body = sys.argv[2] if len(sys.argv) > 2 else "human_f"
    src = os.path.join(NUKKI_ROOT, rel.replace("/", os.sep))
    if not os.path.exists(src):
        print(f"!! 없음 {src}")
        return

    walk = np.asarray(Image.open(os.path.join(HERE, BASEW[body])).convert("RGBA")).astype(int)
    norm = Norm(load(BALD[body]))
    pad = pad_img(load(src))

    tiles = []
    for r in range(4):
        tiles.append((f"{ROWS[r]} base", walk[r * CH:(r + 1) * CH, 0:CW]))
        tiles.append((f"{ROWS[r]} 원본", binarize(norm.cell(pad, r, 0))))

    p_, lbl = 8, 22
    W = (CW + p_) * len(tiles) + p_
    canvas = Image.new("RGB", (W, CH + lbl + p_ * 2), (248, 248, 248))
    for i, (_t, a) in enumerate(tiles):
        canvas.paste(Image.fromarray(a.astype(np.uint8), "RGBA").convert("RGB"),
                     (p_ + i * (CW + p_), lbl + p_))
    big = canvas.resize((canvas.width * SCALE, canvas.height * SCALE), Image.NEAREST)
    d = ImageDraw.Draw(big)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    for i, (t, _a) in enumerate(tiles):
        d.text(((p_ + i * (CW + p_)) * SCALE, 6), t, fill=(20, 20, 20), font=font)
    out = os.path.join(HERE, "_diag", "src_" + os.path.basename(src))
    big.save(out)
    print(f"-> {out}")


if __name__ == "__main__":
    main()
