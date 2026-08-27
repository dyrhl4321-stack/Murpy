# -*- coding: utf-8 -*-
"""좌향(행2) 프레임을 좌우반전해 우향(행3)으로 채운다.

대표 8-27: "우측은 그냥 좌우반전으로 해주면 안 되냐"
→ **된다.** base 몸통이 좌우 91~94% 대칭이고, 아이템끼리는 서로 독립된 레이어라
  다른 옷과 충돌하지 않는다. 단색 옷(브라탑 등)처럼 좌우 비대칭 무늬가 없을 때만 쓴다.
  ※지퍼·로고·한쪽 어깨끈처럼 방향이 있는 옷에는 쓰지 말 것 — 뒤집힌 게 눈에 띈다.

★그냥 뒤집기만 하면 **2~4px 어긋난다.** base 자체가 완전 대칭이 아니라서다:
  여캐 몸통 중심이 좌향 59.5 / 우향 76.5 인데, 좌향을 뒤집으면 80.5 가 된다.
  → base 의 좌·우향 중심 차이만큼 되밀어 준다.
"""
import argparse, os
import numpy as np
from PIL import Image

CW, CH, COLS = 141, 224, 3


def center_x(a, row, col, y0, y1):
    m = a[row * CH + y0: row * CH + y1, col * CW:(col + 1) * CW, 3] > 128
    xs = np.where(m.any(0))[0]
    return None if not len(xs) else (xs.min() + xs.max()) / 2.0


def run(item_path, base_path, y0=100, y1=150, out_path=None, log=print):
    it = np.array(Image.open(item_path).convert("RGBA"))
    ba = np.array(Image.open(base_path).convert("RGBA"))
    out = it.copy()
    for c in range(COLS):
        lc = center_x(ba, 2, c, y0, y1)
        rc = center_x(ba, 3, c, y0, y1)
        if lc is None or rc is None:
            log("  col%d base 를 못 재서 건너뜀" % c); continue
        # ★셀 기준으로만 뒤집으면 안 된다. **옷이 base 의 어디에 붙어 있었는지**를 지켜야 한다.
        #   좌향에서 (옷 중심 - base 중심) 만큼 떨어져 있었으면,
        #   우향에서는 그 반대편으로 같은 거리에 놓여야 한다.
        ic = center_x(it, 2, c, y0, y1)
        if ic is None:
            log("  col%d 옷을 못 재서 건너뜀" % c); continue
        want = rc - (ic - lc)                          # 우향에서 옷이 있어야 할 중심
        shift = int(round(want - ((CW - 1) - ic)))     # 뒤집은 옷을 그 자리로 옮길 거리
        cell = it[2 * CH:3 * CH, c * CW:(c + 1) * CW][:, ::-1]
        moved = np.zeros_like(cell)
        if shift >= 0:
            if shift < CW: moved[:, shift:] = cell[:, :CW - shift]
        else:
            s = -shift
            if s < CW: moved[:, :CW - s] = cell[:, s:]
        out[3 * CH:4 * CH, c * CW:(c + 1) * CW] = moved
        log("  col%d 반전 + x %+d px (base 중심 좌 %.1f / 우 %.1f)" % (c, shift, lc, rc))
    out[..., 3] = np.where(out[..., 3] >= 128, 255, 0)   # 알파 128 이진화 (하드룰)
    Image.fromarray(out, "RGBA").save(out_path or item_path)
    log("-> %s" % (out_path or item_path))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--item", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--y", nargs=2, type=int, default=[100, 150],
                    help="정렬 기준으로 삼을 세로 구간(옷이 놓이는 곳)")
    ap.add_argument("--out")
    a = ap.parse_args()
    run(a.item, a.base, a.y[0], a.y[1], a.out)
