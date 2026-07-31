# -*- coding: utf-8 -*-
"""캐릭터(몸통) 선택 화면용 미리보기 시트를 만든다 — base 에 기본헤어를 씌운 모습.

몸통 카드가 `walk.png` 를 그대로 배경이미지로 쓰다 보니 **빡빡이로 보였다**(대표 지적).
꾸미기 전 기본 상태는 기본헤어를 쓴 모습이 맞다.

시트 전체(423x896, 3열x4행) 형태를 유지해야 한다 — 카드가 background-position 으로
첫 프레임만 잘라 쓰기 때문이다.

    python char/build_body_preview.py
"""
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "items")
ALPHA_BIN = 128

PAIRS = [
    ("walk.png", "hair_m_basic.png", "preview_human.png"),
    ("walk_female.png", "hair_f_basic.png", "preview_human_f.png"),
]


def main():
    for base_n, hair_n, out_n in PAIRS:
        b = np.asarray(Image.open(os.path.join(HERE, base_n)).convert("RGBA")).astype(int)
        h = np.asarray(Image.open(os.path.join(ITEMS, hair_n)).convert("RGBA")).astype(int)
        if b.shape != h.shape:
            print(f"!! 규격 불일치 {base_n} {b.shape} vs {hair_n} {h.shape}")
            continue
        out = b.copy()
        m = h[:, :, 3] >= ALPHA_BIN
        out[m] = h[m]
        out[m, 3] = 255
        p = os.path.join(HERE, out_n)
        Image.fromarray(out.astype(np.uint8), "RGBA").save(p)
        print(f"{base_n} + {hair_n} -> char/{out_n}  ({out.shape[1]}x{out.shape[0]})")


if __name__ == "__main__":
    main()
