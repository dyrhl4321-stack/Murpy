# -*- coding: utf-8 -*-
"""겹쳐 입는 아이템 사이에 드러나는 살 띠(솔기)를 메운다.

시트가 아이템마다 따로 그려져서, 두 아이템의 경계가 픽셀 단위로 맞지 않는다.
그 틈으로 몸이 1~2px 씩 비친다. 셔츠 밑단 아래, 바지 밑단과 신발 목 사이가 그렇다.

규칙: **두 아이템 사이에 끼인 얇은 몸 픽셀은 위에 그려지는 아이템이 덮는다.**

솔기의 조건 (셋 다 만족):
  1. 몸이 있고, 두 아이템 어느 쪽도 덮지 않는다
  2. 그 연결덩어리가 두 아이템에 **모두** 닿는다  (둘 사이에 끼어 있다)
  3. 덩어리가 얇다 (내접 반지름 ≤ max_thick)  — 맨종아리 같은 넓은 살은 제외

색은 채워 넣을 아이템(--into)의 가장 가까운 픽셀에서 복사한다.

    # 셔츠 밑단 아래 살 띠 → 셔츠가 덮는다
    python char/seal_gaps.py --into top_redhood --with bottom_trainpt bottom_bermuda

    # 바지 밑단과 신발 목 사이 → 바지가 덮는다 (신발이 위에 그려져 가려준다)
    python char/seal_gaps.py --into bottom_trainpt --with shoes_black shoes_white

주의: 버뮤다처럼 발목이 원래 맨살인 조합에는 쓰지 말 것. 반바지 천이 종아리로 번진다.
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

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ROOT / "char" / "items"
FW, FH, COLS, ROWS = 141, 224, 3, 4
MAX_THICK = 2.5      # 내접 반지름. 이보다 두꺼우면 솔기가 아니라 드러나야 할 살이다


def _opaque(p: Path) -> np.ndarray:
    return np.asarray(Image.open(p).convert("RGBA"))[..., 3] > 128


def seam_mask(body: np.ndarray, a: np.ndarray, b: np.ndarray, max_thick: float) -> np.ndarray:
    gap = body & ~a & ~b
    lab, n = ndimage.label(gap, np.ones((3, 3)))
    if n == 0:
        return gap & False

    near_a = ndimage.binary_dilation(a, np.ones((3, 3)))
    near_b = ndimage.binary_dilation(b, np.ones((3, 3)))

    keep = np.zeros_like(gap)
    for i in range(1, n + 1):
        comp = lab == i
        if not (comp & near_a).any() or not (comp & near_b).any():
            continue                                   # 둘 사이에 끼어 있지 않다
        if ndimage.distance_transform_edt(comp).max() > max_thick:
            continue                                   # 넓은 살이다 (맨종아리 등)
        keep |= comp
    return keep


def seal(into: str, others: list[str], max_thick: float = MAX_THICK, out: Path | None = None) -> Path:
    body = _opaque(ROOT / "char" / "walk.png")
    arr = np.asarray(Image.open(ITEMS / f"{into}.png").convert("RGBA")).copy()
    a = arr[..., 3] > 128

    target = np.zeros_like(a)
    for o in others:
        m = seam_mask(body, a, _opaque(ITEMS / f"{o}.png"), max_thick)
        target |= m
        print(f"  ↔ {o}: 솔기 {int(m.sum()):,}px")

    if not target.any():
        print(f"{into}: 메울 솔기 없음")
        return ITEMS / f"{into}.png"

    _, (iy, ix) = ndimage.distance_transform_edt(~a, return_indices=True)
    ys, xs = np.nonzero(target)
    arr[ys, xs] = arr[iy[ys, xs], ix[ys, xs]]
    arr[ys, xs, 3] = 255

    dst = out or (ITEMS / f"{into}.png")
    Image.fromarray(arr, mode="RGBA").save(dst)
    print(f"{into}: 총 {int(target.sum()):,}px 메움 → {dst.name}")
    return dst


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--into", required=True, help="틈을 메울 아이템 (위에 그려지는 쪽)")
    ap.add_argument("--with", dest="others", nargs="+", required=True, help="맞닿는 아이템들")
    ap.add_argument("--max-thick", type=float, default=MAX_THICK)
    ap.add_argument("-o", "--out", type=Path)
    a = ap.parse_args()
    seal(a.into, a.others, a.max_thick, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
