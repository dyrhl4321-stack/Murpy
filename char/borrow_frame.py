# -*- coding: utf-8 -*-
"""망가진 프레임을 같은 방향의 **다른 프레임에서 빌려와** 채운다.

원본 AI 가 특정 프레임만 자세를 base 와 다르게 그리면 차분 추출이 몸 윤곽선을 옷으로
오인한다(회색 후드집업 우 col2). 색·위치로 구분이 안 돼 자동 보정이 불가능하고,
수동으로 고치기엔 손상이 크다.

대신 **같은 방향의 멀쩡한 프레임**을 몸 기준점에 맞춰 옮겨 채운다.
상의처럼 걸음에 따른 변형이 작은 슬롯에서 실용적이다(팔이 크게 흔들리면 어색해질 수 있어
반드시 렌더로 확인할 것).

    python char/borrow_frame.py top_f_hoodzip human_f 3 2 --from 0
    python char/borrow_frame.py top_f_hoodzip human_f 3 2 --from 0 --apply
"""
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
BASEW = {"human": "walk.png", "human_f": "walk_female.png"}


def torso_ref(bm):
    """몸통 기준점 — 머리 아래(어깨~허리) 구간의 중심 x, 위쪽 y.

    발이나 머리보다 상의 정합에 맞다. 걸음에 따라 팔이 흔들려도 몸통은 덜 움직인다.
    """
    ys = np.where(bm.any(axis=1))[0]
    top, bot = int(ys.min()), int(ys.max())
    y0 = top + int((bot - top) * 0.42)      # 대략 어깨
    y1 = top + int((bot - top) * 0.62)      # 대략 허리
    band = bm[y0:y1]
    xs = np.where(band.any(axis=0))[0]
    return y0, (int(xs.min()) + int(xs.max())) / 2.0


def main():
    if len(sys.argv) < 5:
        print(__doc__)
        return
    name, body, row, col = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    src_col = int(sys.argv[sys.argv.index("--from") + 1]) if "--from" in sys.argv else 0
    apply = "--apply" in sys.argv

    base = np.asarray(Image.open(os.path.join(HERE, BASEW[body])).convert("RGBA")).astype(int)
    p = os.path.join(ITEMS, name + ".png")
    a = np.asarray(Image.open(p).convert("RGBA")).astype(int)

    bm_s = base[row * CH:(row + 1) * CH, src_col * CW:(src_col + 1) * CW, 3] >= ALPHA_BIN
    bm_d = base[row * CH:(row + 1) * CH, col * CW:(col + 1) * CW, 3] >= ALPHA_BIN
    ys, xs = torso_ref(bm_s)
    yd, xd = torso_ref(bm_d)
    dx, dy = int(round(xd - xs)), int(yd - ys)

    src = a[row * CH:(row + 1) * CH, src_col * CW:(src_col + 1) * CW]
    moved = shift(src, dx, dy)
    before = int((a[row * CH:(row + 1) * CH, col * CW:(col + 1) * CW, 3] >= ALPHA_BIN).sum())
    out = a.copy()
    out[row * CH:(row + 1) * CH, col * CW:(col + 1) * CW] = moved
    out[:, :, 3] = np.where(out[:, :, 3] >= ALPHA_BIN, 255, 0)
    out[out[:, :, 3] == 0] = 0
    after = int((moved[:, :, 3] >= ALPHA_BIN).sum())
    print(f"■ {name}  {ROWS[row]} col{col} ← col{src_col}  이동({dx:+d},{dy:+d})"
          f"  픽셀 {before} → {after}")

    if apply:
        Image.fromarray(out.astype(np.uint8), "RGBA").save(p)
        print(f"   -> 적용됨 {p}")
    else:
        q = os.path.join(HERE, "_diag", f"borrow_{name}.png")
        Image.fromarray(out.astype(np.uint8), "RGBA").save(q)
        print(f"   -> 미리보기 {q}")


if __name__ == "__main__":
    main()
