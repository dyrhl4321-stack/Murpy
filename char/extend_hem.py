# -*- coding: utf-8 -*-
"""하의 밑단을 신발 목까지 자동으로 늘린다.

문제: 바지 시트와 신발 시트는 따로 그려져서, 바지 밑단이 신발 목보다 위에 있다.
그 사이 구간은 두 아이템 다 소유하지 않아 몸(맨살)이 드러난다.
worn 원본에도 그 자리는 살뿐이라 마스크 편집으로는 못 메운다.

해법: 바지 **자신의** 커프(밑단 띠)를 아래로 옮기고, 비워진 자리를 바로 위
다리통 색으로 채운다. 새 색을 지어내지 않고 아이템의 실제 픽셀만 재배치한다.

    python char/extend_hem.py bottom_trainpt --shoes shoes_black shoes_white
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ROOT / "char" / "items"
FW, FH, COLS, ROWS = 141, 224, 3, 4
MAX_EXTEND = 24          # 이보다 긴 틈은 그림이 어긋난 것이다. 사람이 봐야 한다.


def _opaque(p: Path) -> np.ndarray:
    return np.asarray(Image.open(p).convert("RGBA"))[..., 3] > 128


def extend(item_id: str, shoe_ids: list[str], out: Path | None = None) -> Path:
    body = _opaque(ROOT / "char" / "walk.png")
    arr = np.asarray(Image.open(ITEMS / f"{item_id}.png").convert("RGBA")).copy()
    pants = arr[..., 3] > 128

    shoes = [_opaque(ITEMS / f"{s}.png") for s in shoe_ids]
    shoe_any = np.zeros_like(body)
    for s in shoes:
        shoe_any |= s

    # 신발을 신었을 때 드러나는 몸 = 바지도 신발도 안 덮는 곳 (신발별 합집합)
    exposed = np.zeros_like(body)
    for s in shoes:
        exposed |= body & ~pants & ~s

    filled = 0
    skipped = 0
    for r in range(ROWS):
        for c in range(COLS):
            for x in range(c * FW, (c + 1) * FW):
                col = slice(r * FH, (r + 1) * FH)
                pc = np.nonzero(pants[col, x])[0]
                if not len(pc):
                    continue
                hem = int(pc.max())

                # 밑단 바로 아래로 이어지는 노출 구간의 길이
                k = 0
                while hem + 1 + k < FH and exposed[r * FH + hem + 1 + k, x]:
                    k += 1
                if k == 0:
                    continue
                # 연장 끝에 신발이 있어야 한다. 허공(다리 사이 등)으로 뻗지 않게.
                end = hem + 1 + k
                if end >= FH or not shoe_any[r * FH + end, x]:
                    skipped += k
                    continue
                if k > MAX_EXTEND or hem - k < 0:
                    skipped += k
                    continue

                y0 = r * FH
                cuff = arr[y0 + hem - k + 1: y0 + hem + 1, x].copy()   # 커프 k줄
                tube = arr[y0 + hem - k, x].copy()                      # 커프 바로 위 = 다리통

                arr[y0 + hem + 1: y0 + hem + 1 + k, x] = cuff           # 커프를 내리고
                arr[y0 + hem - k + 1: y0 + hem + 1, x] = tube           # 빈 자리는 다리통으로
                filled += k

    dst = out or (ITEMS / f"{item_id}.png")
    Image.fromarray(arr, mode="RGBA").save(dst)

    a = arr[..., 3]
    semi = int(((a > 0) & (a < 255)).sum())
    print(f"{item_id}: {filled:,}px 연장 (건너뜀 {skipped:,}px)  반투명 {semi}  → {dst.name}")
    return dst


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("item")
    ap.add_argument("--shoes", nargs="+", required=True)
    ap.add_argument("-o", "--out", type=Path)
    a = ap.parse_args()
    extend(a.item, a.shoes, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
