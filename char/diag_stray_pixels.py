# -*- coding: utf-8 -*-
"""걸음 프레임에만 박힌 불순물 픽셀을 찾는다 (2026-07-31 대표가 발견한 결함 유형).

■ 왜 이걸 자동으로 찾아야 하나
남캐 헤어 3종의 걸음 프레임 이마에 **세로 ㅣ 모양 불순물**이 박혀 있었다.
대표 설명: "세로선이 하나 박혀 있으면 그 선을 기준으로 앞뒤가 튀어나온 것처럼 보인다."
나는 이걸 'base 의 두상과 얼굴이 따로 움직인다'는 기하 문제로 오해하고 커버 영역을
계산해 채우다가 세미리프컷 머리 결을 뭉갰다. **증상을 규칙으로 쫓기 전에 픽셀을 봐야 한다.**

■ 어떻게 찾나
불순물은 **정지 프레임엔 없고 걸음 프레임에만** 있었고, 열마다 자리가 달랐다.
그래서 3열을 서로 맞춰 놓고 비교하면 드러난다:
  col0 을 각 열의 base 두상 위치로 옮긴 것 vs 그 열의 실제 헤어 → 어긋난 픽셀이 후보.
얇은 세로 구조(폭 ≤2px)만 남기면 진짜 불순물에 가깝다.

    python char/diag_stray_pixels.py hair_m_basic.png human
    python char/diag_stray_pixels.py            # 등록된 헤어 전부
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_hair_layer import skull_ref, shift   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CW, CH = 141, 224
ALPHA_BIN = 128
ROWS = ["정면", "후면", "좌", "우"]
BASEW = {"human": "walk.png", "human_f": "walk_female.png"}
ALL = [("hair_m_basic.png", "human"), ("hair_ivyleague.png", "human"),
       ("hair_m_semileaf.png", "human"), ("hair_f_basic.png", "human_f"),
       ("hair_f_bob_bang.png", "human_f"), ("hair_f_long.png", "human_f")]


def check(name, body):
    base_name = BASEW[body]
    base = np.asarray(Image.open(os.path.join(HERE, base_name)).convert("RGBA")).astype(int)
    hair = np.asarray(Image.open(os.path.join(HERE, "items", name)).convert("RGBA")).astype(int)
    print(f"\n■ {name}")
    worst = 0
    for r in range(4):
        bm0 = base[r * CH:(r + 1) * CH, 0:CW, 3] >= ALPHA_BIN
        t0, x0 = skull_ref(bm0)
        h0 = hair[r * CH:(r + 1) * CH, 0:CW]
        for c in range(1, 3):
            bmc = base[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW, 3] >= ALPHA_BIN
            tc, xc = skull_ref(bmc)
            dx, dy = int(round(xc - x0)), int(tc - t0)
            expect = shift(h0, dx, dy)[:, :, 3] >= ALPHA_BIN     # col0 을 이 열로 옮긴 모양
            actual = hair[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW, 3] >= ALPHA_BIN
            extra = actual & ~expect                              # 이 열에만 있는 픽셀
            if not extra.any():
                continue
            # 얇은 세로 구조만 남긴다 (가로로 1~2px 폭)
            thin = extra & ~ndimage.binary_erosion(extra, np.ones((1, 3), bool))
            lab, n = ndimage.label(thin, np.ones((3, 3), bool))
            spots = []
            for i in range(1, n + 1):
                m = lab == i
                ys, xs = np.where(m)
                if m.sum() >= 3 and (ys.max() - ys.min()) >= 2 and (xs.max() - xs.min()) <= 2:
                    spots.append((int(m.sum()), int(xs.mean()), int(ys.mean())))
            if spots:
                spots.sort(reverse=True)
                worst += len(spots)
                s = " · ".join(f"{a}px@x{b},y{c2}" for a, b, c2 in spots[:5])
                print(f"   {ROWS[r]:2s} col{c}  세로 불순물 후보 {len(spots)}곳  {s}")
    if not worst:
        print("   깨끗함 — 걸음 프레임에만 있는 세로 불순물 없음")
    return worst


def main():
    if len(sys.argv) > 2:
        check(sys.argv[1], sys.argv[2])
    else:
        tot = sum(check(n, b) for n, b in ALL)
        print(f"\n합계 후보 {tot}곳")


if __name__ == "__main__":
    main()
