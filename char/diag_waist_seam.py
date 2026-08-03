# -*- coding: utf-8 -*-
"""상의·하의 경계에서 base 살색이 비치는 자리를 잰다.

대표 증상: "후드 + 레깅스를 같이 입으면 허리에 살색이 ㅡ 모양으로 비친다."
(남캐 레드후드 + 검정 트레이닝도 같은 증상)

앱 z 순서는 body → bottom → shoes → top 이라 상의가 하의 위에 그려진다.
그러니 허리에 살색이 보인다 = **상의 밑단과 하의 허리선이 둘 다 그 줄을 안 덮는다**는 뜻이다.
어느 쪽이 모자란지는 두 레이어의 y 를 따로 재야 알 수 있다.

    python char/diag_waist_seam.py human_f top_f_hoodzip bottom_f_leggings
    python char/diag_waist_seam.py human top_redhood bottom_trainpt --row 0

노출 지도(마젠타) = char/_diag/waist_<상의>_<하의>.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ITEMS = HERE / "items"
CW, CH = 141, 224
ALPHA_BIN = 128
SKIN_R = 95
ROW_KO = ["정면", "후면", "좌", "우"]
COL_KO = ["정지", "걸음A", "걸음B"]
BASEW = {"human": "walk.png", "human_f": "walk_female.png"}
SCALE = 4


def is_skin(a: np.ndarray) -> np.ndarray:
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    return (a[:, :, 3] >= ALPHA_BIN) & (R >= SKIN_R) & (R > G + 20) & (G > B)


def load(name: str) -> np.ndarray:
    return np.asarray(Image.open(ITEMS / f"{name}.png").convert("RGBA")).astype(int)


def cell(arr: np.ndarray, r: int, c: int) -> np.ndarray:
    return arr[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]


def runs(mask_row: np.ndarray) -> list[tuple[int, int]]:
    """한 줄에서 연속 구간 [(x0, x1), ...]"""
    xs = np.nonzero(mask_row)[0]
    if not len(xs):
        return []
    out, s = [], xs[0]
    for a, b in zip(xs, xs[1:]):
        if b != a + 1:
            out.append((int(s), int(a)))
            s = b
    out.append((int(s), int(xs[-1])))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("body", choices=list(BASEW))
    ap.add_argument("top")
    ap.add_argument("bottom")
    ap.add_argument("--row", type=int, action="append")
    ap.add_argument("--minrun", type=int, default=3,
                    help="이 폭 이상 가로로 이어진 노출만 'ㅡ 선'으로 본다")
    ap.add_argument("--band", type=int, nargs=2, default=[115, 205],
                    help="허리 구간 y0 y1 — 머리·손·발 노출은 세지 않는다")
    a = ap.parse_args()
    rows = a.row if a.row else [0, 1, 2, 3]
    BY0, BY1 = a.band

    base = np.asarray(Image.open(HERE / BASEW[a.body]).convert("RGBA")).astype(int)
    top, bot = load(a.top), load(a.bottom)

    print(f"■ {a.body}: {a.top} + {a.bottom}  (z: base → 하의 → 상의)")
    tiles = []
    for r in rows:
        for c in range(3):
            b = cell(base, r, c)
            t = cell(top, r, c)[:, :, 3] >= ALPHA_BIN
            m = cell(bot, r, c)[:, :, 3] >= ALPHA_BIN
            skin = is_skin(b)
            expose = skin & ~t & ~m           # 옷이 하나도 안 덮는 base 살색
            band = np.zeros_like(expose)      # 머리·손·발은 원래 맨살이라 뺀다
            band[BY0:BY1 + 1] = True
            expose &= band

            # 상의가 있는 x 마다 상의 밑단 / 하의 허리선을 잰다
            gaps = []
            for x in range(CW):
                ty = np.nonzero(t[:, x])[0]
                my = np.nonzero(m[:, x])[0]
                if not len(ty) or not len(my):
                    continue
                hem, waist = int(ty.max()), int(my.min())
                if waist > hem + 1:            # 사이가 비었다
                    gaps.append((x, hem, waist))

            # 노출 픽셀 중 가로로 길게 이어진 줄만 추린다(ㅡ 선)
            lines = []
            for y in range(CH):
                for x0, x1 in runs(expose[y]):
                    if x1 - x0 + 1 >= a.minrun:
                        lines.append((y, x0, x1))

            head = f"   {ROW_KO[r]:2s} {COL_KO[c]:3s}"
            if not lines and not gaps:
                print(f"{head}  깨끗 ✔")
            else:
                seam = ""
                if gaps:
                    hs = [g[1] for g in gaps]
                    ws = [g[2] for g in gaps]
                    seam = (f"  틈 x{gaps[0][0]}~{gaps[-1][0]}"
                            f" 상의밑단 y{min(hs)}~{max(hs)} / 하의허리 y{min(ws)}~{max(ws)}")
                px = int(expose.sum())
                print(f"{head}  노출 {px:4d}px · ㅡ선 {len(lines)}줄{seam}")
                for y, x0, x1 in lines[:6]:
                    print(f"            y{y:3d}  x{x0:3d}~{x1:3d} ({x1 - x0 + 1}px)")
                if len(lines) > 6:
                    print(f"            … {len(lines) - 6}줄 더")

            comp = b.copy()
            for lay in (cell(bot, r, c), cell(top, r, c)):
                s = lay[:, :, 3] >= ALPHA_BIN
                comp[s] = lay[s]
                comp[s, 3] = 255
            comp[expose] = [255, 0, 255, 255]
            tiles.append((f"{ROW_KO[r]}-{COL_KO[c]}", comp[BY0:BY1 + 1]))

    CHB = BY1 - BY0 + 1
    pad, lbl = 6, 20
    rn = len(tiles) // 3
    W, H = (CW + pad) * 3 + pad, (CHB + lbl + pad) * rn + pad
    canvas = Image.new("RGB", (W, H), (250, 250, 250))
    for i, (_t, arr) in enumerate(tiles):
        rr, cc = divmod(i, 3)
        canvas.paste(Image.fromarray(arr.astype(np.uint8), "RGBA").convert("RGB"),
                     (pad + cc * (CW + pad), pad + rr * (CHB + lbl + pad) + lbl))
    big = canvas.resize((W * SCALE, H * SCALE), Image.NEAREST)
    d = ImageDraw.Draw(big)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    for i, (t, _a) in enumerate(tiles):
        rr, cc = divmod(i, 3)
        d.text(((pad + cc * (CW + pad)) * SCALE, (pad + rr * (CHB + lbl + pad)) * SCALE),
               t, fill=(20, 20, 20), font=font)
    out = HERE / "_diag" / f"waist_{a.top}_{a.bottom}.png"
    out.parent.mkdir(exist_ok=True)
    big.save(out)
    print(f"-> {out}  (마젠타 = 옷이 안 덮은 base 살색)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
