# -*- coding: utf-8 -*-
"""진한 색 상의의 가장자리에 남은 '살색 오염 픽셀'을 원단색으로 되돌린다.

추출 과정에서 밑단·소매 같은 윤곽선이 몸 살색과 섞여 굳으면, 불투명인데 색만
살색인 픽셀 띠가 남는다. seal_gaps.py 는 '투명한 틈'만 메우므로 이런 불투명
오염은 못 고친다. 이 도구가 그 픽셀을 근처 정상 원단색으로 덮는다.

규칙:
  - 대상 = 불투명(alpha>200) ∧ 살색 팔레트
  - 정상 원단색이 가까이(≤ --near px) 있으면 → 가장 가까운 정상 픽셀색으로 recolor (밑단·가장자리)
  - 가까이 없으면 → 삭제 (윤곽 밖 부유 노이즈)

⚠️ 원단 자체가 살색/베이지/연분홍인 아이템(링거티 등)에는 쓰지 말 것 —
   원단 전체가 대상으로 잡힌다. --max 가드로 자동 중단한다.

    python char/recolor_edge_skin.py top_redhood
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


def skin_mask(arr: np.ndarray) -> np.ndarray:
    r, g, b = arr[..., 0].astype(int), arr[..., 1].astype(int), arr[..., 2].astype(int)
    return ((r > 140) & (r < 250) & (g > 85) & (g < 195) & (b > 60) & (b < 165)
            & (r >= g) & (g >= b) & ((r - b) > 25))


def recolor(item: str, near: float = 3.0, max_px: int = 400, out: Path | None = None) -> Path:
    arr = np.asarray(Image.open(ITEMS / f"{item}.png").convert("RGBA")).copy()
    opaque = arr[..., 3] > 200
    target = opaque & skin_mask(arr)
    n = int(target.sum())
    print(f"{item}: 살색 오염 후보 {n}px")
    if n == 0:
        print("  고칠 것 없음")
        return ITEMS / f"{item}.png"
    if n > max_px:
        print(f"  ✗ 중단: {n} > max {max_px} — 원단색이 살색 계열인 아이템일 수 있음. 이 도구 대상 아님.")
        sys.exit(2)

    source = opaque & ~target                     # 정상 원단
    dist, (iy, ix) = ndimage.distance_transform_edt(~source, return_indices=True)

    ys, xs = np.nonzero(target)
    fill = dist[ys, xs] <= near                   # 근처에 정상색 있음 → recolor
    fy, fx = ys[fill], xs[fill]
    arr[fy, fx] = arr[iy[fy, fx], ix[fy, fx]]
    arr[fy, fx, 3] = 255

    dy, dx = ys[~fill], xs[~fill]                  # 고립 → 삭제
    arr[dy, dx] = 0

    print(f"  recolor {int(fill.sum())}px, 삭제(고립) {int((~fill).sum())}px")
    dst = out or (ITEMS / f"{item}.png")
    Image.fromarray(arr, mode="RGBA").save(dst)
    print(f"  → {dst.name}")
    return dst


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("item")
    ap.add_argument("--near", type=float, default=3.0)
    ap.add_argument("--max", type=int, default=400, dest="max_px")
    ap.add_argument("-o", "--out", type=Path)
    a = ap.parse_args()
    recolor(a.item, a.near, a.max_px, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
