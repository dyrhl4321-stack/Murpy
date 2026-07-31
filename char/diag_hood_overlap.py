# -*- coding: utf-8 -*-
"""헤어가 상의(후드)를 덮는 양을 좌우로 나눠 잰다.

대표: "아이비리그컷 + 후드를 같이 쓰면 후면에서 후드 우측이 잘려 보인다."
후드만 렌더하면 좌우 대칭이므로, 헤어가 한쪽만 더 덮고 있다는 뜻이다.

    python char/diag_hood_overlap.py hair_ivyleague top_redhood human 1
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
CW, CH = 141, 224
ALPHA_BIN = 128
ROWS = ["정면", "후면", "좌", "우"]
BASEW = {"human": "walk.png", "human_f": "walk_female.png"}


def main():
    hair_n = sys.argv[1] if len(sys.argv) > 1 else "hair_ivyleague"
    top_n = sys.argv[2] if len(sys.argv) > 2 else "top_redhood"
    body = sys.argv[3] if len(sys.argv) > 3 else "human"
    rows = [int(sys.argv[4])] if len(sys.argv) > 4 else [0, 1, 2, 3]

    base = np.asarray(Image.open(os.path.join(HERE, BASEW[body])).convert("RGBA")).astype(int)
    hair = np.asarray(Image.open(os.path.join(HERE, "items", hair_n + ".png"))
                      .convert("RGBA")).astype(int)
    top = np.asarray(Image.open(os.path.join(HERE, "items", top_n + ".png"))
                     .convert("RGBA")).astype(int)

    print(f"■ {hair_n} 가 {top_n} 를 덮는 양")
    for r in rows:
        bm = base[r * CH:(r + 1) * CH, 0:CW, 3] >= ALPHA_BIN
        xs = np.where(bm.any(axis=0))[0]
        mid = (int(xs.min()) + int(xs.max())) // 2
        for c in range(3):
            h = hair[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW, 3] >= ALPHA_BIN
            t = top[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW, 3] >= ALPHA_BIN
            hide = h & t                      # 헤어가 위라서 가려지는 상의 픽셀
            left = int(hide[:, :mid].sum())
            right = int(hide[:, mid:].sum())
            hl = int(h[:, :mid].sum())
            hr = int(h[:, mid:].sum())
            flag = "  ★좌우 차이 큼" if abs(left - right) > 20 else ""
            print(f"   {ROWS[r]:2s} col{c}  상의 가림 좌{left:4d} / 우{right:4d}"
                  f"   (헤어 자체 좌{hl:5d} / 우{hr:5d}, 차 {hl-hr:+d}){flag}")


if __name__ == "__main__":
    main()
