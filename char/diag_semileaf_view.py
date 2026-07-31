# -*- coding: utf-8 -*-
"""앱과 같은 방식(base 위에 헤어 알파합성, NEAREST 정수배)으로 4방향 col0 을 그려 눈으로 본다.

왼쪽 = 합성 결과 / 오른쪽 = 같은 그림에 'base 실루엣 밖 헤어'만 마젠타로 표시.
    python char/diag_semileaf_view.py hair_m_semileaf.png
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
CW, CH = 141, 224
ALPHA_BIN = 128
SCALE = 4


def cell(sheet, r, c):
    return sheet[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]


def over(dst, src):
    """src(RGBA) 를 dst 위에 알파 합성. 앱은 알파 128 이진화 시트를 그대로 얹는다."""
    out = dst.copy()
    m = src[:, :, 3] >= ALPHA_BIN
    out[m] = src[m]
    out[m, 3] = 255
    return out


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "hair_m_semileaf.png"
    base = np.asarray(Image.open(os.path.join(HERE, "walk.png")).convert("RGBA")).astype(int)
    hs = np.asarray(Image.open(os.path.join(HERE, "items", name)).convert("RGBA")).astype(int)

    canvas = Image.new("RGB", (CW * 4 * 2 + 20, CH), (250, 250, 250))
    for r in range(4):
        bc, hc = cell(base, r, 0), cell(hs, r, 0)
        comp = over(bc, hc)
        canvas.paste(Image.fromarray(comp.astype(np.uint8), "RGBA").convert("RGB"), (r * CW, 0))
        mark = comp.copy()
        outside = (hc[:, :, 3] >= ALPHA_BIN) & ~(bc[:, :, 3] >= ALPHA_BIN)
        mark[outside] = [255, 0, 255, 255]
        canvas.paste(Image.fromarray(mark.astype(np.uint8), "RGBA").convert("RGB"),
                     (CW * 4 + 20 + r * CW, 0))

    p = os.path.join(HERE, "_diag", f"view_{name}")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    canvas.resize((canvas.width * SCALE, canvas.height * SCALE), Image.NEAREST).save(p)
    print(f"-> {p}")


if __name__ == "__main__":
    main()
