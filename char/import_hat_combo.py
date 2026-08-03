# -*- coding: utf-8 -*-
r"""대표가 제미나이로 뽑은 모자 조합 시트를 앱 규격으로 되돌린다.

대표 확정 방침(2026-08-03): **생성형 AI 조합 시트가 기본**이고, 내가 하는 일은
받은 시트를 앱에 넣을 수 있게 정리하고 **모자 디자인을 마스터 하나로 통일**하는 것이다.
(귀 앞/뒤 자동 분할은 대표가 기각했다 — 다시 만들지 말 것.)

이 스크립트는 그 첫 단계 = 규격 복원.
  1. 격자 정규화 — 제미나이는 1408×2982 로 뱉고, 배치도 6칸×2줄로 바꿔버릴 때가 있다
  2. 마젠타 배경 제거 → 투명
  3. base(walk.png) 대비 diff → 헤어+모자 레이어만 남긴다 (몸·얼굴 제외)

    python char/import_hat_combo.py            # 폴더 전체
    python char/import_hat_combo.py --only 남자기본헤어비니
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from regrid_sheet import regrid  # noqa: E402
from base_regions import regions  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
SRC = Path(r"C:\Users\allys\Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차\모자\모자 AI테스트")
OUT = HERE / "_combo"
CW, CH = 141, 224
ALPHA_BIN = 128

# 파일명 → (base 시트, 원본 헤어 아이템). 대표 파일명이 자유라 여기서 이어준다.
MAP = {
    "남자기본헤어비니": ("walk.png", "hair_m_basic", "hat_beanie"),
    "남자기본헤어LA모자": ("walk.png", "hair_m_basic", "hat_ladodgers"),
    "남자아이비리그헤어비니": ("walk.png", "hair_ivyleague", "hat_beanie"),
    "남자아이비그LA모자": ("walk.png", "hair_ivyleague", "hat_ladodgers"),
    "남자세미리프 GBD모자": ("walk.png", "hair_m_semileaf", "hat_beanie"),
    "남자세미리프LA모자": ("walk.png", "hair_m_semileaf", "hat_ladodgers"),
    "여자기본헤어비니": ("walk_female.png", "hair_f_basic", "hat_f_beanie"),
    "여자앞머리헤어비니": ("walk_female.png", "hair_f_bob_bang", "hat_f_beanie"),
    "여자롱헤어비니": ("walk_female.png", "hair_f_long", "hat_f_beanie"),
    "여자기본헤어LA모자": ("walk_female.png", "hair_f_basic", "hat_f_ladodgers"),
    "여자앞머리헤어LA모자": ("walk_female.png", "hair_f_bob_bang", "hat_f_ladodgers"),
    "여자롱헤어모자": ("walk_female.png", "hair_f_long", "hat_f_ladodgers"),
}


def strip_magenta(im: Image.Image) -> Image.Image:
    """형광 마젠타 배경을 **가장자리에서 번져 들어가며** 지운다.

    ★색 임계만으로는 안 된다 — AI 원본은 이미 경계가 마젠타와 섞여 있어서(안티에일리어싱)
      임계를 좁히면 보라색 링이 남고, 넓히면 캐릭터 색까지 먹는다(둘 다 실측).
      배경은 가장자리에 연결돼 있으므로 flood fill 이면 느슨한 임계를 써도 안전하다.
      캐릭터 안쪽은 검은 외곽선에 막혀 물이 못 들어간다.
    ★반드시 **리사이즈 전에** 부른다.
    """
    a = np.asarray(im.convert("RGBA")).astype(int)
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    # ★밝기 조건을 걸면 안 된다 — 경계의 '어두운 보라'(마젠타가 검은 외곽선과 섞인 것)를
    #   놓쳐 링이 남는다. 색조만 본다: 살색은 B-G 가 음수, 검은 외곽선은 R-G≈0 이라 안 걸린다.
    magish = (R - G > 15) & (B - G > 15)
    seed = np.zeros(magish.shape, bool)
    seed[0, :] = seed[-1, :] = True
    seed[:, 0] = seed[:, -1] = True
    seed &= magish
    lab, _ = ndimage.label(magish, np.ones((3, 3), bool))
    keep = set(np.unique(lab[seed])) - {0}
    bg = np.isin(lab, list(keep)) if keep else np.zeros_like(magish)

    out = a.copy().astype(np.uint8)
    out[bg] = [0, 0, 0, 0]
    return Image.fromarray(out, "RGBA")


def to_app_grid(p: Path) -> Image.Image:
    """어떤 크기·배치로 와도 423×896 (3칸×4줄) 로 되돌린다."""
    im = strip_magenta(Image.open(p))
    w, h = im.size
    if abs(w / h - (CW * 3) / (CH * 4)) < 0.08:        # 세로형 = 이미 3×4
        return regrid(im, 3, 4)
    return regrid(im, 6, 2)                            # 가로형 = 6칸×2줄


def binarize(a: np.ndarray) -> np.ndarray:
    """알파 128 이진화 — 앱 하드룰. 축소 보간이 만든 반투명을 없앤다."""
    out = a.copy()
    out[out[:, :, 3] < ALPHA_BIN] = [0, 0, 0, 0]
    out[out[:, :, 3] >= ALPHA_BIN, 3] = 255
    return out


def largest_blobs(m: np.ndarray, keep: int = 40) -> np.ndarray:
    """40px 미만 고립 조각 제거 — 몸통 윤곽 드리프트가 점처럼 흩어져 남는다."""
    lab, n = ndimage.label(m, np.ones((3, 3), bool))
    if n <= 1:
        return m
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    out = m.copy()
    for i, s in enumerate(sizes, start=1):
        if s < keep:
            out[lab == i] = False
    return out


HAT_BAND = 58        # 머리 최상단부터 이 높이까지는 모자 구간 — 얼굴 보호를 적용하지 않는다


def head_layer(sheet: np.ndarray, base: np.ndarray, base_name: str) -> np.ndarray:
    """base 와 다른 픽셀 = 머리 + 모자. 몸·얼굴은 base 가 그대로 그린다."""
    out = np.zeros_like(sheet)
    for r in range(4):
        for c in range(3):
            ys, xs = slice(r * CH, (r + 1) * CH), slice(c * CW, (c + 1) * CW)
            s, b = sheet[ys, xs], base[ys, xs]
            sa = s[:, :, 3] >= ALPHA_BIN
            ba = b[:, :, 3] >= ALPHA_BIN
            diff = np.abs(s[:, :, :3].astype(int) - b[:, :, :3].astype(int)).max(axis=2)
            m = sa & (~ba | (diff > 24))
            # ★머리 길이로 자르지 않는다 — 긴 생머리는 허리까지 내려온다(+120 으로 잘랐다가
            #   정면에서 긴 머리가 통째로 없어졌다). 대신 몸통 AI 드리프트는 아래에서 거른다.
            # 몸통에서 base 와 살짝 어긋난 윤곽선이 '머리'로 잡히는 것을 막는다:
            # base 실루엣 안쪽이면서 base 와 밝기가 비슷한 픽셀은 버린다.
            inside = ba & ndimage.binary_erosion(ba, np.ones((3, 3), bool))
            lum_s = s[:, :, :3].astype(int).mean(axis=2)
            lum_b = b[:, :, :3].astype(int).mean(axis=2)
            m &= ~(inside & (np.abs(lum_s - lum_b) < 60))

            # ★얼굴·귀(base_regions 의 KEEP)에 남은 AI 드리프트 조각을 걷어낸다.
            #   세미리프 시트에서 눈 옆에 흰 픽셀·살색 조각이 남아 앱에서 얼굴 위에 겹친다.
            #   ★단 모자 구간은 예외 — 모자 밑단이 눈썹 근처까지 내려와서(실측 y65 vs 눈썹 y64)
            #     그대로 걸면 모자 밑단이 깎인다.
            _must, keep = regions(b.astype(int), r, base_name, c)
            bys = np.nonzero(ba.any(axis=1))[0]
            band = np.zeros_like(m)
            if len(bys):
                band[int(bys.min()):int(bys.min()) + HAT_BAND] = True
            m &= ~(keep & ~band)

            m = ndimage.binary_opening(m, np.ones((2, 2), bool)) | (
                m & ndimage.binary_dilation(m, np.ones((3, 3), bool)))
            m = largest_blobs(m)
            cell = np.zeros_like(s)
            cell[m] = s[m]
            out[ys, xs] = cell
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    for p in sorted(SRC.glob("*.png")):
        stem = p.stem
        if a.only and a.only not in stem:
            continue
        if stem not in MAP:
            print(f"!! 이름 매핑 없음: {stem} — MAP 에 추가해야 한다")
            continue
        base_n, hair_id, hat_id = MAP[stem]
        grid = binarize(np.asarray(to_app_grid(p)).astype(np.uint8))
        base = np.asarray(Image.open(HERE / base_n).convert("RGBA")).astype(np.uint8)
        layer = head_layer(grid, base, base_n)

        Image.fromarray(grid, "RGBA").save(OUT / f"{hair_id}__{hat_id}_full.png")
        Image.fromarray(layer, "RGBA").save(OUT / f"{hair_id}__{hat_id}.png")
        n = int((layer[:, :, 3] >= ALPHA_BIN).sum())
        print(f"{stem:24s} -> {hair_id}__{hat_id}.png   레이어 {n:6,}px")
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
