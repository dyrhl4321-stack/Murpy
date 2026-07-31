# -*- coding: utf-8 -*-
"""옛 버전과 현재 버전을 **합성한 화면끼리** 비교한다.

알파 기준(헤어 픽셀 유무)으로 재면 속는다 — base 와 같은 색을 덮고 있던 픽셀은
지워도 화면이 안 변하기 때문이다. 대표가 보는 것은 합성 결과다.

    python char/diag_visible_diff.py 671c2c5
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_regions import skinmask   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CW, CH = 141, 224
ALPHA_BIN = 128


def cell(s, r, c):
    return s[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]


def over(dst, src):
    out = dst.copy()
    m = src[:, :, 3] >= ALPHA_BIN
    out[m] = src[m]
    out[m, 3] = 255
    return out


def main():
    old_sha = sys.argv[1] if len(sys.argv) > 1 else "671c2c5"
    base = np.asarray(Image.open(os.path.join(HERE, "walk.png")).convert("RGBA")).astype(int)
    old = np.asarray(Image.open(os.path.join(HERE, "_diag", "hist", f"{old_sha}.png"))
                     .convert("RGBA")).astype(int)
    cur = np.asarray(Image.open(os.path.join(HERE, "items", "hair_m_semileaf.png"))
                     .convert("RGBA")).astype(int)

    bc = cell(base, 0, 0)
    co = over(bc, cell(old, 0, 0))
    cc = over(bc, cell(cur, 0, 0))
    diff = (np.abs(co[:, :, :3] - cc[:, :, :3]).sum(axis=2) > 24)

    bm = bc[:, :, 3] >= ALPHA_BIN
    top = int(np.where(bm.any(axis=1))[0].min())
    print(f"화면이 실제로 달라진 픽셀 {int(diff.sum())}px")

    # 어느 방향으로 바뀌었나 — 옛것이 머리카락색이고 지금은 살색인 곳 = '머리가 사라진' 자리
    sk_old, sk_cur = skinmask(co), skinmask(cc)
    hair_lost = diff & ~sk_old & sk_cur      # 갈색 → 살색  (M자 탈모)
    hair_gain = diff & sk_old & ~sk_cur      # 살색 → 갈색
    other = diff & ~hair_lost & ~hair_gain
    print(f"  머리카락 → 살색 (탈모처럼 보이는 자리) {int(hair_lost.sum()):5d}px")
    print(f"  살색 → 머리카락                     {int(hair_gain.sum()):5d}px")
    print(f"  그 외(머리색끼리 미세 변화)            {int(other.sum()):5d}px")

    if hair_lost.any():
        ys, xs = np.where(hair_lost)
        print(f"  탈모 영역  y{ys.min()}~{ys.max()} (rel {ys.min()-top}~{ys.max()-top})"
              f"  x{xs.min()}~{xs.max()}")
        print(f"  그 자리 옛 색 평균 RGB {co[hair_lost][:, :3].mean(axis=0).round(0)}")

    # 시각화
    vis = cc.copy()
    vis[hair_lost] = [255, 0, 255, 255]
    vis[hair_gain] = [0, 255, 255, 255]
    vis[other] = [255, 255, 0, 255]
    side = np.concatenate([co[:110], cc[:110], vis[:110]], axis=1)
    p = os.path.join(HERE, "_diag", "visible_diff.png")
    im = Image.fromarray(side.astype(np.uint8), "RGBA").convert("RGB")
    im.resize((im.width * 5, im.height * 5), Image.NEAREST).save(p)
    print(f"-> {p}  (옛것 | 현재 | 차이표시: 마젠타=머리가 살색으로 바뀐 곳)")


if __name__ == "__main__":
    main()
