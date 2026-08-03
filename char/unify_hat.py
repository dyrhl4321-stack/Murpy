# -*- coding: utf-8 -*-
r"""조합 시트마다 갈린 모자의 **색·재질·로고**를 통일한다. 모양은 건드리지 않는다.

★대표 요구(2026-08-03): "모자의 재질 + 색 + 로고 같은 디테일만 비슷해 보이면 돼."
  모자 **모양·크기·위치는 AI 것을 그대로 둔다** — 헤어마다 머리 부피가 달라서
  모자가 앉는 높이·폭이 달라야 자연스럽고, AI 가 그건 맞춰 그렸다.
  갈리는 건 안쪽 디테일(검정 톤이 회색으로 뜨거나, 로고 폰트·굵기가 다르거나) 뿐이다.

지금은 **측정** 단계다. 무엇이 얼마나 갈렸는지 먼저 재고 통일 규칙을 정한다.

    python char/unify_hat.py            # 12장의 모자 색·로고 실측
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
COMBO = HERE / "_combo"
CW, CH = 141, 224
ALPHA_BIN = 128
ROW_KO = ["정면", "후면", "좌", "우"]


def alpha(a: np.ndarray) -> np.ndarray:
    return a[:, :, 3] >= ALPHA_BIN


def logo_mask(cell: np.ndarray) -> np.ndarray:
    """모자 로고 = 밝은 흰/크림 덩어리.

    ★살색 배제가 필수다. 밝기만 보면 **얼굴을 로고로 잡는다** — 세미리프에서 로고가
      652px·35덩이로 튀고 모자 영역이 3배가 됐던 원인이 이것이었다.
      로고는 무채색에 가까워 R-G 가 작고(실측 11~14), 살색은 R-G 가 크다(실측 55).
    """
    R, G, B = cell[:, :, 0].astype(int), cell[:, :, 1].astype(int), cell[:, :, 2].astype(int)
    bright = alpha(cell) & (R > 180) & (G > 165) & (B > 140)
    return bright & (R - G < 30) & (G - B < 40) & hat_band(cell)


HAT_BAND = 58        # 머리 최상단부터 이 높이까지가 모자다 (정면 로고 실측 y42~58, 밑단 ~65)


def hat_band(cell: np.ndarray) -> np.ndarray:
    """모자가 있을 수 있는 밴드. ★로고·모자 판정을 반드시 여기로 가둔다 —
    풀어놓으면 얼굴 주변 AI 드리프트 조각을 로고로 잡는다(세미리프에서 실제로 발생)."""
    a = alpha(cell)
    band = np.zeros_like(a)
    if not a.any():
        return band
    top = int(np.nonzero(a.any(axis=1))[0].min())
    band[top:top + HAT_BAND] = True
    return band


def hat_body(cell: np.ndarray, logo: np.ndarray) -> np.ndarray:
    """모자 본체 = 밴드 안의 픽셀에서 로고를 뺀 것."""
    return alpha(cell) & hat_band(cell) & ~logo


def bbox(m: np.ndarray):
    ys, xs = np.nonzero(m)
    if not len(ys):
        return None
    return int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())


def stamp_logos(master_id: str, apply: bool) -> None:
    """마스터 시트의 로고를 다른 시트에 그대로 찍는다.

    ★모자 모양·크기·위치는 손대지 않는다(대표 요구). 바꾸는 것은 로고 픽셀뿐이다.
    로고는 방향마다 보이는 글자가 다르므로(정면 GBD / 좌 BD / 우 G / 후면 없음)
    **같은 행끼리만** 옮긴다. 위치는 대상 칸의 기존 로고 중심에 맞춘다.
    """
    mp = COMBO / f"{master_id}.png"
    master = np.asarray(Image.open(mp).convert("RGBA")).astype(np.uint8)

    patches = {}
    for r in range(4):
        cell = master[r * CH:(r + 1) * CH, 0:CW]
        bb = bbox(logo_mask(cell))
        if bb is None:
            continue
        y0, y1, x0, x1 = bb
        patch = cell[y0:y1 + 1, x0:x1 + 1].copy()
        pm = logo_mask(master[r * CH:(r + 1) * CH, 0:CW])[y0:y1 + 1, x0:x1 + 1]
        patches[r] = (patch, pm)
        print(f"   마스터 로고 {ROW_KO[r]}: {x1-x0+1}×{y1-y0+1}  {int(pm.sum())}px")

    # ★스탬프를 걸면 오히려 망가지는 시트가 있다 — 로고가 살구빛으로 떠 있어 검출이
    #   부분적으로만 되고, 지우다 만 잔재 위에 마스터가 겹쳐 글자가 뭉개진다.
    #   세미리프 GBD 는 원본 로고가 이미 읽히므로 건드리지 않는 편이 낫다(실측 비교).
    SKIP = {"hair_m_semileaf__hat_beanie"}

    for p in sorted(COMBO.glob("*__*.png")):
        if p.stem.endswith("_full") or p.stem == master_id or p.stem in SKIP:
            continue
        if ("beanie" in p.stem) != ("beanie" in master_id):
            continue                                   # 비니 마스터는 비니에만
        sheet = np.asarray(Image.open(p).convert("RGBA")).astype(np.uint8).copy()
        hit = 0
        for r, (patch, pm) in patches.items():
            ph, pw = pm.shape
            for c in range(3):
                ys, xs = slice(r * CH, (r + 1) * CH), slice(c * CW, (c + 1) * CW)
                cell = sheet[ys, xs]
                lm = logo_mask(cell)
                bb = bbox(lm)
                if bb is None:
                    continue
                y0, y1, x0, x1 = bb
                cy, cx = (y0 + y1) // 2, (x0 + x1) // 2
                ty, tx = cy - ph // 2, cx - pw // 2
                if ty < 0 or tx < 0 or ty + ph > CH or tx + pw > CW:
                    continue
                # 기존 로고 자리를 모자 어두운색으로 메운 뒤 마스터 로고를 찍는다
                body = cell[hat_body(cell, lm)][:, :3]
                fill = np.median(body, axis=0).astype(np.uint8) if len(body) else np.array(
                    [30, 28, 26], np.uint8)
                fill4 = np.array([*fill, 255], np.uint8)
                # ★logo_mask 만으로 지우면 잔재가 남는다 — 시트에 따라 로고가 살구빛으로 떠
                #   검출을 빠져나가고, 그 위에 마스터를 찍으면 두 글자가 겹쳐 뭉개진다
                #   (세미리프 새 버전에서 실제로 발생). 밴드 안의 밝은 픽셀을 통째로 민다.
                Rc, Gc = cell[:, :, 0].astype(int), cell[:, :, 1].astype(int)
                erase = alpha(cell) & hat_band(cell) & (Rc > 130) & (Gc > 110)
                cell[erase] = fill4
                tgt = cell[ty:ty + ph, tx:tx + pw]
                tgt[...] = fill4                     # 패치 자리는 무조건 모자색으로 초기화
                tgt[pm] = patch[pm]
                hit += 1
        if apply:
            Image.fromarray(sheet, "RGBA").save(p)
        print(f"   {p.stem:34s} 로고 {hit:2d}칸 교체{'' if apply else ' (미리보기만)'}")


def main() -> int:
    if "--stamp" in sys.argv:
        apply = "--apply" in sys.argv
        print("■ 로고 통일 — 마스터 hair_m_basic__hat_beanie")
        stamp_logos("hair_m_basic__hat_beanie", apply)
        return 0

    files = sorted(p for p in COMBO.glob("*__*.png") if not p.stem.endswith("_full"))
    if not files:
        raise SystemExit("char/_combo 가 비어 있다 — import_hat_combo.py 를 먼저 돌려라")

    rows = []
    for p in files:
        sheet = np.asarray(Image.open(p).convert("RGBA")).astype(np.uint8)
        cell = sheet[0:CH, 0:CW]                              # 정면 정지 = 로고가 다 보이는 칸
        logo = logo_mask(cell)
        body = hat_body(cell, logo)
        if not body.any():
            print(f"!! 모자 못 찾음 {p.stem}")
            continue
        px = cell[body][:, :3].astype(int)
        med = np.median(px, axis=0).astype(int)
        dark = px[px.mean(axis=1) < np.percentile(px.mean(axis=1), 40)]
        darkmed = np.median(dark, axis=0).astype(int) if len(dark) else med
        lg = cell[logo][:, :3].astype(int)
        lgmed = np.median(lg, axis=0).astype(int) if len(lg) else np.array([0, 0, 0])
        lab, nblob = ndimage.label(logo, np.ones((3, 3), bool))
        rows.append((p.stem, med, darkmed, int(body.sum()), lgmed, int(logo.sum()), nblob))

    print("■ 정면 정지 칸 실측 — 모자 본체 색 / 로고 색·크기")
    for stem, med, dk, n, lgm, ln, nb in rows:
        print(f"  {stem:34s} 본체 중앙값 {tuple(med)}  어두운쪽 {tuple(dk)}  {n:4d}px"
              f"   로고 {tuple(lgm)} {ln:3d}px {nb}덩이")

    beanie = [r for r in rows if "beanie" in r[0]]
    la = [r for r in rows if "ladodgers" in r[0]]
    for name, grp in (("비니", beanie), ("LA 볼캡", la)):
        if len(grp) < 2:
            continue
        meds = np.array([r[1] for r in grp])
        lgs = np.array([r[4] for r in grp])
        lns = np.array([r[5] for r in grp])
        print(f"\n■ {name} {len(grp)}장 편차")
        # numpy 2.x 에서 ndarray.ptp() 가 없어졌다 — np.ptp() 를 쓴다
        print(f"   본체색 폭 R{np.ptp(meds[:,0])} G{np.ptp(meds[:,1])} B{np.ptp(meds[:,2])}"
              f"   (최저 {tuple(meds.min(axis=0))} ~ 최고 {tuple(meds.max(axis=0))})")
        print(f"   로고색 폭 R{np.ptp(lgs[:,0])} G{np.ptp(lgs[:,1])} B{np.ptp(lgs[:,2])}"
              f"   로고 크기 {lns.min()}~{lns.max()}px (차 {np.ptp(lns)}px)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
