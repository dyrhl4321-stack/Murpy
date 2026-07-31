# -*- coding: utf-8 -*-
"""한 방향의 3열(정지·걸음1·걸음2) 헤어 모양이 같은지 검증한다.

헤어는 방향당 1프레임을 3열에 복제하는 구조다. 열마다 모양이 달라지면 걸을 때
머리가 깜빡이고 출렁인다(대표 증상: "왼쪽 갈 때 앞머리 구멍이 채워졌다 메꿔졌다 반복").

검증법 = 각 열의 헤어를 **bbox 로 크롭해 비트맵 비교**. 열마다 평행이동만 다르므로
위치를 빼고 모양만 본다.

    python char/verify_col_consistency.py hair_m_semileaf.png
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
CW, CH = 141, 224
ALPHA_BIN = 128
ROWS = ["정면", "후면", "좌", "우"]


def crop(m):
    if not m.any():
        return None
    ys, xs = np.where(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "hair_m_semileaf.png"
    a = np.asarray(Image.open(os.path.join(HERE, "items", name)).convert("RGBA")).astype(int)
    print(f"■ {name}")
    bad = 0
    for r in range(4):
        shapes = []
        for c in range(3):
            m = a[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW, 3] >= ALPHA_BIN
            shapes.append((int(m.sum()), crop(m)))
        ref = shapes[0][1]
        notes = []
        for c in range(1, 3):
            s = shapes[c][1]
            if ref is None or s is None:
                notes.append(f"col{c}=비어있음")
                bad += 1
            elif s.shape != ref.shape:
                notes.append(f"col{c} 크기 {s.shape[1]}x{s.shape[0]} ≠ col0 {ref.shape[1]}x{ref.shape[0]}")
                bad += 1
            else:
                d = int((s ^ ref).sum())
                if d:
                    notes.append(f"col{c} 다른 픽셀 {d}")
                    bad += 1
        px = " / ".join(str(s[0]) for s in shapes)
        print(f"  {ROWS[r]:2s}  픽셀 {px}   {'모양 일치' if not notes else ' · '.join(notes)}")
    print("\n" + ("✔ 3열 모양이 전부 같다 — 걸을 때 안 흔들린다" if not bad
                  else f"★ {bad}건 불일치 — 걸을 때 깜빡일 수 있다"))
    return bad


if __name__ == "__main__":
    sys.exit(0 if main() == 0 else 1)
