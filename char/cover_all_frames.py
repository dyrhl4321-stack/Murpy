# -*- coding: utf-8 -*-
"""걸음 3프레임 **전부**를 덮도록 기준 프레임의 헤어를 넓힌다.

■ 대표 증상 (7-31)
"오른쪽으로 이동할 때 이마나 입이 계속 튀어나온다. 프레임마다 왔다갔다 한다."

■ 원인
헤어는 방향당 1프레임을 3열에 복제한다(모양 고정 = 깜빡임 방지). 그런데 base 는 걸음
프레임마다 두상·얼굴이 다르게 움직인다(실측: 두상과 얼굴이 서로 최대 3.4px 어긋난다).
그래서 한 프레임에 맞춘 헤어는 **다른 프레임에서 덮어야 할 곳을 놓친다** —
이마가 열렸다 닫혔다 하는 게 이 때문이다.

■ 해법
열별로 헤어를 다르게 만들면 안 된다(모양이 달라져 걸을 때 출렁인다).
대신 **각 열이 요구하는 커버 영역을 기준 프레임 좌표로 역이동해 합집합**을 만들고,
그 합집합을 기준 프레임에서 한 번에 덮는다. 그 뒤 3열에 복제한다.
→ 모양은 3열 동일(깜빡임 없음) + 어느 프레임에서도 두상이 안 열린다.

색은 지어내지 않는다. 가장 가까운 기존 머리카락 픽셀의 색을 복사한다.

    python char/cover_all_frames.py hair_m_semileaf.png human            # 미리보기
    python char/cover_all_frames.py hair_m_semileaf.png human --apply
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_regions import regions as base_regions   # noqa: E402
from build_hair_layer import skull_ref, shift      # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CW, CH = 141, 224
ALPHA_BIN = 128
ROWS = ["정면", "후면", "좌", "우"]
BASEW = {"human": "walk.png", "human_f": "walk_female.png"}
GROW = 0          # 커버 영역 여유(px). --grow 1 로 준다


def main():
    name = sys.argv[1]
    body = sys.argv[2] if len(sys.argv) > 2 else "human"
    apply = "--apply" in sys.argv
    base_name = BASEW[body]
    global GROW
    if "--grow" in sys.argv:
        GROW = int(sys.argv[sys.argv.index("--grow") + 1])

    base = np.asarray(Image.open(os.path.join(HERE, base_name)).convert("RGBA")).astype(int)
    p = os.path.join(HERE, "items", name)
    a = np.asarray(Image.open(p).convert("RGBA")).astype(int)
    out = a.copy()

    print(f"■ {name}  ({base_name})")
    total = 0
    for r in range(4):
        bc0 = base[r * CH:(r + 1) * CH, 0:CW]
        bm0 = bc0[:, :, 3] >= ALPHA_BIN
        t0, x0 = skull_ref(bm0)

        # 각 열의 MUST 를 기준(col0) 좌표계로 역이동해 합집합
        union = np.zeros(bm0.shape, bool)
        for c in range(3):
            bcc = base[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
            bmc = bcc[:, :, 3] >= ALPHA_BIN
            tc, xc = skull_ref(bmc)
            dx, dy = int(round(xc - x0)), int(tc - t0)
            must, _keep = base_regions(bcc, r, base_name, c)
            m3 = np.zeros((CH, CW, 4), int)
            m3[:, :, 3] = np.where(must, 255, 0)
            back = shift(m3, -dx, -dy)[:, :, 3] > 0     # col0 좌표계로 되돌린다
            union |= back
        # 평행이동은 정수 픽셀이라 반올림 오차가 남고, MUST 모양 자체도 열마다 조금씩 다르다.
        # 여유를 주면 남은 노출이 줄어든다. 얼굴·귀는 아래 keep0 으로 계속 지킨다.
        if GROW:
            union = ndimage.binary_dilation(union, np.ones((3, 3), bool), iterations=GROW)
            union &= bm0 | ndimage.binary_dilation(bm0, np.ones((3, 3), bool), iterations=GROW)

        hc = out[r * CH:(r + 1) * CH, 0:CW]
        h = hc[:, :, 3] >= ALPHA_BIN
        need = union & ~h
        # 얼굴·귀는 기준 프레임 기준으로 한 번 더 지킨다
        _must0, keep0 = base_regions(bc0, r, base_name, 0)
        need &= ~keep0

        n = int(need.sum())
        print(f"   {ROWS[r]:2s}  3열 합집합이 요구 {int(union.sum())}px · 지금 안 덮인 곳 {n}px")
        if n:
            # 가장 가까운 머리카락 색을 복사한다 (색을 지어내지 않는다)
            _d, idx = ndimage.distance_transform_edt(~h, return_indices=True)
            ys, xs = np.where(need)
            hc[ys, xs] = hc[idx[0][ys, xs], idx[1][ys, xs]]
            hc[ys, xs, 3] = 255
            total += n

        # 기준 프레임을 3열에 복제 (열별 base 두상 위치로 평행이동)
        srcc = out[r * CH:(r + 1) * CH, 0:CW].copy()
        for c in range(1, 3):
            bmc = base[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW, 3] >= ALPHA_BIN
            tc, xc = skull_ref(bmc)
            dx, dy = int(round(xc - x0)), int(tc - t0)
            out[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW] = shift(srcc, dx, dy)

    out[:, :, 3] = np.where(out[:, :, 3] >= ALPHA_BIN, 255, 0)
    out[out[:, :, 3] == 0] = 0
    print(f"   합계 {total}px 채움")

    if apply:
        Image.fromarray(out.astype(np.uint8), "RGBA").save(p)
        print(f"   -> 적용됨 {p}")
    else:
        q = os.path.join(HERE, "_diag", f"cover_{name}")
        Image.fromarray(out.astype(np.uint8), "RGBA").save(q)
        print(f"   -> 미리보기 {q}")


if __name__ == "__main__":
    main()
