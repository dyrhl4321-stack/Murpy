# -*- coding: utf-8 -*-
"""여캐 상의·하의 레이어를 원본 시트에서 차분(diff)으로 추출한다.

■ 왜 차분인가
기존 `extract_top_v2.py` 는 **색 규칙**(파란 셔츠 전용)이라 회색·보라·차콜에 못 쓴다.
여캐 옷 시트는 base(빡빡이 여캐)와 몸·자세가 정합되어 있고 **둘 다 머리가 없다**.
그래서 색 규칙 없이 "base 와 다른 픽셀 = 옷"으로 잡을 수 있다.

■ 헤어와 다른 점 (중요)
헤어는 머리에 고정이라 **방향당 1프레임을 복제**한다. 옷은 팔·다리 움직임을 따라가야 하므로
**12프레임을 각각 추출**한다. 복제하면 걸을 때 옷이 몸을 안 따라간다.

    python char/build_outfit_layer.py                 # 전체
    python char/build_outfit_layer.py --only bottom_f_leggings
    python char/build_outfit_layer.py --dry           # 파일 안 쓰고 수치만
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_hair_layer import (BALD_F, DESK, CW, CH, ALPHA_BIN, SKIN_R,   # noqa: E402
                              Norm, load, pad_img, binarize)
from base_regions import neck_end   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "items")
NUKKI_F = os.path.join(DESK, "머피_로고삭제툴_에셋보관", "여캐")
ROWS = ["정면", "후면", "좌", "우"]

DIFF_T = 40        # RGB 변화 판정 (헤어 파이프라인과 같은 값)
STRAY_MAX = 40     # 앱 셀 기준 고립조각 하한
HOLE_MAX = 400     # 옷 안쪽 구멍은 메운다 (몸이 비쳐 보이면 안 된다)
NECK_MARGIN = 8    # 목 끝에서 이만큼 위까지는 옷으로 인정 (후드 칼라 등)

CONFIG = [
    dict(out="top_f_hoodzip", slot="top", name="회색 후드집업",
         src=os.path.join(NUKKI_F, "회색후드집업_clean-Photoroom.png")),
    dict(out="top_f_zipup", slot="top", name="보라 트레이닝 집업",
         src=os.path.join(NUKKI_F, "보라색 트레이닝 집업_clean-Photoroom.png")),
    dict(out="bottom_f_leggings", slot="bottom", name="차콜 레깅스",
         src=os.path.join(NUKKI_F, "챠콜레깅스_clean-Photoroom.png")),
    dict(out="bottom_f_sweatpants", slot="bottom", name="회색 츄리닝 바지",
         src=os.path.join(NUKKI_F, "회색츄리닝바지_clean-Photoroom.png")),
]


def is_skin(a):
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    return (a[:, :, 3] >= ALPHA_BIN) & (R >= SKIN_R) & (R > G + 20) & (G > B)


def extract_cell(src, bse):
    """이 프레임에서 옷 픽셀 마스크를 만든다."""
    sa = src[:, :, 3] >= ALPHA_BIN
    ba = bse[:, :, 3] >= ALPHA_BIN
    rgbdiff = np.abs(src[:, :, :3] - bse[:, :, :3]).sum(axis=2) > DIFF_T
    m = sa & (rgbdiff | ~ba)          # 색이 달라졌거나, base 엔 없던 자리(옷이 몸보다 넓다)
    m &= ~is_skin(src)                # 살색은 옷이 아니다

    # ★머리 구간은 통째로 뺀다. 옷은 목 아래다.
    #   프레임에 따라 원본의 머리가 base 와 몇 px 어긋나면 **얼굴 외곽선 전체가 차분으로
    #   잡힌다**(실측: 우 col2 만 2830 -> 5838px 로 튀고 머리에 검은 선이 겹쳤다).
    #   NECK_MARGIN 만큼 여유를 둬 후드 칼라 같은 목 근처 옷은 살린다.
    if ba.any():
        ys = np.where(ba.any(axis=1))[0]
        top = int(ys.min())
        cut = neck_end(ba, top) - NECK_MARGIN
        if cut > top:
            m[:cut] = False

    # 고립 조각 제거
    lab, n = ndimage.label(m, np.ones((3, 3), bool))
    if n > 1:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        for i, s in enumerate(sizes, start=1):
            if s < STRAY_MAX:
                m[lab == i] = False

    # 옷 안쪽 구멍 메움 (작은 것만 — 겨드랑이·팔 사이 큰 틈은 남긴다)
    holes = ndimage.binary_fill_holes(m) & ~m
    lab2, n2 = ndimage.label(holes, np.ones((3, 3), bool))
    for i in range(1, n2 + 1):
        h = lab2 == i
        if h.sum() <= HOLE_MAX:
            m |= h
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--only")
    args = ap.parse_args()

    base_arr = load(BALD_F)
    norm = Norm(base_arr)
    bpad = pad_img(base_arr)

    for cfg in CONFIG:
        if args.only and cfg["out"] != args.only:
            continue
        if not os.path.exists(cfg["src"]):
            print(f"!! 원본 없음 {cfg['src']}")
            continue
        spad = pad_img(load(cfg["src"]))
        sheet = Image.new("RGBA", (CW * 3, CH * 4), (0, 0, 0, 0))
        print(f"\n■ {cfg['name']}  ({cfg['out']}, {cfg['slot']})")
        for r in range(4):
            counts = []
            for c in range(3):
                # ★옷은 12프레임을 각각 뽑는다. 복제하면 걸을 때 몸을 안 따라간다.
                src = binarize(norm.cell(spad, r, c))
                bse = binarize(norm.cell(bpad, r, c))
                m = extract_cell(src, bse)
                cell = np.zeros((CH, CW, 4), int)
                cell[m] = src[m]
                cell[m, 3] = 255
                counts.append(int(m.sum()))
                sheet.paste(Image.fromarray(cell.astype(np.uint8), "RGBA"), (c * CW, r * CH))
            print(f"   {ROWS[r]:2s}  픽셀 {counts[0]} / {counts[1]} / {counts[2]}")

        a = np.asarray(sheet).astype(int)
        semi = int(((a[:, :, 3] > 0) & (a[:, :, 3] < 255)).sum())
        print(f"   반투명 {semi}px {'' if semi == 0 else '★위반'}")
        if not args.dry:
            sheet.save(os.path.join(ITEMS, cfg["out"] + ".png"))
            print(f"   -> items/{cfg['out']}.png")


if __name__ == "__main__":
    main()
