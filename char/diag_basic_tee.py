# -*- coding: utf-8 -*-
"""기본 흰티 원본이 우리 base 와 정합되는지 **실측**한다.

차분 추출은 몸이 base 와 같은 자리에 있어야만 성립한다. 눈으로 비슷해 보여도
머리 크기가 몇 px 다르면 옷만 떼어낼 수가 없다. 그래서 먼저 잰다.

★배경 제거를 **리사이즈 전에** 한다. 이 시트는 알파가 전부 255 이고 체크무늬가
  그려져 있는데, 체크무늬 흰색이 흰 티 색과 같아서 색 임계로는 못 지운다.
  가장자리에서 flood fill 로만 안전하다.

    python char/diag_basic_tee.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from base_regions import ALPHA_BIN, CW, CH  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
D = Path(r"C:\Users\allys\Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차\상의")
SRC = [("남", D / "남자 기본흰티.png", "walk.png"),
       ("여", D / "여캐" / "여자 기본흰티.png", "walk_female.png")]


def strip_checker(a: np.ndarray) -> np.ndarray:
    """가장자리에 연결된 '중성 회색/흰색'을 지운다. 캐릭터는 어두운 외곽선으로 닫혀 있어
    안쪽 흰 셔츠까지는 안 번진다 — 번지면 외곽선에 틈이 있다는 뜻이라 그때 알 수 있다."""
    r, g, b = a[:, :, 0].astype(int), a[:, :, 1].astype(int), a[:, :, 2].astype(int)
    neutral = (np.max(a[:, :, :3], axis=2).astype(int) - np.min(a[:, :, :3], axis=2).astype(int) <= 10) \
        & (np.min(a[:, :, :3], axis=2) >= 145)
    lab, _ = ndimage.label(neutral)
    edge = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
    edge.discard(0)
    bg = np.isin(lab, list(edge))
    out = a.copy()
    out[bg] = [0, 0, 0, 0]
    return out


def cells(a: np.ndarray, cw: float, ch: float):
    for r in range(4):
        for c in range(3):
            y0, y1 = int(round(r * ch)), int(round((r + 1) * ch))
            x0, x1 = int(round(c * cw)), int(round((c + 1) * cw))
            yield r, c, a[y0:y1, x0:x1]


def bbox(cell: np.ndarray):
    m = cell[:, :, 3] >= ALPHA_BIN
    if not m.any():
        return None
    ys, xs = np.nonzero(m)
    return xs.min(), xs.max(), ys.min(), ys.max()


def main() -> int:
    for tag, p, base_n in SRC:
        if not p.exists():
            print(f"!! 없음 {p}")
            continue
        raw = np.asarray(Image.open(p).convert("RGBA")).astype(np.uint8)
        H, W = raw.shape[0], raw.shape[1]
        clean = strip_checker(raw)
        kept = int((clean[:, :, 3] >= ALPHA_BIN).sum())
        print(f"\n■ {tag}  원본 {W}×{H}  배경제거 후 남은 픽셀 {kept:,} "
              f"({kept / (W * H) * 100:.1f}%)")

        base = np.asarray(Image.open(HERE / base_n).convert("RGBA")).astype(np.uint8)
        bw, bh = CW, CH
        sw, sh = W / 3, H / 4
        print(f"   셀 크기  원본 {sw:.1f}×{sh:.1f}   base {bw}×{bh}   배율 {sw/bw:.3f}×{sh/bh:.3f}")
        print("   col row |      원본 캐릭터 bbox(셀기준)      |   base 를 같은 배율로 환산")
        for (r, c, cell), (_, _, bcell) in zip(cells(clean, sw, sh), cells(base, bw, bh)):
            a1, b1 = bbox(cell), bbox(bcell)
            if not a1 or not b1:
                continue
            # base bbox 를 원본 스케일로 올려서 비교 (몇 px 어긋나는지)
            k = sw / bw
            exp = tuple(round(v * k) for v in b1)
            d = tuple(a1[i] - exp[i] for i in range(4))
            flag = "  <-- 어긋남" if max(abs(x) for x in d) > 6 else ""
            print(f"   r{r} c{c} | x{a1[0]:4d}~{a1[1]:4d} y{a1[2]:4d}~{a1[3]:4d} | "
                  f"기대 x{exp[0]:4d}~{exp[1]:4d} y{exp[2]:4d}~{exp[3]:4d}  차 {d}{flag}")
    print("\n※ 차가 ±6px(원본 기준) 안이면 차분 추출 가능. 그보다 크면 AI 가 몸을 다시 그린 것이다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
