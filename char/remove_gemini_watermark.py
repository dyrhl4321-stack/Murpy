# -*- coding: utf-8 -*-
"""제미나이 워터마크(✦) 제거 — 도너 프레임 이식 방식.

누끼 **전** 원본 시트(1408x3008, 3열x4행)에 쓴다.
✦ 는 항상 우하단 = "오른쪽·걸음B" 프레임에 찍힌다.

없는 픽셀을 지어내지 않는다. 같은 시트의 다른 프레임 중 그 자리가 가장 잘 맞는
프레임을 찾아 정합한 뒤, 마스크 안쪽만 통째로 옮겨 심는다.

고전 인페인트(OpenCV Telea)는 쓰지 않는다. 마스크 경계에 검은 테두리가 닿아 있어
그 검정을 안쪽으로 전파해 별 모양 얼룩을 만든다 (실측 확인).

    python char/remove_gemini_watermark.py <원본.png> [-o 출력폴더]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):       # 콘솔이 cp949 여도 한글/기호 출력
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SHEET = (1408, 3008)
COLS, ROWS = 3, 4

# ✦ 중심과 반지름 (1408x3008 시트 기준, 실측)
WM_CX, WM_CY, WM_HW, WM_HH = 1169, 2764, 52, 54

RING_PAD = 26          # 정합 품질을 재는 바깥 띠 두께
SEARCH = 18            # 정합 탐색 반경(px)
PRESENT_RATIO = 2.0    # 안쪽MAE / 띠MAE 가 이 값을 넘으면 워터마크 있음
PRESENT_INNER = 18.0
DONOR_MAX_RING = 20.0  # 띠 MAE 가 이보다 크면 믿을 만한 도너가 없다


def _frame(im: np.ndarray, r: int, c: int) -> np.ndarray:
    fh, fw = im.shape[0] // ROWS, im.shape[1] // COLS
    return im[r * fh:(r + 1) * fh, c * fw:(c + 1) * fw]


def _masks(fh: int, fw: int, cx: int, cy: int):
    Y, X = np.mgrid[0:fh, 0:fw]
    r = np.abs(X - cx) / WM_HW + np.abs(Y - cy) / WM_HH
    wm = r <= 1.0
    ring = (np.abs(X - cx) / (WM_HW + RING_PAD) + np.abs(Y - cy) / (WM_HH + RING_PAD) <= 1.0) & ~wm
    return wm, ring


def _best_donor(target: np.ndarray, donors: dict[str, np.ndarray], ring: np.ndarray):
    best = None
    for name, d in donors.items():
        for dy in range(-SEARCH, SEARCH + 1, 2):
            for dx in range(-SEARCH, SEARCH + 1, 2):
                shifted = np.roll(np.roll(d, dy, axis=0), dx, axis=1)
                mae = float(np.abs(shifted[ring] - target[ring]).mean())
                if best is None or mae < best[0]:
                    best = (mae, name, dx, dy)
    mae, name, dx, dy = best
    for ddy in range(dy - 2, dy + 3):          # 1px 정밀 탐색
        for ddx in range(dx - 2, dx + 3):
            shifted = np.roll(np.roll(donors[name], ddy, axis=0), ddx, axis=1)
            m = float(np.abs(shifted[ring] - target[ring]).mean())
            if m < mae:
                mae, dx, dy = m, ddx, ddy
    return mae, name, dx, dy


def remove(src: Path, out_dir: Path, force: bool = False) -> Path | None:
    # force=True: 판정(present/도너품질) 검사를 건너뛰고, 정합된 최적 도너를 무조건 이식한다.
    # 흐린 배경(흰 셔츠) 위 워터마크가 임계값 미달로 안 잡히거나, 프레임 차이로 띠MAE가
    # 큰(헝클어진 머리 등) 경우용. 도너 정합 자체는 그대로라 '없는 픽셀 지어내기'는 아니다.
    # 반드시 결과를 눈으로 검증할 것.
    img = Image.open(src)
    if img.size != SHEET:
        print(f"  건너뜀 — 크기 {img.size}, 기대 {SHEET}")
        return None

    rgba = np.asarray(img.convert("RGBA"))
    rgb = rgba[..., :3].astype(int)
    fh, fw = SHEET[1] // ROWS, SHEET[0] // COLS

    target = _frame(rgb, 3, 2)
    cx, cy = WM_CX - 2 * fw, WM_CY - 3 * fh
    wm, ring = _masks(fh, fw, cx, cy)

    donors = {
        "right·idle": _frame(rgb, 3, 0),
        "right·walk1": _frame(rgb, 3, 1),
        "left·walk2(미러)": _frame(rgb, 2, 2)[:, ::-1],
        "left·idle(미러)": _frame(rgb, 2, 0)[:, ::-1],
    }
    ring_mae, name, dx, dy = _best_donor(target, donors, ring)
    donor = np.roll(np.roll(donors[name], dy, axis=0), dx, axis=1)
    inner_mae = float(np.abs(donor[wm] - target[wm]).mean())
    ratio = inner_mae / max(ring_mae, 1e-6)

    print(f"  도너 {name}  이동({dx:+d},{dy:+d})  띠MAE {ring_mae:.2f}  안쪽MAE {inner_mae:.2f}  비율 {ratio:.2f}")

    if force:
        print("  --force: 판정 건너뛰고 최적 도너 이식 (결과 눈으로 검증 필수)")
    else:
        # 도너가 안 맞으면 워터마크 유무 자체를 판정할 수 없다. 이 검사가 먼저다.
        if ring_mae > DONOR_MAX_RING:
            print(f"  중단 - 띠MAE {ring_mae:.2f} > {DONOR_MAX_RING}. 도너가 대상 프레임과 안 맞음")
            print("         (프레임끼리 그림이 다를 수 있음. 워터마크 유무는 판정 불가. 사람이 볼 것)")
            return None
        if not (ratio > PRESENT_RATIO and inner_mae > PRESENT_INNER):
            print("  워터마크 없음 - 원본 유지")
            return None

    fixed = target.copy()
    fixed[wm] = donor[wm]
    out = rgb.copy()
    out[3 * fh:4 * fh, 2 * fw:3 * fw] = fixed

    result = rgba.copy()
    result[..., :3] = out.astype(np.uint8)   # 알파는 원본 그대로

    changed = int((np.abs(rgb - out).sum(-1) > 0).sum())
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / f"{src.stem}_clean.png"
    Image.fromarray(result, mode="RGBA").save(dst)
    print(f"  바뀐 픽셀 {changed:,}개 (우하단 프레임 안) → {dst.name}")
    return dst


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sources", nargs="+", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("-f", "--force", action="store_true",
                    help="판정 건너뛰고 최적 도너 무조건 이식(흐린 배경/머리 흔들림용). 눈검증 필수")
    args = ap.parse_args()

    made = 0
    for s in args.sources:
        print(f"{s.name}")
        if remove(s, args.out, force=args.force):
            made += 1
    print(f"\n{made}장 처리됨")
    return 0


if __name__ == "__main__":
    sys.exit(main())
