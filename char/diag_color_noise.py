# -*- coding: utf-8 -*-
"""AI 생성 픽셀아트가 '진짜 픽셀아트'와 얼마나 다른지 색으로 잰다.

대표(7-31): "AI로 만든 픽셀아트는 픽셀마다 색이 미묘하게 달라서, 에테르는 색부터
최적화(픽셀화)해준다더라."

우리 원본 시트가 실제로 그런지, 그리고 그게 우리 추출 실패와 어떻게 연결되는지 본다.
  - 고유 색이 몇 개인가 (진짜 도트는 보통 8~32색)
  - 그중 대부분을 덮는 '주요 색'은 몇 개인가
  - 머리색과 base 외곽선색이 얼마나 가까운가 ← 차분 추출이 0이 되는 원인

    python char/diag_color_noise.py
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_hair_layer import (BALD_F, NUKKI, FBASIC, MHAIR, CW, CH, ALPHA_BIN,   # noqa: E402
                              Norm, load, pad_img, binarize)

HERE = os.path.dirname(os.path.abspath(__file__))

CASES = [
    ("여자 긴생머리(원본)", os.path.join(NUKKI, "여자 검정생머리_clean-Photoroom.png")),
    ("여자 단발(원본)", os.path.join(NUKKI, "여자 검정단발머리_clean-Photoroom.png")),
    ("여자 기본머리(원본)", os.path.join(FBASIC, "여자기본머리_clean-Photoroom.png")),
    ("세미리프컷(원본)", os.path.join(MHAIR, "세미리프컷_clean-Photoroom.png")),
]


def stats(label, arr, alpha_min=ALPHA_BIN):
    m = arr[:, :, 3] >= alpha_min
    px = arr[m][:, :3]
    if not len(px):
        print(f"  {label}: 비어있음")
        return
    uniq, cnt = np.unique(px, axis=0, return_counts=True)
    order = np.argsort(-cnt)
    cum = np.cumsum(cnt[order]) / cnt.sum()
    n90 = int(np.searchsorted(cum, 0.90) + 1)
    n99 = int(np.searchsorted(cum, 0.99) + 1)
    print(f"  {label}: 픽셀 {len(px):,}  고유색 {len(uniq):,}개"
          f"  · 90%를 덮는 색 {n90}개 · 99% {n99}개")
    top = [f"({uniq[order[i]][0]},{uniq[order[i]][1]},{uniq[order[i]][2]})×{cnt[order[i]]}"
           for i in range(min(4, len(uniq)))]
    print(f"      최빈 4색: " + "  ".join(top))
    return uniq, cnt, order


def main():
    print("■ 원본 시트(AI 생성물) 색 분포 — 진짜 도트라면 고유색이 수십 개여야 한다\n")
    for label, p in CASES:
        if not os.path.exists(p):
            print(f"  {label}: 파일 없음")
            continue
        a = np.asarray(Image.open(p).convert("RGBA")).astype(int)
        stats(label, a)
        print()

    print("■ 우리가 이미 추출한 앱 레이어 (참고)\n")
    for n in ["hair_f_long.png", "hair_m_semileaf.png"]:
        a = np.asarray(Image.open(os.path.join(HERE, "items", n)).convert("RGBA")).astype(int)
        stats(n, a)
        print()

    print("■ ★차분 추출이 0이 되는 자리 — 머리색과 base 외곽선색의 거리\n")
    walk_f = np.asarray(Image.open(os.path.join(HERE, "walk_female.png"))
                        .convert("RGBA")).astype(int)
    norm = Norm(load(BALD_F))
    src = pad_img(load(os.path.join(NUKKI, "여자 검정생머리_clean-Photoroom.png")))
    worn = binarize(norm.cell(src, 0, 0))
    bc = walk_f[0:CH, 0:CW]

    bm = bc[:, :, 3] >= ALPHA_BIN
    dark_base = bm & (bc[:, :, 0] < 70) & (bc[:, :, 1] < 70) & (bc[:, :, 2] < 70)
    wm = worn[:, :, 3] >= ALPHA_BIN
    dark_hair = wm & (worn[:, :, 0] < 70) & (worn[:, :, 1] < 70) & (worn[:, :, 2] < 70)
    both = dark_base & dark_hair
    print(f"  base 어두운 픽셀 {int(dark_base.sum())} · 원본 어두운 픽셀 {int(dark_hair.sum())}"
          f" · 겹치는 자리 {int(both.sum())}")
    if both.any():
        d = np.abs(bc[both][:, :3] - worn[both][:, :3]).sum(axis=1)
        print(f"  겹치는 자리의 색 차이: 평균 {d.mean():.1f} · 중앙값 {np.median(d):.0f}"
              f" · 임계(DIFF_T=40) 미만 {100.0 * (d < 40).mean():.0f}%")
        print(f"  → 이 비율만큼이 '차분 0'으로 통째로 빠진다. 검은 머리가 특히 심한 이유다.")


if __name__ == "__main__":
    main()
