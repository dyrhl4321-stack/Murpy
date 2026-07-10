# -*- coding: utf-8 -*-
"""하의를 신었을 때 발목 둘레에 드러나는 맨살을 하의 픽셀로 메운다.

바지 시트와 신발 시트는 따로 그려져서 서로의 경계가 안 맞는다. 그 사이로 몸이 드러난다.
worn 원본에도 그 자리는 살뿐이라 마스크 편집으로는 못 메운다.

대상: 아래 셋을 모두 만족하는 픽셀
  1. 몸이 있고, 바지도 신발도 덮지 않는다 (드러난 살)
  2. 같은 열에서 바지 밑단보다 아래다 (허리·팔로 번지지 않게)
  3. 신발에서 REACH px 이내다 (맨 종아리를 칠하지 않게 — 버뮤다 보호)

색은 가장 가까운 바지 픽셀에서 복사한다. 새 색을 지어내지 않는다.

    python char/fill_exposed.py bottom_trainpt --shoes shoes_black shoes_white
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
REACH = 10          # 신발에서 이 거리 안쪽만 메운다


def _opaque(p: Path) -> np.ndarray:
    return np.asarray(Image.open(p).convert("RGBA"))[..., 3] > 128


def fill(item_id: str, shoe_ids: list[str], out: Path | None = None, reach: int = REACH) -> Path:
    body = _opaque(ROOT / "char" / "walk.png")
    arr = np.asarray(Image.open(ITEMS / f"{item_id}.png").convert("RGBA")).copy()
    pants = arr[..., 3] > 128

    shoes = [_opaque(ITEMS / f"{s}.png") for s in shoe_ids]

    # 조건 2: 같은 열에서 바지 밑단 아래
    below = np.zeros_like(pants)
    for r in range(ROWS):
        for c in range(COLS):
            for x in range(c * FW, (c + 1) * FW):
                pc = np.nonzero(pants[r * FH:(r + 1) * FH, x])[0]
                if not len(pc):
                    continue
                below[r * FH + int(pc.max()) + 1: (r + 1) * FH, x] = True

    target = np.zeros_like(pants)
    for s in shoes:
        exposed = body & ~pants & ~s & below
        # 조건 3: 신발에서 reach px 이내
        near = ndimage.distance_transform_edt(~s) <= reach
        target |= exposed & near

    if not target.any():
        print(f"{item_id}: 메울 곳 없음")
        return ITEMS / f"{item_id}.png"

    # 가장 가까운 바지 픽셀의 색을 복사한다
    _, (iy, ix) = ndimage.distance_transform_edt(~pants, return_indices=True)
    ys, xs = np.nonzero(target)
    arr[ys, xs] = arr[iy[ys, xs], ix[ys, xs]]
    arr[ys, xs, 3] = 255

    dst = out or (ITEMS / f"{item_id}.png")
    Image.fromarray(arr, mode="RGBA").save(dst)

    per = [int(target[r * FH:(r + 1) * FH, c * FW:(c + 1) * FW].sum()) for r in range(ROWS) for c in range(COLS)]
    print(f"{item_id}: {int(target.sum()):,}px 메움  프레임별 {per}  → {dst.name}")
    return dst


def fill_holes(item_id: str, out: Path | None = None) -> Path:
    """아이템에 뚫린 내부 구멍을 가장 가까운 자기 픽셀 색으로 메운다.

    상의·모자에는 쓰지 말 것. 겨드랑이 틈이나 모자 챙 밑처럼 몸이 보여야 하는
    정당한 구멍까지 메워버린다. 하의·신발 전용이다.
    """
    im = Image.open(ITEMS / f"{item_id}.png").convert("RGBA")
    arr = np.asarray(im).copy()
    on = arr[..., 3] > 128

    holes = np.zeros_like(on)
    for r in range(ROWS):
        for c in range(COLS):
            sl = (slice(r * FH, (r + 1) * FH), slice(c * FW, (c + 1) * FW))
            m = on[sl]
            if not m.any():
                continue
            lab, _ = ndimage.label(~m)
            border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
            border = border[border > 0]
            holes[sl] = (~np.isin(lab, border)) & (~m)

    if holes.any():
        _, (iy, ix) = ndimage.distance_transform_edt(~on, return_indices=True)
        ys, xs = np.nonzero(holes)
        arr[ys, xs] = arr[iy[ys, xs], ix[ys, xs]]
        arr[ys, xs, 3] = 255

    dst = out or (ITEMS / f"{item_id}.png")
    Image.fromarray(arr, mode="RGBA").save(dst)
    print(f"{item_id}: 내부 구멍 {int(holes.sum()):,}px 메움 → {dst.name}")
    return dst


def fill_seams(item_id: str, out: Path | None = None, max_width: int = 3) -> Path:
    """옷을 가로지르는 좁은 세로 틈(솔기)을 메운다.

    한 행에서 좌우 양쪽이 옷이고 그 사이 빈칸이 max_width 이하일 때만 채운다.
    다리 사이 틈(보통 5px 이상)은 정상이므로 건드리지 않는다.
    """
    im = Image.open(ITEMS / f"{item_id}.png").convert("RGBA")
    arr = np.asarray(im).copy()
    on = arr[..., 3] > 128

    seam = np.zeros_like(on)
    for y in range(on.shape[0]):
        row = on[y]
        x = 0
        while x < on.shape[1]:
            if row[x]:
                x += 1
                continue
            run = x
            while x < on.shape[1] and not row[x]:
                x += 1
            width = x - run
            # 프레임 경계를 넘지 않고, 좌우 양쪽이 옷이며, 충분히 좁을 때
            same_frame = (run - 1) // FW == x // FW if x < on.shape[1] else False
            if width <= max_width and run > 0 and x < on.shape[1] and row[run - 1] and row[x] and same_frame:
                seam[y, run:x] = True

    if seam.any():
        _, (iy, ix) = ndimage.distance_transform_edt(~on, return_indices=True)
        ys, xs = np.nonzero(seam)
        arr[ys, xs] = arr[iy[ys, xs], ix[ys, xs]]
        arr[ys, xs, 3] = 255

    dst = out or (ITEMS / f"{item_id}.png")
    Image.fromarray(arr, mode="RGBA").save(dst)
    print(f"{item_id}: 세로 솔기 {int(seam.sum()):,}px 메움 (폭 ≤{max_width}) → {dst.name}")
    return dst


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("item")
    ap.add_argument("--shoes", nargs="*", default=[])
    ap.add_argument("--reach", type=int, default=REACH)
    ap.add_argument("--holes", action="store_true", help="내부 구멍도 메운다 (하의·신발 전용)")
    ap.add_argument("--seams", type=int, metavar="W", help="폭 W 이하의 세로 솔기를 메운다")
    ap.add_argument("-o", "--out", type=Path)
    a = ap.parse_args()
    if a.holes:
        fill_holes(a.item, a.out)
    if a.seams:
        fill_seams(a.item, a.out, a.seams)
    if a.shoes:
        fill(a.item, a.shoes, a.out, a.reach)
    return 0


if __name__ == "__main__":
    sys.exit(main())
