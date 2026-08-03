# -*- coding: utf-8 -*-
"""헤어 × 모자 전 조합을 한 장에 펼쳐 본다 (조합 결함 현황 파악용).

앱 z 순서: body -> ... -> hair -> hat
헤어 항목의 hatVariants[모자id] 가 있으면 그 시트로 **대체**된다(null 이면 헤어 숨김).
이 스크립트도 같은 규칙을 그대로 흉내낸다.

    python char/diag_hat_matrix.py human
    python char/diag_hat_matrix.py human_f
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "items")
CW, CH = 141, 224
ALPHA_BIN = 128
ROWS = ["정면", "후면", "좌", "우"]
BASEW = {"human": "walk.png", "human_f": "walk_female.png"}
HEAD_H = 108
SCALE = 3

HAIRS = {
    "human": ["hair_m_basic", "hair_ivyleague", "hair_m_semileaf"],
    "human_f": ["hair_f_basic", "hair_f_bob_bang", "hair_f_long"],
}
HATS = ["hat_beanie", "hat_ladodgers"]
# 대체 시트는 `<헤어>__<모자>.png` 규칙으로 만든다(char/build_hat_variants.py).
# 파일이 있으면 그걸 쓰고, 없으면 대체 없음(헤어 그대로)으로 본다 — 앱 등록과 같은 결과.
def variant_of(hair, hat):
    n = f"{hair}__{hat}"
    return n if os.path.exists(os.path.join(ITEMS, n + ".png")) else None


def load(name):
    p = os.path.join(ITEMS, name + ".png")
    if not os.path.exists(p):
        return None
    return np.asarray(Image.open(p).convert("RGBA")).astype(int)


def over(dst, src):
    if src is None:
        return dst
    out = dst.copy()
    m = src[:, :, 3] >= ALPHA_BIN
    out[m] = src[m]
    out[m, 3] = 255
    return out


def main():
    body = sys.argv[1] if len(sys.argv) > 1 else "human"
    base = np.asarray(Image.open(os.path.join(HERE, BASEW[body])).convert("RGBA")).astype(int)
    hairs = HAIRS[body]

    cols = []          # (라벨, [4방향 셀])
    for h in hairs:
        for hat in [None] + HATS:
            hair_arr = load(h)
            if hat:
                alt = variant_of(h, hat)
                if alt:
                    hair_arr = load(alt)
            hat_arr = load(hat) if hat else None
            cells = []
            for r in range(4):
                comp = base[r * CH:(r + 1) * CH, 0:CW].copy()
                comp = over(comp, hair_arr[r * CH:(r + 1) * CH, 0:CW] if hair_arr is not None else None)
                comp = over(comp, hat_arr[r * CH:(r + 1) * CH, 0:CW] if hat_arr is not None else None)
                cells.append(comp[:HEAD_H])
            lbl = h.replace("hair_", "") + ("\n+ " + hat.replace("hat_", "") if hat else "\n(모자 없음)")
            cols.append((lbl, cells))

    pad, lbl_h = 6, 34
    W = (CW + pad) * len(cols) + pad
    H = (HEAD_H + pad) * 4 + lbl_h + pad
    canvas = Image.new("RGB", (W, H), (248, 248, 248))
    for i, (_l, cells) in enumerate(cols):
        for r, cell in enumerate(cells):
            canvas.paste(Image.fromarray(cell.astype(np.uint8), "RGBA").convert("RGB"),
                         (pad + i * (CW + pad), lbl_h + r * (HEAD_H + pad)))
    big = canvas.resize((W * SCALE, H * SCALE), Image.NEAREST)
    d = ImageDraw.Draw(big)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 24)
    except OSError:
        font = ImageFont.load_default()
    for i, (l, _c) in enumerate(cols):
        d.text(((pad + i * (CW + pad)) * SCALE, 4), l, fill=(20, 20, 20), font=font)
    p = os.path.join(HERE, "_diag", f"hatmatrix_{body}.png")
    big.save(p)
    print(f"-> {p}   (행=정면/후면/좌/우, 열=헤어×모자)")


if __name__ == "__main__":
    main()
