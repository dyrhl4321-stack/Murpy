# -*- coding: utf-8 -*-
"""대숲 가면 제작용 입력 시트 — 정면 캐릭터 + 가면 자리 가이드.

가면은 **대숲 전용**이고 **정면(row0)만** 필요하다(대표 확정 2026-08-04).
대표가 이 그림 위에 가면을 그리면, 내가 가면만 떼어 3열에 복제해 붙인다.

만드는 것 (각 남/여):
  1) <이름>_가이드.png  : 정면 정지 캐릭터 + 가면 자리 안내선(빨강)  ← 보고 그리는 용도
  2) <이름>_생성용.png  : 안내선 없는 정면 캐릭터, 마젠타 배경       ← AI 에 넣는 용도

    python char/build_mask_guide.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from base_regions import BROW, FACE_X, EAR_TOP_FB, ALPHA_BIN, CW, CH, largest  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ITEMS = HERE / "items"
OUT = Path(r"C:\Users\allys\Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차\대숲가면")
BG = (255, 0, 255, 255)
SCALE = 4

PAIRS = [
    ("walk.png", "hair_m_basic", "남_가면"),
    ("walk_female.png", "hair_f_long", "여_가면"),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for base_n, hair_id, label in PAIRS:
        base = np.asarray(Image.open(HERE / base_n).convert("RGBA")).astype(np.uint8)
        cell = base[0:CH, 0:CW].copy()
        hp = ITEMS / f"{hair_id}.png"
        if hp.exists():
            h = np.asarray(Image.open(hp).convert("RGBA")).astype(np.uint8)[0:CH, 0:CW]
            m = h[:, :, 3] >= ALPHA_BIN
            cell[m] = h[m]
            cell[m, 3] = 255

        # ★가면은 **눈을 덮어야** 한다. BROW(눈썹 상수)는 앞머리에 가려진 값이라 실제 눈보다
        #   훨씬 위다 — 그대로 쓰면 상자가 이마에 잡힌다(가이드 1차본에서 실제로 그랬다).
        #   그래서 base(헤어 없는 얼굴)에서 눈 픽셀을 직접 잰다.
        bb = np.asarray(Image.open(HERE / base_n).convert("RGBA")).astype(int)[0:CH, 0:CW]
        bmb = largest(bb[:, :, 3] >= ALPHA_BIN)
        topb = int(np.nonzero(bmb.any(axis=1))[0].min())
        fx0, fx1 = FACE_X[base_n]
        r_, g_, b_ = bb[:, :, 0], bb[:, :, 1], bb[:, :, 2]
        dark = bmb & (r_ < 80) & (g_ < 80) & (b_ < 80)
        dark[:topb + 30] = False          # 정수리 외곽선 제외
        dark[topb + 80:] = False          # 턱 아래 제외
        dark[:, :fx0 + 4] = False         # 얼굴 옆 외곽선 제외
        dark[:, fx1 - 3:] = False
        ys = np.nonzero(dark.any(axis=1))[0]
        if len(ys):
            eye_y0, eye_y1 = int(ys.min()), int(ys.max())
        else:                              # 못 찾으면 상수로 폴백
            eye_y0, eye_y1 = topb + BROW[base_n][0], topb + EAR_TOP_FB[base_n][0]

        bm = largest(cell[:, :, 3] >= ALPHA_BIN)
        top = int(np.nonzero(bm.any(axis=1))[0].min())
        x0, x1 = FACE_X[base_n]
        y0 = eye_y0 - 5                    # 눈 위 여유
        y1 = eye_y1 + 5                    # 눈 아래 여유

        # 생성용 (마젠타 배경, 안내선 없음)
        gen = cell.copy()
        gen[gen[:, :, 3] < ALPHA_BIN] = BG
        gen[:, :, 3] = 255
        Image.fromarray(gen, "RGBA").resize((CW * SCALE, CH * SCALE), Image.NEAREST) \
            .save(OUT / f"{label}_생성용.png")

        # 가이드 (안내선 빨강)
        gd = Image.fromarray(gen, "RGBA").resize((CW * SCALE, CH * SCALE), Image.NEAREST)
        d = ImageDraw.Draw(gd)
        d.rectangle([x0 * SCALE, y0 * SCALE, x1 * SCALE, y1 * SCALE],
                    outline=(255, 40, 40, 255), width=3)
        gd.save(OUT / f"{label}_가이드.png")

        print(f"{label}: 가면 자리 x{x0}~{x1}({x1-x0+1}px) y{y0}~{y1}({y1-y0+1}px)  "
              f"-> {label}_가이드.png / {label}_생성용.png")
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
