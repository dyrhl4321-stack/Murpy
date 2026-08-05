# -*- coding: utf-8 -*-
"""여캐 기본흰티 '우측 걸음2' 프레임의 제미나이 워터마크(✦)를 지운다.

remove_gemini_watermark.py 는 시트 1408x3008 을 전제로 좌표가 하드코딩돼 있는데
이 시트는 1408x2986 이라 그대로 못 쓴다. 그래서 **위치를 실측으로 찾는다.**

방식은 같다 — 없는 픽셀을 지어내지 않고 **같은 행의 다른 프레임에서 이식**한다.
✦ 는 반투명 흰색이라 흰티 추출 필터(무채색+밝음)를 그대로 통과해 옷으로 잡힌다.
(반바지는 어두운 것만 골라서 안 걸렸다 — 그래서 반바지에선 이 문제가 없었다)

    python char/fix_tee_watermark.py            # 찾기만
    python char/fix_tee_watermark.py --apply    # 원본 정리본 저장
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = Path(r"C:\Users\allys\Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차\상의\여캐\여자 기본흰티.png")
OUT = SRC.with_name("여자 기본흰티_워터마크제거.png")
TARGET = (3, 2)        # 우측 행, 걸음2
DONORS = [(3, 0), (3, 1)]
SEARCH = 14            # 도너 정합 탐색 반경(px)
PAD = 10               # 이식 영역 여유
# ✦ 가 있는 몸통 구간 (셀 크기 대비 비율). 눈으로 확인한 위치를 근거로 잡았다.
ROI_Y0, ROI_Y1 = 0.55, 0.82
ROI_X0, ROI_X1 = 0.30, 0.72


def cells(a):
    h, w = a.shape[0] // 4, a.shape[1] // 3
    return h, w


def find_wm(a):
    """워터마크 후보 = 도너 프레임과 **크게 다른** 덩어리.

    ★'밝은 무채색'으로 찾으면 못 잡는다. ✦ 는 반투명이라 살색 위에서는 '밝은 살색'이
      되어 무채색 조건에 안 걸린다(실제로 그렇게 놓쳤다). 도너 차분이 맞다.
    ★그리고 ✦ 는 **부드러운 그라데이션**이라 하드 픽셀아트 사이에서 튄다 —
      경계가 뭉개진 것도 같이 본다.
    """
    h, w = cells(a)
    tr, tc = TARGET
    t = a[tr * h:(tr + 1) * h, tc * w:(tc + 1) * w, :3].astype(int)
    best = None
    for dr, dc in DONORS:
        d = a[dr * h:(dr + 1) * h, dc * w:(dc + 1) * w, :3].astype(int)
        for dy in range(-SEARCH, SEARCH + 1, 2):
            for dx in range(-SEARCH, SEARCH + 1, 2):
                s = np.roll(np.roll(d, dy, axis=0), dx, axis=1)
                diff = np.abs(s - t).sum(axis=2)
                score = float(np.median(diff))
                if best is None or score < best[0]:
                    best = (score, diff, dr, dc, dy, dx)
    med, diff, dr, dc, dy, dx = best
    print(f"  기준 도너 r{dr}c{dc} offset({dx:+d},{dy:+d})  중앙값차 {med:.0f}")
    # ★다리는 프레임마다 위치가 달라 통째로 '차이'로 잡힌다(실제로 270×172 가 잡혔다).
    #   ✦ 는 상반신에 있으므로 몸통 띠로 좁힌다. 아래 상수는 셀 높이 비율.
    roi = np.zeros(diff.shape, bool)
    roi[int(h * ROI_Y0):int(h * ROI_Y1), int(w * ROI_X0):int(w * ROI_X1)] = True
    diff = np.where(roi, diff, 0)
    m = ndimage.binary_opening(diff > 90, np.ones((3, 3), bool))
    lab, n = ndimage.label(m, np.ones((3, 3), bool))
    if not n:
        return None
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    i = int(np.argmax(sizes)) + 1
    ys, xs = np.nonzero(lab == i)
    return int(sizes[i - 1]), xs.min(), xs.max(), ys.min(), ys.max()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    # ★자동 검출은 ✦ 의 **진한 부분만** 잡는다(반투명이라 옅은 데는 차이가 작다).
    #   눈으로 잰 상자를 직접 넘길 수 있게 둔다 — 이 경우가 더 정확하다.
    ap.add_argument("--box", help="셀 안 좌표 x0,x1,y0,y1")
    args = ap.parse_args()

    a = np.asarray(Image.open(SRC).convert("RGBA")).astype(np.uint8)
    h, w = cells(a)
    print(f"시트 {a.shape[1]}×{a.shape[0]}  셀 {w}×{h}")

    if args.box:
        x0, x1, y0, y1 = (int(v) for v in args.box.split(","))
        npx = (x1 - x0 + 1) * (y1 - y0 + 1)
        print("  상자 직접 지정")
    else:
        got = find_wm(a)
        if not got:
            print("워터마크 후보를 못 찾았다")
            return 1
        npx, x0, x1, y0, y1 = got
    print(f"워터마크 후보  {npx}px  셀내 x{x0}~{x1} y{y0}~{y1}  "
          f"(크기 {x1-x0+1}×{y1-y0+1})")

    if not args.apply:
        print("\n--apply 를 붙이면 도너 이식 후 저장한다")
        return 0

    tr, tc = TARGET
    ox, oy = tc * w, tr * h
    bx0, bx1 = max(0, x0 - PAD), min(w - 1, x1 + PAD)
    by0, by1 = max(0, y0 - PAD), min(h - 1, y1 + PAD)

    target = a[oy + by0:oy + by1 + 1, ox + bx0:ox + bx1 + 1, :3].astype(int)
    # 이식할 자리(워터마크)와 정합 품질을 잴 테두리
    inner = np.zeros(target.shape[:2], bool)
    inner[y0 - by0:y1 - by0 + 1, x0 - bx0:x1 - bx0 + 1] = True
    ring = ~inner

    best = None
    for dr, dc in DONORS:
        dox, doy = dc * w, dr * h
        for dy in range(-SEARCH, SEARCH + 1):
            for dx in range(-SEARCH, SEARCH + 1):
                sy, sx = doy + by0 + dy, dox + bx0 + dx
                if sy < 0 or sx < 0 or sy + target.shape[0] > a.shape[0] or sx + target.shape[1] > a.shape[1]:
                    continue
                cand = a[sy:sy + target.shape[0], sx:sx + target.shape[1], :3].astype(int)
                mae = float(np.abs(cand[ring] - target[ring]).mean())
                if best is None or mae < best[0]:
                    best = (mae, dr, dc, dy, dx, sy, sx)
    mae, dr, dc, dy, dx, sy, sx = best
    print(f"도너 r{dr}c{dc}  offset({dx:+d},{dy:+d})  테두리 MAE {mae:.1f}")
    if mae > 22:
        print("!! 테두리가 안 맞는다 — 믿을 만한 도너가 없다. 중단")
        return 1

    out = a.copy()
    patch = a[sy:sy + target.shape[0], sx:sx + target.shape[1]]
    dst = out[oy + by0:oy + by1 + 1, ox + bx0:ox + bx1 + 1]
    dst[inner] = patch[inner]
    Image.fromarray(out, "RGBA").save(OUT)
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
