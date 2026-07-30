# -*- coding: utf-8 -*-
"""잘 나온 방향을 좌우반전해 반대 방향을 만든다.

★왜 필요한가 (2026-07-31, 대표 지시)
AI가 4방향을 그리면 한쪽만 잘 나오는 일이 흔하다(아이비리그컷 = 우향은 깨끗, 좌향은 지저분).
머리는 좌우대칭이므로 **잘 나온 쪽을 뒤집어 쓰는 게 다시 뽑는 것보다 확실하다.**

★그냥 뒤집으면 안 된다 — base(walk.png)의 좌향/우향은 서로 정확한 거울상이 아니다.
  걸음 자세가 다르고 머리 위치도 1~3px 어긋난다. 그래서 **base의 머리 위치에 맞춰 정렬**한다.
  (열마다 따로 잰다. 걸음 프레임마다 머리가 움직이기 때문.)

    python char/mirror_direction.py hair_ivyleague 3 2      # 우(3) -> 좌(2)
    python char/mirror_direction.py hair_ivyleague 2 3      # 좌(2) -> 우(3)
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
CW, CH = 141, 224
ROWS = ["정면", "후면", "좌", "우"]
HEAD_H = 78


def largest(m):
    lab, n = ndimage.label(m, np.ones((3, 3), bool))
    if n <= 1:
        return m
    s = ndimage.sum(m, lab, range(1, n + 1))
    return lab == (int(np.argmax(s)) + 1)


def head_center(bc):
    """base 셀에서 머리 구간의 가로 중심과 최상단 y. 정렬 기준."""
    bm = largest(bc[:, :, 3] >= 128)
    ys = np.where(bm.any(axis=1))[0]
    top = int(ys.min())
    xs = np.where(bm[top:top + HEAD_H].any(axis=0))[0]
    return (int(xs.min()) + int(xs.max())) / 2.0, top


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return
    item, src_r, dst_r = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    ip = os.path.join(HERE, "items", item + ".png")
    sheet = Image.open(ip).convert("RGBA")
    a = np.asarray(sheet).astype(int).copy()

    # 여캐 아이템이면 여캐 base
    walk = "walk_female.png" if "_f_" in item else "walk.png"
    base = np.asarray(Image.open(os.path.join(HERE, walk)).convert("RGBA")).astype(int)

    print("■ %s : %s(row%d) -> %s(row%d)" % (item, ROWS[src_r], src_r, ROWS[dst_r], dst_r))
    for c in range(3):
        sb = base[src_r * CH:(src_r + 1) * CH, c * CW:(c + 1) * CW]
        db = base[dst_r * CH:(dst_r + 1) * CH, c * CW:(c + 1) * CW]
        scx, stop = head_center(sb)
        dcx, dtop = head_center(db)

        cell = a[src_r * CH:(src_r + 1) * CH, c * CW:(c + 1) * CW]
        flip = cell[:, ::-1, :].copy()          # 좌우 반전
        # 반전하면 중심이 (CW-1-scx) 로 간다. 목표 중심까지 평행이동.
        dx = int(round(dcx - (CW - 1 - scx)))
        dy = int(round(dtop - stop))
        out = np.zeros_like(flip)
        ys0, ys1 = max(0, dy), min(CH, CH + dy)
        xs0, xs1 = max(0, dx), min(CW, CW + dx)
        out[ys0:ys1, xs0:xs1] = flip[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]

        a[dst_r * CH:(dst_r + 1) * CH, c * CW:(c + 1) * CW] = out
        print("   col%d  이동 dx=%+d dy=%+d  (머리중심 %.1f -> %.1f)" % (c, dx, dy, scx, dcx))

    # 알파 이진화 (하드룰)
    keep = a[:, :, 3] >= 128
    a[:, :, 3] = np.where(keep, 255, 0)
    a[~keep] = 0
    Image.fromarray(a.astype(np.uint8), "RGBA").save(ip)
    print("   -> items/%s.png 저장" % item)

    # 썸네일 = 정면 전신
    t = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    t.alpha_composite(Image.fromarray(base[0:CH, 0:CW].astype(np.uint8), "RGBA"))
    t.alpha_composite(Image.open(ip).crop((0, 0, CW, CH)))
    ta = np.asarray(t)[:, :, 3]
    ys, xs = np.where(ta > 0)
    t.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)).save(
        os.path.join(HERE, "items", item + "_thumb.png"))
    print("   -> 썸네일 갱신")


if __name__ == "__main__":
    main()
