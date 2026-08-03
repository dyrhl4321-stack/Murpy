# -*- coding: utf-8 -*-
"""헤어를 착용한 캐릭터 시트를 마젠타 배경으로 만든다 (모자 생성 입력용).

대표가 이 시트를 나노바나나에 넣고 "모자 씌워줘"로 **헤어×모자 조합**을 생성한다.
그래서 앱 자산이 아니라 **AI 입력 그림**이다 — 배경을 형광 마젠타로 채우고
반투명을 없앤다(투명 PNG 를 넣으면 배경을 검게 인식해 결과가 흐려진다).

    python char/build_hair_worn_sheets.py
"""
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "items")
OUT = r"C:\Users\allys\Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차\헤어\_모자생성용_헤어착용시트"
ALPHA_BIN = 128
BG = np.array([255, 0, 255, 255])      # 형광 마젠타 (캐릭터에 없는 색 — 누끼 안전)

PAIRS = [
    ("walk.png", "hair_m_basic", "남_기본헤어"),
    ("walk.png", "hair_ivyleague", "남_아이비리그컷"),
    ("walk.png", "hair_m_semileaf", "남_세미리프컷"),
    ("walk_female.png", "hair_f_basic", "여_기본헤어"),
    ("walk_female.png", "hair_f_bob_bang", "여_앞머리단발"),
    ("walk_female.png", "hair_f_long", "여_긴생머리"),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    for base_n, hair_id, label in PAIRS:
        bp = os.path.join(HERE, base_n)
        hp = os.path.join(ITEMS, hair_id + ".png")
        if not (os.path.exists(bp) and os.path.exists(hp)):
            print(f"!! 없음 {label}")
            continue
        b = np.asarray(Image.open(bp).convert("RGBA")).astype(int)
        h = np.asarray(Image.open(hp).convert("RGBA")).astype(int)
        out = b.copy()
        m = h[:, :, 3] >= ALPHA_BIN
        out[m] = h[m]
        out[m, 3] = 255
        # 배경을 마젠타로 채우고 전부 불투명하게
        out[out[:, :, 3] < ALPHA_BIN] = BG
        out[:, :, 3] = 255
        p = os.path.join(OUT, f"{label}.png")
        Image.fromarray(out.astype(np.uint8), "RGBA").save(p)
        print(f"{label:16s} {out.shape[1]}x{out.shape[0]}  -> {p}")


if __name__ == "__main__":
    main()
