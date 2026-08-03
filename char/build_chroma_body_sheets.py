# -*- coding: utf-8 -*-
r"""모자 생성용 입력 시트를 만든다 — **목 아래 몸만 형광 초록**으로 칠한 버전.

★왜 (2026-08-03)
조합 시트에서 머리·모자를 오려내려다 계속 실패했다. 이유는 규칙 문제가 아니라 원리 문제다.
Smith & Blinn, "Blue Screen Matting"(SIGGRAPH 1996)의 결론:
  **배경을 정확히 알아도 알파를 뽑는 것은 under-constrained problem 이다.**
검은 머리카락이 base 의 검은 외곽선 위에 얹히면 두 색이 같아 정보가 없다. 못 푼다.
해법은 전경과 배경의 색을 **애초에 갈라놓는 것**(크로마키)이다.

그래서 AI 에 넣는 입력의 **몸을 형광 초록**으로 칠한다. 결과에서 초록을 지우면
몸 위로 흐르는 머리카락만 정확히 남는다. AI 가 몸을 다시 그려도 어차피 버리니 무관하다.

★얼굴·두상은 건드리지 않는다. 얼굴을 초록으로 만들면 제미나이가 사람 얼굴로 되돌릴
  위험이 크다(대표 지적). 목 위는 '통째로 가져오기'가 이미 처리하므로 초록이 필요 없다.

    python char/build_chroma_body_sheets.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from base_regions import neck_end  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ITEMS = HERE / "items"
OUT = Path(r"C:\Users\allys\Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차"
           r"\헤어\_모자생성용_헤어착용시트_초록몸")
CW, CH = 141, 224
ALPHA_BIN = 128
BG = np.array([255, 0, 255, 255], np.uint8)        # 배경 = 형광 마젠타 (기존과 동일)
CHROMA = np.array([0, 255, 0, 255], np.uint8)      # 몸 = 형광 초록
NECK_PAD = 3        # 목(실루엣이 가장 좁아지는 줄) 아래로 이만큼 더 내려서 칠한다

PAIRS = [
    ("walk.png", "hair_m_basic", "남_기본헤어"),
    ("walk.png", "hair_ivyleague", "남_아이비리그컷"),
    ("walk.png", "hair_m_semileaf", "남_세미리프컷"),
    ("walk_female.png", "hair_f_basic", "여_기본헤어"),
    ("walk_female.png", "hair_f_bob_bang", "여_앞머리단발"),
    ("walk_female.png", "hair_f_long", "여_긴생머리"),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for base_n, hair_id, label in PAIRS:
        bp, hp = HERE / base_n, ITEMS / f"{hair_id}.png"
        if not (bp.exists() and hp.exists()):
            print(f"!! 없음 {label}")
            continue
        b = np.asarray(Image.open(bp).convert("RGBA")).astype(np.uint8)
        h = np.asarray(Image.open(hp).convert("RGBA")).astype(np.uint8)
        out = b.copy()

        painted = 0
        for r in range(4):
            for c in range(3):
                ys, xs = slice(r * CH, (r + 1) * CH), slice(c * CW, (c + 1) * CW)
                cell = out[ys, xs]
                hair = h[ys, xs]
                ba = cell[:, :, 3] >= ALPHA_BIN
                bys = np.nonzero(ba.any(axis=1))[0]
                if not len(bys):
                    continue
                # ★목 위치는 고정 오프셋으로 잡으면 안 된다 — 80 으로 했더니 턱·입까지
                #   초록이 되어 '초록 마스크 쓴 얼굴'이 됐다. 실루엣이 가장 좁아지는 줄을 찾는다.
                neck = neck_end(ba, int(bys.min())) + NECK_PAD
                body = np.zeros(ba.shape, bool)
                body[neck:] = True
                # 몸을 초록으로. ★헤어가 덮는 자리는 빼야 한다 — 긴 머리가 몸 위로 흐르는
                #   부분까지 초록으로 칠하면 AI 가 그 머리를 잃는다.
                ha = hair[:, :, 3] >= ALPHA_BIN
                m = ba & body & ~ha
                cell[m] = CHROMA
                painted += int(m.sum())
                # 헤어를 얹는다 (기존 입력 시트와 동일)
                cell[ha] = hair[ha]
                cell[ha, 3] = 255

        out[out[:, :, 3] < ALPHA_BIN] = BG
        out[:, :, 3] = 255
        p = OUT / f"{label}.png"
        Image.fromarray(out, "RGBA").save(p)
        print(f"{label:16s} 몸 {painted:6,}px 초록  -> {p.name}")
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
