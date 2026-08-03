# -*- coding: utf-8 -*-
r"""AI가 다른 격자로 뱉은 시트를 앱 격자(3칸×4줄)로 되돌린다.

제미나이는 같은 프롬프트여도 배치를 마음대로 바꾼다. 실제로 나온 것:
  · 3칸×4줄 (정상)
  · 6칸×2줄 — 1줄에 정면3+후면3, 2줄에 좌3+우3  ← 남자세미리프 GBD모자
읽는 순서(왼→오, 위→아래)는 어느 배치든 정면·후면·좌·우 순으로 같으므로,
칸을 순서대로 12개 뽑아 3개씩 4줄로 다시 깔면 된다.

    python char/regrid_sheet.py "…\남자세미리프 GBD모자.png" char\_diag\norm_semileaf_beanie.png --from 6 2
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CW, CH = 141, 224


def regrid(src: Image.Image, from_cols: int, from_rows: int,
           resample=Image.Resampling.NEAREST) -> Image.Image:
    """★기본 NEAREST. 도트 시트를 LANCZOS 로 줄이면 이웃 색을 섞어 로고가 탁해지고
    배경(마젠타)이 경계에 스며 보라색 링이 남는다(실측). 정수배가 아니어도 NEAREST 가 낫다."""
    src = src.convert("RGBA")
    sw, sh = src.size
    cells = []
    for r in range(from_rows):
        for c in range(from_cols):
            box = (round(sw * c / from_cols), round(sh * r / from_rows),
                   round(sw * (c + 1) / from_cols), round(sh * (r + 1) / from_rows))
            cells.append(src.crop(box).resize((CW, CH), resample))

    if len(cells) != 12:
        raise SystemExit(f"칸이 12개가 아니다: {len(cells)}개 ({from_cols}x{from_rows})")

    out = Image.new("RGBA", (CW * 3, CH * 4), (0, 0, 0, 0))
    for i, cell in enumerate(cells):
        r, c = divmod(i, 3)
        out.alpha_composite(cell, (c * CW, r * CH))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--from", dest="frm", type=int, nargs=2, metavar=("COLS", "ROWS"),
                    required=True, help="원본 격자 (예: --from 6 2)")
    a = ap.parse_args()

    src = Image.open(a.input)
    out = regrid(src, a.frm[0], a.frm[1])
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    out.save(a.output)
    print(f"{src.size} ({a.frm[0]}x{a.frm[1]}) -> {out.size} (3x4)  {a.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
