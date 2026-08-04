# -*- coding: utf-8 -*-
"""기본 반바지(남/여) 레이어를 원본 시트에서 차분 추출한다.

■ 원본의 특징 (2026-08-04 대표 제공)
- 1408×2986, **마젠타 배경**(알파 없음) — 리사이즈 **전에** flood fill 로 지운다.
  색 임계만 쓰면 경계에 보라 링이 남는다(모자 조합 때 겪음).
- base 와 정합 양호(앱 셀 환산 2px 이내). 그래도 Norm 이 셀별 bbox 로 다시 맞춘다.
- ★AI 가 **탱크톱을 같이 그렸다.** 하의만 요청했는데 base 가 상반신 알몸이라 알아서 입혔다.
  그래서 차분 결과에서 허리 위를 버려야 한다 — 자르는 높이는 --diag 로 실측해서 정한다.

    python char/build_basic_shorts.py --diag     # 행별 픽셀 분포만 출력(자를 높이 찾기)
    python char/build_basic_shorts.py            # 추출 + 저장
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_hair_layer import CW, CH, ALPHA_BIN, Norm, load, pad_img, binarize  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "items")
D = r"C:\Users\allys\Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차\바지"

DIFF_T = 40
STRAY_MAX = 40
HOLE_MAX = 400
DARK_MAX = 100
MIN_PART = 120     # 이보다 작은 덩어리는 반바지 조각으로 안 본다(얼룩 제거)     # 이 밝기 미만만 반바지로 본다(탱크톱 분리). --diag 로 검증.

CONFIG = [
    dict(out="bottom_basic_shorts", name="기본 반바지(남)", base="walk.png",
         src=os.path.join(D, "남자 기본 반바지.png")),
    dict(out="bottom_f_basic_shorts", name="기본 반바지(여)", base="walk_female.png",
         src=os.path.join(D, "여캐", "여자기본반바지.png")),
]


def strip_magenta(path: str) -> np.ndarray:
    """마젠타 배경 제거. ★가장자리에서 연결된 것만 지운다 — 색 임계만으로 지우면
    캐릭터와 섞인 경계 픽셀까지 먹어서 보라 링/구멍이 남는다."""
    a = np.asarray(Image.open(path).convert("RGBA")).astype(int)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    mag = (r - g > 40) & (b - g > 40)
    lab, _ = ndimage.label(mag)
    edge = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
    edge.discard(0)
    bg = np.isin(lab, list(edge))
    out = a.copy()
    out[bg] = [0, 0, 0, 0]
    out[~bg, 3] = 255
    return out


def is_skin(arr):
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    return (r > 140) & (r - b > 30) & (g >= b)


def garment_mask(src, bse):
    sa = src[:, :, 3] >= ALPHA_BIN
    ba = bse[:, :, 3] >= ALPHA_BIN
    rgbdiff = np.abs(src[:, :, :3] - bse[:, :, :3]).sum(axis=2) > DIFF_T
    m = sa & (rgbdiff | ~ba)
    m &= ~is_skin(src)
    return m


def keep_main(m):
    """반바지 본체만 남긴다. 가장 큰 덩어리 + 그와 세로로 겹치는 덩어리(양쪽 바지단이
    다리 사이에서 끊겨 둘로 나뉘는 프레임이 있다)만 인정한다."""
    lab, n = ndimage.label(m, np.ones((3, 3), bool))
    if n <= 1:
        return m
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    main = int(np.argmax(sizes)) + 1
    ys = np.nonzero(m & (lab == main))[0]
    lo, hi = ys.min(), ys.max()
    out = np.zeros_like(m)
    for i in range(1, n + 1):
        if sizes[i - 1] < MIN_PART:
            continue
        yy = np.nonzero(lab == i)[0]
        # 본체와 세로 구간이 겹치면 같은 옷으로 본다(머리 쪽 얼룩은 안 겹쳐서 걸러진다)
        if yy.max() >= lo and yy.min() <= hi:
            out |= (lab == i)
    return out


def clean(m):
    lab, n = ndimage.label(m, np.ones((3, 3), bool))
    if n > 1:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        for i, s in enumerate(sizes, start=1):
            if s < STRAY_MAX:
                m[lab == i] = False
    holes = ndimage.binary_fill_holes(m) & ~m
    lab2, n2 = ndimage.label(holes, np.ones((3, 3), bool))
    for i in range(1, n2 + 1):
        h = lab2 == i
        if h.sum() <= HOLE_MAX:
            m |= h
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--diag", action="store_true")
    ap.add_argument("--only")
    a = ap.parse_args()

    for cfg in CONFIG:
        if a.only and cfg["out"] != a.only:
            continue
        if not os.path.exists(cfg["src"]):
            print(f"!! 원본 없음 {cfg['src']}")
            continue
        base_arr = load(os.path.join(HERE, cfg["base"]))
        nb = Norm(base_arr)
        bpad = pad_img(base_arr)

        src_arr = strip_magenta(cfg["src"])
        ns = Norm(src_arr)
        spad = pad_img(src_arr)

        print(f"\n■ {cfg['name']}  ({cfg['out']})")
        sheet = Image.new("RGBA", (CW * 3, CH * 4), (0, 0, 0, 0))
        for r in range(4):
            row = []
            for c in range(3):
                src = binarize(ns.cell(spad, r, c))
                bse = binarize(nb.cell(bpad, r, c))
                m = garment_mask(src, bse)
                if a.diag:
                    # 8px 구간마다 픽셀 수를 막대로 — 탱크톱 덩어리와 반바지 덩어리,
                    # 그리고 그 사이 골짜기가 눈에 보여야 CUT_Y 를 근거 있게 정할 수 있다
                    prof = m.sum(axis=1)
                    if c == 0:
                        bars = []
                        for y0 in range(0, CH, 8):
                            v = int(prof[y0:y0 + 8].sum())
                            bars.append(' .:-=+*#%@'[min(9, v // 60)])
                        print(f"   row{r} c0  총{int(m.sum()):5d}px  [{''.join(bars)}]")
                    row.append(f"{int(m.sum()):5d}")
                    continue
                # ★탱크톱을 **위치가 아니라 색으로** 버린다.
                #   둘이 허리에서 맞닿아 있어 세로 골짜기가 없다(--diag 로 확인).
                #   반바지는 검정, 탱크톱은 흰색(여)·베이지(남)라 밝기로 깨끗이 갈린다.
                lum = src[:, :, :3].mean(axis=2)
                m &= lum < DARK_MAX
                # ★캐릭터 **외곽선도 어둡다.** 원본과 base 의 외곽선이 몇 px 어긋난 자리가
                #   전부 '반바지'로 잡혀서 얼굴·머리에 검은 얼룩이 튀었다(남 4행에서 실제 발생).
                #   반바지는 허리 아래 한 덩어리다 → 큰 덩어리만 남기고 나머지는 버린다.
                # ★가시 제거. 원본과 base 의 **외곽선이 1px 어긋난 자리**가 전부 옷으로 잡혀서
                #   다리·팔을 따라 실선이 사방으로 뻗었다(추출 레이어를 눈으로 보고 발견).
                #   가시는 폭 1~2px, 반바지 본체는 40px 이상 → 침식 후 팽창하면 가시만 죽는다.
                m = ndimage.binary_opening(m, np.ones((3, 3), bool))
                m = keep_main(m)
                m = clean(m)
                cell = np.zeros((CH, CW, 4), np.uint8)
                cell[m] = src[m].astype(np.uint8)
                cell[m, 3] = 255
                sheet.paste(Image.fromarray(cell, "RGBA"), (c * CW, r * CH))
                row.append(f"{int(m.sum()):5d}px")
            print(f"   row{r}: " + "  ".join(row))
        if a.diag:
            continue
        dst = os.path.join(ITEMS, cfg["out"] + ".png")
        sheet.save(dst)
        print(f"   -> {dst}")
    if a.diag:
        print("\n※ 위 범위에서 탱크톱과 반바지 사이가 끊기는 y 를 CUT_Y 로 잡는다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
