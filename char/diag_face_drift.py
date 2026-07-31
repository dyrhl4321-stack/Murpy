# -*- coding: utf-8 -*-
"""base 의 걸음 프레임에서 **두상과 얼굴이 따로 움직이는지** 잰다.

대표(7-31): "오른쪽으로 이동할 때 이마나 입이 계속 튀어나온다. 프레임마다 왔다갔다."

헤어는 방향당 1프레임을 3열에 복제하고 **두상 기준점**(최상단 y, 상단 18px 밴드 중심 x)으로만
맞춘다(replicate_cols). 그런데 base 의 얼굴(눈·코·입)이 두상과 **다른 양만큼** 움직이면,
헤어와 얼굴의 상대 위치가 프레임마다 달라진다 → 이마가 열렸다 닫혔다 한다.

두 기준점의 열별 이동량을 비교하면 원인인지 아닌지 바로 나온다.

    python char/diag_face_drift.py            # 남녀 base 둘 다
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_hair_layer import skull_ref   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CW, CH = 141, 224
ALPHA_BIN = 128
ROWS = ["정면", "후면", "좌", "우"]


def face_ref(bc, bm, top):
    """얼굴 기준점 = 눈·눈썹·입 같은 **어두운 이목구비 덩어리**의 중심.

    외곽선을 빼려고 실루엣 경계에서 6px 이상 안쪽만 본다. 머리 구간(top~top+100)만.
    """
    dark = bm & (bc[:, :, :3].mean(axis=2) < 70)
    inner = dark & (ndimage.distance_transform_edt(bm) > 6)
    band = np.zeros_like(bm)
    band[top + 35:top + 100] = True
    m = inner & band
    if not m.any():
        return None
    ys, xs = np.where(m)
    return float(xs.mean()), float(ys.mean()), int(m.sum())


def main():
    for base_name in ["walk.png", "walk_female.png"]:
        p = os.path.join(HERE, base_name)
        if not os.path.exists(p):
            continue
        base = np.asarray(Image.open(p).convert("RGBA")).astype(int)
        print(f"\n■ {base_name}")
        print("   방향  열 |  두상(x,y)      얼굴(x,y)     | col0 대비 이동  두상 → 얼굴  차이")
        for r in range(4):
            ref = {}
            for c in range(3):
                bc = base[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
                bm = bc[:, :, 3] >= ALPHA_BIN
                top, sx = skull_ref(bm)
                f = face_ref(bc, bm, top)
                ref[c] = (sx, float(top), f)
            for c in range(3):
                sx, sy, f = ref[c]
                if f is None:
                    print(f"   {ROWS[r]:2s}  {c}  | 얼굴 검출 실패")
                    continue
                fx, fy, n = f
                if c == 0:
                    print(f"   {ROWS[r]:2s}  {c}  | ({sx:6.1f},{sy:5.1f})  ({fx:6.1f},{fy:5.1f}) | 기준")
                else:
                    s0x, s0y, f0 = ref[0]
                    dsx, dsy = sx - s0x, sy - s0y
                    dfx, dfy = fx - f0[0], fy - f0[1]
                    gap = ((dfx - dsx) ** 2 + (dfy - dsy) ** 2) ** 0.5
                    flag = "  ★어긋남" if gap >= 1.0 else ""
                    print(f"   {ROWS[r]:2s}  {c}  | ({sx:6.1f},{sy:5.1f})  ({fx:6.1f},{fy:5.1f}) | "
                          f"두상({dsx:+.1f},{dsy:+.1f}) 얼굴({dfx:+.1f},{dfy:+.1f})  차이 {gap:.1f}px{flag}")


if __name__ == "__main__":
    main()
