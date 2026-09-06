# -*- coding: utf-8 -*-
"""정면 칸에서 눈 좌표 자동 실측 (무궁화꽃 하트눈 SQ_MG_EYES 용, 2026-09-06).

돌려주는 값 = {'y': 0~1, 'x': [왼, 오른]} (정면 셀 141×224 대비 비율) 또는 None.
방법: 살색 영역 안쪽의 어두운 덩어리들 중 **좌우 한 쌍**(같은 높이, 얼굴 폭의 22~60% 간격, 중심선 대칭)을 고른다.
눈썹도 같은 조건을 만족하므로 **주변 2px 안의 흰 픽셀(흰자·하이라이트)이 있는 쌍**을 우선한다.
실측 대비 오차(9-06): 재진 0.012 · 패수현 0.020 · 기본남 0.025 · 기본여 0.019 — 하트 자리로는 충분.
"""
import numpy as np
from PIL import Image
from scipy.ndimage import label, binary_dilation

def detect(sheet_path):
    a = np.array(Image.open(sheet_path).convert('RGBA')).astype(int)[0:224, 0:141]
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]; mx = np.maximum(np.maximum(r, g), b)
    skin = (al > 128) & (r > 150) & (r > g + 20) & (g > b) & (g - b < 45)
    ys, xs = np.where(skin[30:140])
    if len(ys) < 100: return None
    fy0, fy1 = 30 + ys.min(), 30 + ys.max(); fx0, fx1 = xs.min(), xs.max(); cx = (fx0 + fx1) / 2; fw = fx1 - fx0
    if fw < 20 or fy1 - fy0 < 20: return None
    dark = (al > 128) & (mx < 95); bright = (al > 128) & (mx > 200) & (r - b < 40) & (g - b < 40)
    inside = binary_dilation(skin, iterations=2) & ~binary_dilation(~(skin | dark | bright), iterations=1)
    cand = dark & inside; cand[:fy0, :] = False; cand[fy1:, :] = False
    lab, n = label(cand, structure=np.ones((3, 3)))
    comps = []
    for k in range(1, n + 1):
        m = lab == k; yy, xx = np.where(m)
        h, w = yy.max() - yy.min() + 1, xx.max() - xx.min() + 1
        if len(yy) < 8 or w > 34 or h > 26: continue
        hl = int((bright & binary_dilation(m, iterations=2)).sum())
        comps.append(dict(n=len(yy), y=yy.mean(), x=xx.mean(), hl=hl))
    best = None
    for L in comps:
        for R in comps:
            if L['x'] >= R['x']: continue
            dx = R['x'] - L['x']
            if not (0.22 * fw < dx < 0.6 * fw) or abs(L['y'] - R['y']) > 4: continue
            rel = (L['y'] - fy0) / (fy1 - fy0)
            if not (0.15 < rel < 0.7): continue
            sc = abs(L['x'] + R['x'] - 2 * cx) - 3 * min(L['hl'], R['hl'])
            if best is None or sc < best[0]: best = (sc, L, R)
    if not best: return None
    _, L, R = best
    return {'y': round(float((L['y'] + R['y']) / 2 / 224), 3), 'x': [round(float(L['x'] / 141), 3), round(float(R['x'] / 141), 3)]}
