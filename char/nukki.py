# -*- coding: utf-8 -*-
"""초록(#00FF00) 배경 크로마키 누끼 — Photoroom 대체(자체 파이프라인).

나노바나나(제미나이)는 투명 배경을 못 그려서 단색 형광초록 #00FF00 위에 뽑는다.
그 초록만 투명 처리한다. 캐릭터가 가진 초록(예: 소믈리에 나비넥타이·좀비 피부)은
'초록기'가 약해서 안 지워지도록 임계값으로 구분한다. 경계의 초록 번짐은 가장자리만 despill.

    python char/nukki.py <입력.png> [입력2.png ...] [-o 출력폴더] [--greenness N] [--gmin N]

기본 출력 = 각 입력 옆에 <이름>-nukki.png. -o 주면 그 폴더로.
방송 그린스크린과 같은 원리(초록기 = G - max(R,B)). 배경은 이 값이 255로 극단적,
캐릭터 초록(나비넥타이~86, 좀비피부~24)은 낮아서 임계값(기본 120) 사이로 가른다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def nukki(src: Path, dst: Path, greenness_bg: int, g_min: int) -> None:
    im = Image.open(src).convert("RGBA")
    arr = np.asarray(im).astype(np.int16)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    greenness = g - np.maximum(r, b)          # '초록기'
    bg = (g > g_min) & (greenness > greenness_bg)

    alpha = np.where(bg, 0, 255).astype(np.uint8)

    # 유지 픽셀 중 '투명(bg)과 붙은 가장자리'만 despill: 초록 번짐을 max(r,b) 근처로 눌러 제거
    keep = ~bg
    edge = np.zeros_like(bg)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy or dx:
                edge |= keep & np.roll(np.roll(bg, dy, 0), dx, 1)
    cap = np.maximum(r, b) + 12
    despill = edge & (g > cap)
    g2 = g.copy()
    g2[despill] = cap[despill]

    out = arr.copy()
    out[..., 1] = g2
    out[..., 3] = alpha
    Image.fromarray(out.astype(np.uint8), "RGBA").save(dst)
    print(f"  누끼 완료 (배경 {int(bg.sum()):,}px 투명) → {dst.name}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sources", nargs="+", type=Path)
    ap.add_argument("-o", "--out", type=Path, help="출력 폴더(없으면 입력 옆에 저장)")
    ap.add_argument("--greenness", type=int, default=120,
                    help="초록기(G-max(R,B))가 이보다 크면 배경. 기본 120. 캐릭터 초록이 지워지면 올리고, 배경이 남으면 내린다")
    ap.add_argument("--gmin", type=int, default=140, help="배경으로 볼 최소 G. 기본 140")
    args = ap.parse_args()

    for s in args.sources:
        print(s.name)
        dst = (args.out / f"{s.stem}-nukki.png") if args.out else s.with_name(f"{s.stem}-nukki.png")
        if args.out:
            args.out.mkdir(parents=True, exist_ok=True)
        nukki(s, dst, args.greenness, args.gmin)
    return 0


if __name__ == "__main__":
    sys.exit(main())
