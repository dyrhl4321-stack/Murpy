# -*- coding: utf-8 -*-
"""한 방향의 정지 프레임(col0) 헤어를 걸음 프레임(col1·col2)에 복제한다.

헤어는 방향당 1프레임 복제가 원칙이다(빌더도 그렇게 만든다). 대표가 리터치 도구로
고치면 3열에 반영되긴 하지만 열별로 몇 px 어긋나고, 그러면 걸을 때 머리가 깜빡인다.

**모양은 col0 그대로 두고 위치만** 열별 base 두상에 맞춰 평행이동한다.
base 두상은 걸음 프레임마다 움직이므로(열별 dx 최대 3.5px, dy 2px) 그냥 복사하면
어긋난 프레임에서 두상이 삐져나온다.

    python char/replicate_cols.py hair_m_semileaf.png 0            # 미리보기
    python char/replicate_cols.py hair_m_semileaf.png 0 --apply
    python char/replicate_cols.py hair_f_long.png all --apply --base walk_female.png
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_hair_layer import skull_ref, shift   # noqa: E402
from diag_face_drift import face_ref   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CW, CH = 141, 224
ALPHA_BIN = 128
ROWS = ["정면", "후면", "좌", "우"]
REF = "skull"     # 정렬 기준: skull(두상) | face(이목구비) | mid(중간). --ref 로 바꾼다


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    name, rowarg = sys.argv[1], sys.argv[2]
    apply = "--apply" in sys.argv
    base_name = "walk.png"
    if "--base" in sys.argv:
        base_name = sys.argv[sys.argv.index("--base") + 1]
    global REF
    if "--ref" in sys.argv:
        REF = sys.argv[sys.argv.index("--ref") + 1]
    rows = range(4) if rowarg == "all" else [int(rowarg)]

    base = np.asarray(Image.open(os.path.join(HERE, base_name)).convert("RGBA")).astype(int)
    p = os.path.join(HERE, "items", name)
    a = np.asarray(Image.open(p).convert("RGBA")).astype(int)
    out = a.copy()

    print(f"■ {name}  (기준 {base_name})")
    for r in rows:
        src = a[r * CH:(r + 1) * CH, 0:CW]
        bc0 = base[r * CH:(r + 1) * CH, 0:CW]
        bm0 = bc0[:, :, 3] >= ALPHA_BIN
        t0, x0 = skull_ref(bm0)
        f0 = face_ref(bc0, bm0, t0)
        for c in range(1, 3):
            bcc = base[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
            bmc = bcc[:, :, 3] >= ALPHA_BIN
            tc, xc = skull_ref(bmc)
            # ★base 는 걸음 프레임마다 두상과 얼굴을 **다른 양만큼** 움직인다(실측 최대 3.4px).
            #   두상에만 맞추면 헤어와 얼굴이 틀어져 이마·입이 프레임마다 열렸다 닫혔다 한다
            #   (대표: "오른쪽으로 갈 때 이마나 입이 계속 튀어나온다").
            #   기준을 고를 수 있게 한다 — mid 는 둘의 중간(오차를 절반씩 나눔).
            fc = face_ref(bcc, bmc, tc)
            sdx, sdy = xc - x0, float(tc - t0)
            if f0 and fc:
                fdx, fdy = fc[0] - f0[0], fc[1] - f0[1]
            else:
                fdx, fdy = sdx, sdy
            if REF == "face":
                ddx, ddy = fdx, fdy
            elif REF == "mid":
                ddx, ddy = (sdx + fdx) / 2.0, (sdy + fdy) / 2.0
            else:
                ddx, ddy = sdx, sdy
            dx, dy = int(round(ddx)), int(round(ddy))
            moved = shift(src, dx, dy)
            before = int((out[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW, 3] >= ALPHA_BIN).sum())
            out[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW] = moved
            after = int((moved[:, :, 3] >= ALPHA_BIN).sum())
            print(f"  {ROWS[r]:2s} col{c}  이동 dx{dx:+d} dy{dy:+d}   픽셀 {before} → {after}")

    # 알파 하드룰
    out[:, :, 3] = np.where(out[:, :, 3] >= ALPHA_BIN, 255, 0)
    out[out[:, :, 3] == 0] = 0

    if apply:
        Image.fromarray(out.astype(np.uint8), "RGBA").save(p)
        print(f"-> 적용됨 {p}")
    else:
        q = os.path.join(HERE, "_diag", f"replicated_{name}")
        Image.fromarray(out.astype(np.uint8), "RGBA").save(q)
        print(f"-> 미리보기 {q}  (적용하려면 --apply)")


if __name__ == "__main__":
    main()
