# -*- coding: utf-8 -*-
"""base(walk.png / walk_female.png)에서 방향별 두상·얼굴 좌표를 실측한다.

헤어가 덮어야 할 자리를 정의하려면 '얼굴이 어디까지인가'를 알아야 한다.
★기준을 헤어 시트에서 읽으면 안 된다 — AI가 시트마다 얼굴 위치·크기를 다르게 그려서
  보호와 덮기가 정반대로 적용됐다(눈이 깨지고 귀 살색이 남았다). base는 고정 파일이므로
  좌표도 고정이고 AI 드리프트와 무관하다.

눈 = 실루엣 내부의 거의 검은 덩어리(눈썹보다 아래, 얼굴 안쪽).

    python char/measure_head.py
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
CW, CH = 141, 224
ROWNAME = ["정면", "후면", "좌", "우"]


def largest(m):
    lab, n = ndimage.label(m, np.ones((3, 3), bool))
    if n <= 1:
        return m
    s = ndimage.sum(m, lab, range(1, n + 1))
    return lab == (int(np.argmax(s)) + 1)


for f in ("walk.png", "walk_female.png"):
    a = np.asarray(Image.open(os.path.join(HERE, f)).convert("RGBA")).astype(int)
    print("■ %s" % f)
    for r in range(4):
        for c in (0,):
            cell = a[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
            sil = largest(cell[:, :, 3] >= 128)
            ys = np.where(sil.any(axis=1))[0]
            top = int(ys.min())
            inner = ndimage.binary_erosion(sil, np.ones((3, 3), bool))
            dark = inner & (cell[:, :, :3].max(axis=2) <= 70)
            # 눈: 상단 45% 안의 어두운 덩어리들 중 크기 12px 이상
            band = dark.copy(); band[top + int(CH * 0.45):] = False
            lab, n = ndimage.label(band, np.ones((3, 3), bool))
            eyes = []
            for i in range(1, n + 1):
                comp = lab == i
                if comp.sum() < 12:
                    continue
                yy, xx = np.where(comp)
                eyes.append((int(yy.min()), int(yy.max()), int(xx.min()), int(xx.max()), int(comp.sum())))
            eyes.sort(key=lambda e: -e[4])
            # 두상 폭(상단 20px)과 목 y(실루엣 폭이 최소가 되는 지점)
            wid = sil.sum(axis=1)
            neck = int(top + 55 + np.argmin(wid[top + 55:top + 100])) if top + 100 < CH else top + 80
            if eyes:
                ey0 = min(e[0] for e in eyes[:2]); ey1 = max(e[1] for e in eyes[:2])
                ex0 = min(e[2] for e in eyes[:2]); ex1 = max(e[3] for e in eyes[:2])
                print("   %-4s 두상top %3d  눈 y %3d~%-3d x %3d~%-3d (덩어리 %d개)  목 y %3d  얼굴중심x %.0f" % (
                    ROWNAME[r], top, ey0, ey1, ex0, ex1, len(eyes), neck, (ex0 + ex1) / 2))
            else:
                print("   %-4s 두상top %3d  눈 없음(후면)  목 y %3d" % (ROWNAME[r], top, neck))
    print()
