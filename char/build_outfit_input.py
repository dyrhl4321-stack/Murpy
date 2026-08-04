# -*- coding: utf-8 -*-
"""기본 의상(흰 티·기본 반바지·기본 샌들) 생성용 입력 시트를 만든다.

■ 왜 입력 시트를 따로 주는가
AI 에 말로만 시키면 **자기 비율로 사람을 새로 그린다.** 그러면 머리 크기가 달라져서
우리 walk.png 와 정합이 안 되고, 차분 추출(build_outfit_layer.py)이 통째로 망가진다.
그래서 **우리 base 시트 자체를 넣고 "옷만 덧입혀라"** 라고 시킨다.

■ 배경이 마젠타인 이유
제미나이/나노바나나는 투명 배경을 못 그린다(대표 확정). 형광 마젠타 단색으로 받아서
가장자리 flood fill 로 지운다. ★색 임계만으로 지우면 경계에 보라 링이 남는다.

만드는 것 (각 남/여):
  <이름>_생성용.png : base 캐릭터 3열×4행, 마젠타 배경, 4배 확대(AI 가 디테일을 그릴 여유)

    python char/build_outfit_input.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from base_regions import ALPHA_BIN, CW, CH  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
OUT = Path(r"C:\Users\allys\Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차\기본의상")
BG = (255, 0, 255, 255)
SCALE = 4

PAIRS = [("walk.png", "남_기본의상"), ("walk_female.png", "여_기본의상")]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for base_n, label in PAIRS:
        p = HERE / base_n
        if not p.exists():
            print(f"!! 없음 {base_n}")
            continue
        a = np.asarray(Image.open(p).convert("RGBA")).astype(np.uint8)
        h, w = a.shape[0], a.shape[1]
        out = a.copy()
        # 알파 이진화 후 투명부를 마젠타로 (반투명이 남으면 누끼 때 경계가 지저분해진다)
        m = out[:, :, 3] >= ALPHA_BIN
        out[~m] = BG
        out[m, 3] = 255
        img = Image.fromarray(out, "RGBA").resize((w * SCALE, h * SCALE), Image.NEAREST)
        dst = OUT / f"{label}_생성용.png"
        img.save(dst)
        print(f"{label}: {w}×{h} (칸 {CW}×{CH}, 3열×4행) -> {SCALE}배 {img.width}×{img.height}  {dst.name}")
    print(f"\n-> {OUT}")
    print("행 순서: 1=정면 2=후면 3=좌 4=우   /   열: 1=정지 2=걸음A 3=걸음B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
