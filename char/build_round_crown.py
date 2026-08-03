# -*- coding: utf-8 -*-
"""정수리를 둥글게 깎은 **생성 입력용** base 를 만든다 (모자 생성 전용).

■ 왜
base 두상 정수리가 실제로 평평하다 — 맨 윗줄 폭이 남 43px / 여 41px 이고 4줄 내내 그대로다
(둥근 머리면 2~6px). 나노바나나에 이 그림을 넣으면 **모자도 그 평평함을 그대로 복사**한다.
실측: 비니 맨 윗줄 45px(평평), 볼캡 4px(챙 구조라 우연히 둥글게 나옴).

■ 무엇을 바꾸고 무엇을 안 바꾸나
- `char/walk.png` (앱이 그리는 base) = **절대 안 바뀐다.** 추출 기준도 그대로다.
- 이 스크립트가 만드는 `walk_round.png` 는 **AI 에게 보여줄 입력 이미지**일 뿐이다.
  앱에 등록하지 않는다.

■ 어떻게
두상 최상단 몇 줄을 좌우에서 계단식으로 깎아 둥근 실루엣을 만들고, 새로 생긴 경계에는
원래 정수리 외곽선 색을 칠한다. 색을 지어내지 않는다.

    python char/build_round_crown.py
    python char/build_round_crown.py --cut 10,6,4,2,1
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
CW, CH = 141, 224
ALPHA_BIN = 128
ROWS = ["정면", "후면", "좌", "우"]
DEFAULT_CUT = [9, 6, 4, 2, 1]      # 맨 윗줄부터 좌우에서 깎을 px


def outline_color(cell, m, top):
    """정수리 외곽선 색 — 최상단 2줄의 어두운 픽셀 평균."""
    band = np.zeros_like(m)
    band[top:top + 2] = True
    px = cell[m & band]
    if not len(px):
        return np.array([26, 22, 30, 255])
    dark = px[px[:, :3].mean(axis=1) < 120]
    src = dark if len(dark) else px
    return np.concatenate([src[:, :3].mean(axis=0).round(), [255]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cut", default=",".join(map(str, DEFAULT_CUT)))
    args = ap.parse_args()
    cut = [int(x) for x in args.cut.split(",")]

    for name in ["walk.png", "walk_female.png"]:
        p = os.path.join(HERE, name)
        if not os.path.exists(p):
            continue
        a = np.asarray(Image.open(p).convert("RGBA")).astype(int)
        out = a.copy()
        print(f"\n■ {name}")
        for r in range(4):
            for c in range(3):
                cell = out[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
                m = cell[:, :, 3] >= ALPHA_BIN
                if not m.any():
                    continue
                top = int(np.where(m.any(axis=1))[0].min())
                oc = outline_color(cell, m, top)
                for d, k in enumerate(cut):
                    y = top + d
                    if y >= CH or not m[y].any() or k <= 0:
                        continue
                    xs = np.where(m[y])[0]
                    x0, x1 = int(xs.min()), int(xs.max())
                    # 좌우에서 k px 깎는다
                    cell[y, x0:x0 + k] = 0
                    cell[y, x1 - k + 1:x1 + 1] = 0
                    # 새 경계에 외곽선 색
                    nl, nr = x0 + k, x1 - k
                    if nl <= nr:
                        cell[y, nl] = oc
                        cell[y, nr] = oc
                if r == 0 and c == 0:
                    m2 = cell[:, :, 3] >= ALPHA_BIN
                    w = [int(m2[top + d].sum()) for d in range(6) if top + d < CH]
                    print(f"   {ROWS[r]} col{c}  맨윗줄 폭 변화 {w}")
        q = os.path.join(HERE, name.replace(".png", "_round.png"))
        Image.fromarray(out.astype(np.uint8), "RGBA").save(q)
        print(f"   -> {q}  (생성 입력 전용 · 앱에 등록하지 않음)")


if __name__ == "__main__":
    main()
