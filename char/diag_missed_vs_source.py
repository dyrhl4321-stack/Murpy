# -*- coding: utf-8 -*-
"""대표가 손으로 채운 자리가 '원본 시트에는 원래 있던 머리카락'인지 확인한다.

이게 참이면 자동화의 방향이 바뀐다:
  구멍을 '주변 색으로 메우기'(추측) → **원본에서 누락분을 되찾기**(정답 복원)
세미리프컷 정면 뒷머리도 정확히 같은 패턴이었다.

    python char/diag_missed_vs_source.py
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_hair_layer import (BALD_F, NUKKI, FBASIC, CW, CH, ALPHA_BIN, SKIN_R,   # noqa: E402
                              Norm, load, pad_img, binarize)

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = ["정면", "후면", "좌", "우"]

CASES = [
    ("hair_f_long.png", "before_hair_f_long.png",
     os.path.join(NUKKI, "여자 검정생머리_clean-Photoroom.png")),
    ("hair_f_bob_bang.png", "before_hair_f_bob_bang.png",
     os.path.join(NUKKI, "여자 검정단발머리_clean-Photoroom.png")),
    ("hair_f_basic.png", None,
     os.path.join(FBASIC, "여자기본머리_clean-Photoroom.png")),
]


def is_skin(a):
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    return (R >= SKIN_R) & (R > G + 20) & (G > B)


def main():
    norm = Norm(load(BALD_F))
    for item, before, src in CASES:
        if before is None:
            continue
        p_now = os.path.join(HERE, "items", item)
        p_bef = os.path.join(HERE, "_diag", before)
        if not (os.path.exists(p_now) and os.path.exists(p_bef) and os.path.exists(src)):
            print(f"!! 건너뜀 {item}")
            continue
        now = np.asarray(Image.open(p_now).convert("RGBA")).astype(int)
        bef = np.asarray(Image.open(p_bef).convert("RGBA")).astype(int)
        src_pad = pad_img(load(src))

        print(f"\n■ {item}   원본 {os.path.basename(src)}")
        tot_h = tot_in = 0
        for r in range(4):
            worn = binarize(norm.cell(src_pad, r, 0))
            wm = (worn[:, :, 3] >= ALPHA_BIN) & ~is_skin(worn)   # 원본의 머리카락
            for c in range(3):
                a1 = bef[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW, 3] >= ALPHA_BIN
                a2 = now[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW, 3] >= ALPHA_BIN
                human = a2 & ~a1                                  # 대표가 채운 자리
                if not human.any():
                    continue
                tot_h += int(human.sum())
                tot_in += int((human & wm).sum())
            if tot_h:
                pass
        if tot_h:
            print(f"   대표가 채운 {tot_h}px 중 원본에도 머리카락인 곳 {tot_in}px"
                  f"  ({100.0 * tot_in / tot_h:.0f}%)")
        # 방향별
        for r in range(4):
            worn = binarize(norm.cell(src_pad, r, 0))
            wm = (worn[:, :, 3] >= ALPHA_BIN) & ~is_skin(worn)
            h = i = 0
            for c in range(3):
                a1 = bef[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW, 3] >= ALPHA_BIN
                a2 = now[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW, 3] >= ALPHA_BIN
                hu = a2 & ~a1
                h += int(hu.sum()); i += int((hu & wm).sum())
            if h:
                print(f"     {ROWS[r]:2s}  채움 {h:4d}px 중 원본에 있음 {i:4d}px ({100.0*i/h:3.0f}%)")


if __name__ == "__main__":
    main()
