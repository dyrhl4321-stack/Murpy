# -*- coding: utf-8 -*-
"""대숲 가면을 올릴 '정면 얼굴' 상자를 base 에서 실측한다.

가면은 대숲 전용 레이어라 **정면(row0)만** 있으면 된다. 대표가 그 크기에 맞춰 그리면
내가 3열(정지·걸음A·걸음B)에 복제해 붙인다. 걸음 프레임은 두상이 몇 px 움직이므로
열별 두상 기준으로 평행이동한다(헤어와 같은 방식).

    python char/measure_face_box.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from base_regions import BROW, FACE_X, EAR_TOP_FB, ALPHA_BIN, CW, CH, largest  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent


def main() -> int:
    for name, ko in (("walk.png", "남캐"), ("walk_female.png", "여캐")):
        p = HERE / name
        if not p.exists():
            print(f"!! 없음 {name}")
            continue
        sheet = np.asarray(Image.open(p).convert("RGBA")).astype(int)
        print(f"■ {ko} ({name})")
        for c in range(3):
            cell = sheet[0:CH, c * CW:(c + 1) * CW]
            bm = largest(cell[:, :, 3] >= ALPHA_BIN)
            top = int(np.nonzero(bm.any(axis=1))[0].min())
            x0, x1 = FACE_X[name]
            # 눈썹 위 6px 부터 귀 높이까지 = 가면이 덮을 세로 범위
            y0 = top + BROW[name][0] - 6
            y1 = top + EAR_TOP_FB[name][0] + 6
            print(f"   col{c}  머리최상단 y={top:3d}   가면상자 x{x0}~{x1} ({x1-x0+1}px) "
                  f"/ y{y0}~{y1} ({y1-y0+1}px)")
        print()
    print("→ 대표 제작 규격: 141×224 투명 PNG 한 장(정면 정지 기준). 위 상자 안에 가면만 그리고")
    print("  나머지는 전부 투명. 배경을 형광 마젠타로 주셔도 내가 누끼 처리한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
