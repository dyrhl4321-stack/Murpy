# -*- coding: utf-8 -*-
"""대숲 가면 PNG → 앱 아이템 시트(423×896)로 만든다.

대표가 **가면만** 마젠타 배경에 뽑아 준다(캐릭터에 씌워 뽑으면 AI 가 얼굴을 다시 그린다).
여기서 누끼 → 크기 맞춤 → **정면 행(row0) 3열**에 얼굴 위치로 얹는다.
대숲은 정지 프레임만 보이지만, 걸음 프레임도 정면이라 3열 다 채워야 안 깜빡인다.

★가면은 대숲 전용이다. 옷장/상점에 노출하지 않는다(카탈로그 등록 시 슬롯 분리).

    python char/build_mask_item.py "…\대숲가면\대숲가면.png" mask_basic
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from base_regions import FACE_X, ALPHA_BIN, CW, CH, largest  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ITEMS = HERE / "items"
BODIES = {"human": "walk.png", "human_f": "walk_female.png"}


def strip_magenta(im: Image.Image) -> np.ndarray:
    """마젠타를 지운다. ★눈 구멍 안쪽도 마젠타라 색 판정으로 지워야 구멍이 뚫린다
    (가장자리 flood fill 로 하면 구멍이 안 뚫린다)."""
    a = np.asarray(im.convert("RGBA")).astype(int)
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    mag = (R - G > 40) & (B - G > 40)
    out = a.copy().astype(np.uint8)
    out[mag] = [0, 0, 0, 0]
    out[out[:, :, 3] < ALPHA_BIN] = [0, 0, 0, 0]
    out[out[:, :, 3] >= ALPHA_BIN, 3] = 255
    return out


def trim(a: np.ndarray) -> np.ndarray:
    m = a[:, :, 3] >= ALPHA_BIN
    ys, xs = np.nonzero(m)
    if not len(ys):
        raise SystemExit("가면 픽셀이 없다 — 마젠타 판정이 너무 셌을 수 있다")
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def eye_center(base_cell: np.ndarray, base_name: str) -> tuple[int, int]:
    """이 칸의 눈 중심(x, y). 가면을 여기 맞춘다."""
    bm = largest(base_cell[:, :, 3] >= ALPHA_BIN)
    top = int(np.nonzero(bm.any(axis=1))[0].min())
    fx0, fx1 = FACE_X[base_name]
    r, g, b = base_cell[:, :, 0], base_cell[:, :, 1], base_cell[:, :, 2]
    dark = bm & (r < 80) & (g < 80) & (b < 80)
    dark[:top + 30] = False
    dark[top + 80:] = False
    dark[:, :fx0 + 4] = False
    dark[:, fx1 - 3:] = False
    ys, xs = np.nonzero(dark)
    if not len(ys):
        return (fx0 + fx1) // 2, top + 70
    return int(round(xs.mean())), (int(ys.min()) + int(ys.max())) // 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("item_id")
    ap.add_argument("--h", type=int, default=0, help="가면 높이(px). 0=자동(눈 높이+여유)")
    a = ap.parse_args()

    mask = trim(strip_magenta(Image.open(a.src)))
    mh, mw = mask.shape[0], mask.shape[1]
    print(f"가면 원본(트림) {mw}×{mh}  비율 {mw/mh:.2f}")

    for body, base_n in BODIES.items():
        base = np.asarray(Image.open(HERE / base_n).convert("RGBA")).astype(int)
        out = np.zeros((CH * 4, CW * 3, 4), np.uint8)
        for c in range(3):
            cell = base[0:CH, c * CW:(c + 1) * CW]
            cx, cy = eye_center(cell, base_n)
            # 높이는 눈 높이에 여유를 준 값. 폭은 원본 비율 유지(가로로 늘리면 왜곡된다)
            fx0, fx1 = FACE_X[base_n]
            h = a.h or 30
            w = max(8, int(round(h * mw / mh)))
            # 얼굴 폭을 넘으면 얼굴 폭에 맞춘다
            if w > (fx1 - fx0 + 6):
                w = fx1 - fx0 + 6
                h = max(6, int(round(w * mh / mw)))
            m = np.asarray(Image.fromarray(mask, "RGBA").resize((w, h), Image.NEAREST)).astype(np.uint8)
            x0, y0 = cx - w // 2, cy - h // 2
            x0 = max(0, min(CW - w, x0)); y0 = max(0, min(CH - h, y0))
            dst = out[y0:y0 + h, c * CW + x0:c * CW + x0 + w]
            sel = m[:, :, 3] >= ALPHA_BIN
            dst[sel] = m[sel]
            if c == 0:
                print(f"  {body}: 눈중심({cx},{cy})  가면 {w}×{h}  좌상단({x0},{y0})")
        p = ITEMS / f"{a.item_id}{'_f' if body == 'human_f' else ''}.png"
        Image.fromarray(out, "RGBA").save(p)
        print(f"  -> {p.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
