# -*- coding: utf-8 -*-
"""정면 걸음이 '한 발로만 걷는' 시트를 고친다 — 딛는 발을 좌우로 뒤집어 반대 프레임을 만든다.

왜 필요한가 (돼쫀토, 2026-08-10 대표 지적)
    정면 행의 세 프레임이 col0=정지 / col1=거의 정지 / col2=오른발 듦 이었다.
    실측: col1 다리 비대칭 0.4%(=사실상 정지), col2 13.3%(=한 발 듦).
    걷는 내내 오른발만 왔다갔다 해서 절뚝이는 것처럼 보인다.

무엇을 하나
    col1 = col2 를 통째로 복사한 뒤 **허리 아래만 좌우로 뒤집는다.**
    → 몸통은 두 프레임이 완전히 같고 다리만 반대 = 제대로 번갈아 걷는다.
    정면은 좌우대칭 캐릭터라 다리를 뒤집어도 어색하지 않다(대표 판단).

    ★몸통까지 통째로 뒤집지 않는다. 몸통은 미세하게 비대칭이라(음영·나비넥타이)
      프레임마다 뒤집히면 걸을 때 깜빡이는 것처럼 보인다.
    ★이음선은 **실루엣이 완전히 대칭인 행**에서 고른다. 거기서 잘라야 자국이 안 남는다.

    python char/mirror_front_step.py char/ddungddung.png --cw 145 --row 0
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROWS, COLS = 4, 3


def pick_seam(alpha: np.ndarray, lo: int, hi: int) -> int:
    """[lo,hi) 중 좌우 실루엣이 가장 대칭인 행. 동점이면 가장 아래(=다리에 가까운 쪽)."""
    best = None
    for y in range(lo, hi):
        r = alpha[y]
        bad = int((r != r[::-1]).sum())
        if best is None or bad <= best[0]:
            best = (bad, y)
    return best[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet", type=Path)
    ap.add_argument("--cw", type=int, required=True, help="셀 가로(px)")
    ap.add_argument("--ch", type=int, default=224, help="셀 세로(px)")
    ap.add_argument("--row", type=int, default=0, help="고칠 행 (0=정면)")
    ap.add_argument("--src-col", type=int, default=2, help="딛는 발이 있는 프레임")
    ap.add_argument("--dst-col", type=int, default=1, help="여기에 반대 발을 만든다")
    args = ap.parse_args()

    im = Image.open(args.sheet).convert("RGBA")
    a = np.asarray(im).copy()
    CW, CH, R = args.cw, args.ch, args.row

    y0 = R * CH
    sx = args.src_col * CW
    dx = args.dst_col * CW
    src = a[y0:y0 + CH, sx:sx + CW].copy()

    alpha = src[..., 3] >= 40
    seam = pick_seam(alpha, int(CH * 0.60), int(CH * 0.80))
    bad = int((alpha[seam] != alpha[seam][::-1]).sum())
    print("이음선 y=%d (셀 안 기준) · 그 행 실루엣 비대칭 %dpx" % (seam, bad))
    if bad:
        print("  ! 완전 대칭인 행을 못 찾았다. 결과를 반드시 눈으로 볼 것.")

    out = src.copy()
    out[seam:] = src[seam:, ::-1]            # 허리 아래만 좌우 반전
    a[y0:y0 + CH, dx:dx + CW] = out

    Image.fromarray(a, "RGBA").save(args.sheet)

    def leg_asym(cell):
        z = cell[..., 3] >= 40
        z = z[seam:]
        t = int((z | z[:, ::-1]).sum())
        return 100 * int((z != z[:, ::-1]).sum()) / max(t, 1)

    fin = np.asarray(Image.open(args.sheet).convert("RGBA"))
    for c in range(COLS):
        cell = fin[y0:y0 + CH, c * CW:(c + 1) * CW]
        print("  col%d 다리 비대칭 %.1f%%" % (c, leg_asym(cell)))
    d = fin[y0:y0 + CH, dx:dx + CW][..., 3] != fin[y0:y0 + CH, sx:sx + CW][..., 3]
    print("  col%d vs col%d 실루엣 차이 %dpx (0 이면 걸음이 안 생긴 것)"
          % (args.dst_col, args.src_col, int(d.sum())))
    print("저장:", args.sheet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
