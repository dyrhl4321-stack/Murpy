# -*- coding: utf-8 -*-
"""마젠타 누끼 잔여 테두리 제거(despill).

nukki_solid 는 배경과 **연결된** 마젠타만 flood fill 로 지운다. 그런데 AI가 그린 경계는
완전히 하드하지 않아서, 배경색이 살짝 섞인 픽셀이 실루엣을 따라 한 겹 남는다.
그 픽셀은 배경 판정 허용오차 밖이라 살아남고, 결과적으로 캐릭터에 **분홍 테두리**가 생긴다.

색으로만 지운다 — 마젠타는 R·B 가 둘 다 G 보다 크게 높은 유일한 색이다.
  살색  : R > G > B  (B-G 가 음수라 안 걸린다)
  갈색머리: R > G > B  (같은 이유)
  검정외곽선: R≈G≈B   (차이가 없어 안 걸린다)
그래서 이 조건은 캐릭터 색을 건드리지 않는다.

    python char/despill_magenta.py <시트.png> [--apply] [--t 50]
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ALPHA_BIN = 128


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--t", type=int, default=50, help="마젠타 판정 임계 (R-G, B-G 둘 다 이상)")
    a = ap.parse_args()

    im = Image.open(a.src).convert("RGBA")
    arr = np.asarray(im).astype(int)
    r, g, b, al = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]

    vis = al >= ALPHA_BIN
    mag = vis & (r - g >= a.t) & (b - g >= a.t)
    print(f"{a.src.name}  {im.width}×{im.height}")
    print(f"  보이는 픽셀 {int(vis.sum()):,} 중 마젠타 잔여 {int(mag.sum()):,}px "
          f"({mag.sum() / max(1, vis.sum()) * 100:.2f}%)")
    if not mag.any():
        print("  잔여 없음")
        return 0
    if not a.apply:
        print("  --apply 를 붙이면 제거")
        return 0

    bak = a.src.with_name(a.src.stem + "_despill백업.png")
    if not bak.exists():
        shutil.copy2(a.src, bak)
    out = arr.copy()
    out[mag] = 0                       # 통째로 투명 — 이 픽셀은 배경 잔재지 캐릭터가 아니다
    out[..., 3] = np.where(out[..., 3] >= ALPHA_BIN, 255, 0)   # 앱 하드룰: 알파 128 이진화
    Image.fromarray(out.astype(np.uint8), "RGBA").save(a.src)
    print(f"  제거 완료 (백업 {bak.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
