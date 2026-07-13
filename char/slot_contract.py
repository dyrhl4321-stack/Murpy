# -*- coding: utf-8 -*-
"""슬롯 계약(slot contract) — 긴바지×신발 경계를 '맞추기'가 아니라 '겹침'으로 보장한다.

기존 방식의 근본 문제: 아이템마다 실루엣이 제각각이라 바지 밑단과 신발 목이
픽셀 단위로 안 맞고, 조합마다 살 비침·이중 경계·주황 잔선이 생겼다(조합 폭발).

계약 (2026-07-13 검증 완료 규칙 — trainpt×black/white 12프레임 앱-정확 렌더 통과):
  1. [잔선 recolor] 밑단·신발의 따뜻한 추출 잔재(살색 블렌드 갈색/주황: R>B 우세)를
     주변 무채색 원단색으로 되돌린다. 검정/무채색 아이템은 전역 엄격 패스((R-B)>12).
  2. [발목 커프] 발목 밴드(SHOE_TOP-4 ~ SHOE_TOP+OVERLAP)에서 몸 살이 드러나는 곳을
     바지 원단으로 채운다 — 커프가 발목을 감싸고, 신발이 그 위를 덮는다.
  3. [잔여 살 = 신발이 덮음] 신발 구역(y>=190)에서 바지·신발 어느 쪽도 안 덮는 몸 살은
     신발 시트에 인접(<=8px) 신발색으로 채운다(걷기 프레임 반대발 등).
  ✗ [금지] 신발 밖으로 나온 바지 픽셀을 '삭제'하지 말 것 — 그 픽셀이 발목 살을 덮는
     커프다. 삭제하면 살이 드러난다(2026-07-13 실측: 삭제 규칙으로 12프레임 살 노출 발생 후 롤백).

  ※ 반바지(버뮤다 등 overShoes 하의)는 대상 아님 — 종아리 맨살이 의도된 디자인.
  ※ 검증은 반드시 앱-정확 렌더로: 시트를 (3W×4DH) BILINEAR 리사이즈 후 프레임 크롭.
     (앱은 image-rendering:auto 스무딩. 정수 NEAREST 검증은 실앱과 다르다.)

    python char/slot_contract.py --bottom bottom_trainpt --shoes shoes_black shoes_white
    python char/slot_contract.py --bottom bottom_trainpt --shoes shoes_black --achromatic
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
WALK = ROOT / "char" / "walk.png"
CW, CH = 141, 224
SHOE_TOP = 192      # 신발 구역 시작(전 신발 실측 y192)
OVERLAP = 8         # 커프가 신발 구역 안으로 들어가는 깊이


def _cells(arr):
    for r in range(4):
        for c in range(3):
            yield r, c, arr[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]


def _skin(a):
    R, G, B, A = (a[..., i].astype(int) for i in range(4))
    return (A > 60) & (R > 110) & (R > G + 12) & (R > B + 25)


def recolor_warm(cell, y_from, thr):
    """따뜻한 잔재((R-B)>thr)를 가장 가까운 무채색 원단으로 recolor."""
    R, G, B, A = (cell[..., i].astype(int) for i in range(4))
    yy = np.arange(CH)[:, None]
    target = (A > 60) & ((R - B) > thr) & (R > 55) & (yy >= y_from)
    fabric = (A > 60) & ~target & ((R - B) <= thr)
    if not target.any() or not fabric.any():
        return 0
    _, (iy, ix) = ndimage.distance_transform_edt(~fabric, return_indices=True)
    ys, xs = np.nonzero(target)
    cell[ys, xs, :3] = cell[iy[ys, xs], ix[ys, xs], :3]
    return len(ys)


def apply_contract(bottom_name: str, shoes_names: list[str], achromatic: bool = True):
    body = np.asarray(Image.open(WALK).convert("RGBA"))
    thr = 12 if achromatic else 22
    y_from = 150 if achromatic else 170

    # 1)+2) 바지: 잔선 recolor + 발목 커프 채움
    bp = ITEMS / f"{bottom_name}.png"
    pants = np.asarray(Image.open(bp).convert("RGBA")).copy()
    n_re = n_cuff = 0
    for r, c, cell in _cells(pants):
        n_re += recolor_warm(cell, y_from, thr)
        bcell = body[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
        yy = np.arange(CH)[:, None]
        band = (yy >= SHOE_TOP - 4) & (yy < SHOE_TOP + OVERLAP)
        need = _skin(bcell) & band & (cell[..., 3] <= 60)
        if need.any():
            A = cell[..., 3]
            R, G, B = (cell[..., i].astype(int) for i in range(3))
            fabric = (A > 60) & ((R - B) <= thr)
            if fabric.any():
                _, (iy, ix) = ndimage.distance_transform_edt(~fabric, return_indices=True)
                ys, xs = np.nonzero(need)
                cell[ys, xs, :3] = cell[iy[ys, xs], ix[ys, xs], :3]
                cell[ys, xs, 3] = 255
                n_cuff += len(ys)
    Image.fromarray(pants).save(bp)
    print(f"{bottom_name}: 잔선recolor {n_re}px, 발목커프 {n_cuff}px")

    # 1)+3) 신발: 잔선 recolor + 잔여 살 덮기
    for n in shoes_names:
        sp = ITEMS / f"{n}.png"
        sh = np.asarray(Image.open(sp).convert("RGBA")).copy()
        t_re = t_cover = 0
        for r, c, cell in _cells(sh):
            t_re += recolor_warm(cell, 0 if achromatic else SHOE_TOP - 8, thr)
            y0, x0 = r * CH, c * CW
            b = body[y0:y0 + CH, x0:x0 + CW]
            p = pants[y0:y0 + CH, x0:x0 + CW]
            yy = np.arange(CH)[:, None]
            resid = _skin(b) & (yy >= 190) & (p[..., 3] <= 60) & (cell[..., 3] <= 60)
            if resid.any():
                op = cell[..., 3] > 60
                if op.any():
                    dist, (iy, ix) = ndimage.distance_transform_edt(~op, return_indices=True)
                    ys, xs = np.nonzero(resid)
                    near = dist[ys, xs] <= 8
                    fy, fx = ys[near], xs[near]
                    cell[fy, fx, :3] = cell[iy[fy, fx], ix[fy, fx], :3]
                    cell[fy, fx, 3] = 255
                    t_cover += len(fy)
        Image.fromarray(sh).save(sp)
        print(f"{n}: 잔선recolor {t_re}px, 잔여살덮음 {t_cover}px")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bottom", required=True)
    ap.add_argument("--shoes", nargs="+", required=True)
    ap.add_argument("--achromatic", action="store_true", default=True,
                    help="검정/무채색 아이템: 전역 엄격 잔선 제거(기본 켜짐)")
    a = ap.parse_args()
    apply_contract(a.bottom, a.shoes, a.achromatic)
    return 0


if __name__ == "__main__":
    sys.exit(main())
