# -*- coding: utf-8 -*-
"""기본 흰 반팔티(남/여) 레이어를 원본 시트에서 차분 추출한다.

반바지(build_basic_shorts.py)와 같은 구조인데 **색 임계만 반대**다.
- 반바지: 어두운 것만 취함 (lum < 100)
- 흰티  : 밝은 것만 취함 (lum > LIGHT_MIN)
  ★base 가 입고 있는 베이지 나시(214,184,155)보다 확실히 밝아야 한다.
   나시를 같이 집으면 티셔츠 아래로 나시가 비쳐 보인다.

■ 원본 (2026-08-04 17:00 대표 재생성분)
- 1408×2986, 마젠타 배경, 워터마크 잘림. 반바지와 같은 규격.
- 대표 문형("기장은 기본캐릭터의 기본나시기장선에 맞출것")으로 기장이 12칸 일정하다.

    python char/build_basic_tee.py
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
from build_basic_shorts import strip_magenta, is_skin, keep_main, clean, DIFF_T  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "items")
D = r"C:\Users\allys\Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차\상의"

LIGHT_MIN = 150    # 이 밝기 이상
CHROMA_MAX = 28    # 무채색 판정 (max-min). base 나시(베이지)는 이보다 채도가 높다

CONFIG = [
    dict(out="top_basic_tee", name="기본 흰티(남)", base="walk.png",
         src=os.path.join(D, "남자 기본흰티.png")),
    dict(out="top_f_basic_tee", name="기본 흰티(여)", base="walk_female.png",
         src=os.path.join(D, "여캐", "여자 기본흰티.png")),
]


def main() -> int:
    ap = argparse.ArgumentParser()
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
                sa = src[:, :, 3] >= ALPHA_BIN
                ba = bse[:, :, 3] >= ALPHA_BIN
                m = sa & ((np.abs(src[:, :, :3] - bse[:, :, :3]).sum(axis=2) > DIFF_T) | ~ba)
                m &= ~is_skin(src)
                # ★밝기만 쓰면 흰티의 회색 주름·그늘이 잘려서 옆모습이 조각난다(실제로 그랬다).
                #   흰티는 무채색(R≈G≈B), base 나시는 베이지(R>G>B), 살색은 R≫B 다.
                #   → '무채색이면서 밝은 것'으로 잡으면 셋이 깨끗이 갈린다.
                rgb = src[:, :, :3]
                lum = rgb.mean(axis=2)
                chroma = rgb.max(axis=2) - rgb.min(axis=2)
                m &= (chroma <= CHROMA_MAX) & (lum > LIGHT_MIN)
                # 외곽선 어긋남이 만드는 1~2px 가시 제거 (반바지에서 겪은 것과 같은 문제)
                m = ndimage.binary_opening(m, np.ones((3, 3), bool))
                m = keep_main(m)
                m = clean(m)
                cell = np.zeros((CH, CW, 4), np.uint8)
                cell[m] = src[m].astype(np.uint8)
                cell[m, 3] = 255
                sheet.paste(Image.fromarray(cell, "RGBA"), (c * CW, r * CH))
                row.append(f"{int(m.sum()):5d}px")
            print("   row%d: %s" % (r, "  ".join(row)))
        dst = os.path.join(ITEMS, cfg["out"] + ".png")
        sheet.save(dst)
        print(f"   -> {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
