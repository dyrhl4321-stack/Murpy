# -*- coding: utf-8 -*-
"""세미리프컷 정면 '뒷머리가 안 보인다'(대표) 원인 규명.

시트에는 base 실루엣 바깥 헤어가 704px 있다고 측정됐다. 그런데 앱에서 안 보인다.
가능성 3가지를 분리해서 잰다:
  (A) 애초에 안 보일 위치다   → 바깥 픽셀이 얼굴 옆이 아니라 정수리/어깨쪽에 몰려 있나?
  (B) 너무 얇아서 안 보인다  → 행마다 좌/우로 몇 px 나와 있나? 1~2px면 눈에 안 띈다
  (C) 렌더/캐시 문제         → 위 둘이 아니면 앱 쪽

    python char/diag_semileaf_front.py
"""
import os
import sys

import numpy as np
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
CW, CH = 141, 224
ALPHA_BIN = 128
ROWS = ["정면", "후면", "좌", "우"]

TARGETS = ["hair_m_semileaf.png", "hair_m_basic.png"]


def cell(sheet, r, c):
    return sheet[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]


def main():
    base = np.asarray(Image.open(os.path.join(HERE, "walk.png")).convert("RGBA")).astype(int)
    print(f"base walk.png {base.shape[1]}x{base.shape[0]}")

    for name in TARGETS:
        p = os.path.join(HERE, "items", name)
        if not os.path.exists(p):
            print(f"!! 없음 {name}")
            continue
        hs = np.asarray(Image.open(p).convert("RGBA")).astype(int)
        print(f"\n===== {name}  {hs.shape[1]}x{hs.shape[0]} =====")
        if hs.shape[:2] != base.shape[:2]:
            print(f"  !! 규격 불일치 (base {base.shape[1]}x{base.shape[0]})")

        for r in range(4):
            for c in [0]:
                bm = cell(base, r, c)[:, :, 3] >= ALPHA_BIN
                h = cell(hs, r, c)[:, :, 3] >= ALPHA_BIN
                out = h & ~bm                      # 헤어가 base 실루엣 밖으로 나온 곳
                ys = np.where(bm.any(axis=1))[0]
                top = int(ys.min()) if len(ys) else 0
                print(f"  {ROWS[r]:2s} c{c}  헤어 {int(h.sum()):5d}  실루엣밖 {int(out.sum()):5d}")
                if not out.any():
                    continue

                # (A) 어디에 몰려 있나 — 머리 최상단 기준 상대 y 구간별
                oy = np.where(out.any(axis=1))[0]
                bands = [(0, 20, "정수리 위"), (20, 50, "머리 윗쪽"), (50, 80, "얼굴 옆(뒷머리 보일 자리)"),
                         (80, 120, "턱~목"), (120, 999, "어깨 아래")]
                for lo, hi, lbl in bands:
                    m = out[top + lo:top + hi] if top + lo < CH else out[:0]
                    n = int(m.sum())
                    if n:
                        print(f"       rel y{lo:3d}~{hi:<3d} {lbl:24s} {n:5d}px")

                # (B) 얼마나 얇은가 — 행별 좌/우 최대 돌출 폭
                widths_l, widths_r = [], []
                for y in range(CH):
                    if not out[y].any():
                        continue
                    bxs = np.where(bm[y])[0]
                    oxs = np.where(out[y])[0]
                    if len(bxs):
                        widths_l.append(int((oxs < bxs.min()).sum()))
                        widths_r.append(int((oxs > bxs.max()).sum()))
                    else:
                        widths_l.append(0)
                        widths_r.append(len(oxs))
                if widths_l:
                    print(f"       옆으로 나온 폭  좌 최대 {max(widths_l)}px / 우 최대 {max(widths_r)}px"
                          f"  (좌 평균 {np.mean(widths_l):.1f} / 우 평균 {np.mean(widths_r):.1f})")

                # 정면만 상세 — 얼굴 옆 구간에서 행별로 몇 px 나왔는지 전부 출력
                if r == 0:
                    print("       [정면 상세] rel y : 좌돌출 / 우돌출  (실루엣밖 픽셀 있는 행만)")
                    for y in range(CH):
                        if not out[y].any():
                            continue
                        bxs = np.where(bm[y])[0]
                        oxs = np.where(out[y])[0]
                        l = int((oxs < bxs.min()).sum()) if len(bxs) else 0
                        rr = int((oxs > bxs.max()).sum()) if len(bxs) else len(oxs)
                        print(f"         y{y - top:3d} : {l:2d} / {rr:2d}   x={oxs.min()}~{oxs.max()}")


if __name__ == "__main__":
    main()
