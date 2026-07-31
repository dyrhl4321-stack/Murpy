# -*- coding: utf-8 -*-
"""긴 생머리 정면 앞머리 / 후면 하단 '그을림'의 정체를 잰다.

대표: "정면 앞머리쪽이 쥐 파먹은 것 같고, 뒷머리 하단부가 검게 그을려 있다."

두 결함은 성격이 다를 수 있다:
  - 앞머리  = 원본에 있는 머리카락이 **빠진 것**(알파 누락)
  - 그을림  = 알파는 맞는데 **색이 어두워진 것**(RGB 차이)
어느 쪽인지 갈라야 고치는 방법이 정해진다.

    python char/diag_long_hair.py
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_hair_layer import (BALD_F, NUKKI, CW, CH, ALPHA_BIN,   # noqa: E402
                              Norm, load, pad_img, binarize)

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "hair_f_long.png"
SRC = os.path.join(NUKKI, "여자 검정생머리_clean-Photoroom.png")


def main():
    walk = np.asarray(Image.open(os.path.join(HERE, "walk_female.png"))
                      .convert("RGBA")).astype(int)
    cur = np.asarray(Image.open(os.path.join(HERE, "items", NAME)).convert("RGBA")).astype(int)
    norm = Norm(load(BALD_F))
    src_pad = pad_img(load(SRC))

    # ★원본 알파는 '캐릭터 전체'(몸·옷 포함)다. 머리카락만 골라야 비교가 성립한다.
    #   긴 생머리는 검정이므로 어두운 픽셀로 고른다. 우리 레이어의 실제 머리색 분포로 임계를 잡는다.
    cur_all = np.asarray(Image.open(os.path.join(HERE, "items", NAME)).convert("RGBA")).astype(int)
    hm = cur_all[:, :, 3] >= ALPHA_BIN
    lum_hair = cur_all[hm][:, :3].mean(axis=1)
    DARK = float(np.percentile(lum_hair, 99)) + 10
    print(f"머리색 밝기: 중앙 {np.median(lum_hair):.0f} / 99퍼센타일 {np.percentile(lum_hair,99):.0f}"
          f" → 원본에서 '머리카락'으로 볼 임계 = 밝기 < {DARK:.0f}")

    for r, label in [(0, "정면"), (1, "후면")]:
        worn = binarize(norm.cell(src_pad, r, 0))
        wm = (worn[:, :, 3] >= ALPHA_BIN) & (worn[:, :, :3].mean(axis=2) < DARK)
        hc = cur[r * CH:(r + 1) * CH, 0:CW]
        h = hc[:, :, 3] >= ALPHA_BIN
        bm = walk[r * CH:(r + 1) * CH, 0:CW, 3] >= ALPHA_BIN
        top = int(np.where(bm.any(axis=1))[0].min())

        print(f"\n■ {label}  원본 헤어 {int(wm.sum())}px / 현재 {int(h.sum())}px")
        print(f"   원본에만 있음 {int((wm & ~h).sum())}px · 현재에만 있음 {int((h & ~wm).sum())}px")

        both = wm & h
        if both.any():
            d = np.abs(worn[both][:, :3] - hc[both][:, :3]).sum(axis=1)
            print(f"   둘 다 있는 자리 {int(both.sum())}px 의 색 차이: 평균 {d.mean():.1f}"
                  f" · 24 초과(눈에 보임) {100.0 * (d > 24).mean():.0f}%")
            # 우리 것이 더 어두운가?
            lum_w = worn[both][:, :3].mean(axis=1)
            lum_c = hc[both][:, :3].mean(axis=1)
            print(f"   밝기: 원본 {lum_w.mean():.1f} → 현재 {lum_c.mean():.1f}"
                  f"  (현재가 더 어두운 픽셀 {100.0 * (lum_c < lum_w - 8).mean():.0f}%)")

        # 세로 구간별 — '하단부만 그을렸나' 확인
        print("   상대y 구간별  [원본에만 |  더 어두워진 |  밝기 원본→현재]")
        for lo, hi in [(0, 40), (40, 80), (80, 120), (120, 160), (160, 213)]:
            band = np.zeros_like(h)
            y0, y1 = min(top + lo, CH), min(top + hi, CH)
            if y0 >= y1:
                continue
            band[y0:y1] = True
            miss = int((wm & ~h & band).sum())
            bb = both & band
            if bb.any():
                lw = worn[bb][:, :3].mean(axis=1).mean()
                lc = hc[bb][:, :3].mean(axis=1).mean()
                dark = int(((hc[bb][:, :3].mean(axis=1) < worn[bb][:, :3].mean(axis=1) - 8)).sum())
                print(f"     y{lo:3d}~{hi:<3d}  {miss:5d}px  |  {dark:5d}px  |  {lw:5.1f} → {lc:5.1f}")
            else:
                print(f"     y{lo:3d}~{hi:<3d}  {miss:5d}px  |      - |    -")


if __name__ == "__main__":
    main()
