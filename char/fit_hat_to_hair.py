# -*- coding: utf-8 -*-
"""조합별 모자를 **헤어 부피만큼 자동으로 올린다** — 제미나이 생성 없이.

■ 왜 이 방식인가
모자는 강체다. 헤어마다 달라야 하는 건 모양이 아니라 **얹히는 높이**다.
빡빡이엔 밀착, 기본헤어엔 머리카락 두께만큼, 긴 생머리엔 더 위로.
조합마다 AI 로 새로 뽑으면 12장 × 검수 = 노가다인데, 이건 계산으로 끝난다.

■ 어떻게
프레임마다 **헤어가 base 두상보다 얼마나 위로 솟았는지**를 재고(부피),
그만큼 모자를 위로 평행이동한다. 좌우 중심은 그대로 둔다.
모자 모양·색은 하나도 안 바꾼다 — 위치만 옮긴다.

    python char/fit_hat_to_hair.py            # 미리보기(수치만)
    python char/fit_hat_to_hair.py --apply
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_hair_layer import shift   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "items")
CW, CH = 141, 224
ALPHA_BIN = 128
ROWS = ["정면", "후면", "좌", "우"]
MAX_LIFT = 8       # 너무 많이 띄우면 붕 뜬다

PAIRS = [
    ("walk.png", ["hair_m_basic", "hair_ivyleague", "hair_m_semileaf"],
     ["hat_beanie", "hat_ladodgers"]),
    ("walk_female.png", ["hair_f_basic", "hair_f_bob_bang", "hair_f_long"],
     ["hat_f_beanie", "hat_f_ladodgers"]),
]


def top_of(m):
    ys = np.where(m.any(axis=1))[0]
    return int(ys.min()) if len(ys) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    for base_n, hairs, hats in PAIRS:
        base = np.asarray(Image.open(os.path.join(HERE, base_n))
                          .convert("RGBA")).astype(int)
        for h in hairs:
            hp = os.path.join(ITEMS, h + ".png")
            if not os.path.exists(hp):
                continue
            ha = np.asarray(Image.open(hp).convert("RGBA")).astype(int)
            # 프레임별 헤어 부피 = base 두상 최상단 - 헤어 최상단 (양수면 헤어가 더 위)
            lift = {}
            for r in range(4):
                for c in range(3):
                    bm = base[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW, 3] >= ALPHA_BIN
                    hm = ha[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW, 3] >= ALPHA_BIN
                    bt, ht = top_of(bm), top_of(hm)
                    v = 0 if (bt is None or ht is None) else max(0, bt - ht)
                    lift[(r, c)] = min(v, MAX_LIFT)
            per_row = [lift[(r, 0)] for r in range(4)]
            print(f"{h:18s} 헤어 부피(정면/후면/좌/우) {per_row}")

            for hat in hats:
                tp = os.path.join(ITEMS, hat + ".png")
                if not os.path.exists(tp):
                    print(f"   !! 모자 없음 {hat}")
                    continue
                ta = np.asarray(Image.open(tp).convert("RGBA")).astype(int)
                out = np.zeros_like(ta)
                for r in range(4):
                    for c in range(3):
                        cell = ta[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
                        out[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW] = \
                            shift(cell, 0, -lift[(r, c)])      # 위로
                out[:, :, 3] = np.where(out[:, :, 3] >= ALPHA_BIN, 255, 0)
                out[out[:, :, 3] == 0] = 0
                q = os.path.join(ITEMS, f"{hat}__{h}.png")
                if args.apply:
                    Image.fromarray(out.astype(np.uint8), "RGBA").save(q)
                    print(f"   -> {os.path.basename(q)}  (올림 {per_row})")
                else:
                    print(f"   (미리보기) {os.path.basename(q)}  올림 {per_row}")


if __name__ == "__main__":
    main()
