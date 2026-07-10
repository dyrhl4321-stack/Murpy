# -*- coding: utf-8 -*-
"""상의 밑단이 걸음 프레임마다 오르내리는 것을 평평하게 맞춘다.

시트가 프레임별로 따로 그려져서 밑단 y 가 몇 px 씩 다르다. 걸으면 밑단이 들썩인다.
한 방향(행)의 세 프레임 중 가장 짧은 밑단에 맞춰, 아래로 튀어나온 부분만 지운다.

지우기만 한다. 픽셀을 지어내지 않는다.

    python char/level_hem.py top_ringer --rows down up
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ROOT / "char" / "items"
FW, FH, COLS = 141, 224, 3
ROW_NAMES = ["down", "up", "left", "right"]
ROW_KO = ["아래", "위", "왼쪽", "오른쪽"]
COL_KO = ["정지", "걸음A", "걸음B"]


def level(item_id: str, rows: list[str], out: Path | None = None) -> Path:
    arr = np.asarray(Image.open(ITEMS / f"{item_id}.png").convert("RGBA")).copy()
    removed = 0

    for name in rows:
        r = ROW_NAMES.index(name)
        hems = []
        for c in range(COLS):
            m = arr[r * FH:(r + 1) * FH, c * FW:(c + 1) * FW, 3] > 128
            ys = np.nonzero(m.any(axis=1))[0]
            hems.append(int(ys.max()) if len(ys) else -1)
        target = min(h for h in hems if h >= 0)
        print(f"  {ROW_KO[r]}: 밑단 {hems} → {target}")

        for c in range(COLS):
            if hems[c] <= target:
                continue
            band = arr[r * FH + target + 1: r * FH + hems[c] + 1, c * FW:(c + 1) * FW]
            n = int((band[..., 3] > 128).sum())
            band[..., 3] = 0
            removed += n
            print(f"     {COL_KO[c]}: {hems[c] - target}줄 깎음 ({n}px)")

    dst = out or (ITEMS / f"{item_id}.png")
    Image.fromarray(arr, mode="RGBA").save(dst)
    print(f"{item_id}: 총 {removed:,}px 제거 → {dst.name}")
    return dst


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("item")
    ap.add_argument("--rows", nargs="+", default=["down", "up"], choices=ROW_NAMES)
    ap.add_argument("-o", "--out", type=Path)
    a = ap.parse_args()
    level(a.item, a.rows, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
