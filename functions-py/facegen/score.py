# -*- coding: utf-8 -*-
"""생성 결과 자동 채점 — tools/face_backtest.py 와 같은 기준 (서버는 이걸로 재시도 여부를 정한다).

verdict 가 'OK' 가 아니면 다시 생성한다(최대 3회). 항목:
  cells 12 · 정합 dy/dx ≤3px · 크기 0.93~1.07 · 잔상 0 · 정수리에 머리 있음 · 뒤 칸에 얼굴 없음 · 옷 안 바뀜
★살색 판정에 G−B<45 가 필수다 — 금발 그늘(200,170,100)을 살로 세면 뒤 칸이 전부 '얼굴' 로 잡힌다(9-06 실측).
"""
import numpy as np
from PIL import Image

CW, CH = 141, 224

def _skin(a):
    return (a[..., 0] > 150) & (a[..., 0] > a[..., 1] + 20) & (a[..., 1] > a[..., 2]) & (a[..., 1] - a[..., 2] < 45)

def cell_metrics(A, B):
    rows = []
    for r in range(4):
        for c in range(3):
            a = A[r*CH:(r+1)*CH, c*CW:(c+1)*CW, 3] > 128
            b = B[r*CH:(r+1)*CH, c*CW:(c+1)*CW, 3] > 128
            if a.sum() < 200: rows.append(None); continue
            ay, ax = np.where(a); by, bx = np.where(b)
            rows.append({'dy': int(ay.max() - by.max()), 'dx': int(round(ax.mean() - bx.mean())),
                         'h': (ay.max() - ay.min() + 1) / (by.max() - by.min() + 1)})
    return rows

def score(ai_path, base_path, hair_px=0):
    A = np.array(Image.open(ai_path).convert('RGBA')).astype(int); B = np.array(Image.open(base_path).convert('RGBA')).astype(int)
    cm = [m for m in cell_metrics(A, B) if m]
    al = A[..., 3]; mx = A[..., :3].max(-1)
    semi = int(((al > 0) & (al < 255)).sum())
    mag = int(((al == 255) & (mx > 100) & (A[..., 0] > A[..., 1] + 40) & (A[..., 2] > A[..., 1] + 40)).sum())
    crown = A[8:40, 30:111]; crown_px = int(((crown[..., 3] > 128) & ~_skin(crown)).sum())
    back = A[CH + 30:CH + 110, 40:100]; backface = int(((back[..., 3] > 128) & _skin(back)).sum())
    ta, tb = A[128:170, 50:92], B[128:170, 50:92]; ma, mb = ta[..., 3] > 128, tb[..., 3] > 128
    outfit = int(round(float(np.sqrt(((ta[ma][:, :3].mean(0) - tb[mb][:, :3].mean(0)) ** 2).sum())))) if ma.sum() >= 50 and mb.sum() >= 50 else 0
    return {'cells': len(cm),
            'dy_max': max((abs(m['dy']) for m in cm), default=99), 'dx_max': max((abs(m['dx']) for m in cm), default=99),
            'h_min': round(min((m['h'] for m in cm), default=0), 3), 'h_max': round(max((m['h'] for m in cm), default=0), 3),
            'semi': semi, 'mag': mag, 'hair': int(hair_px), 'crown': crown_px, 'backface': backface, 'outfit': outfit}

def verdict(s):
    bad = []
    if s['cells'] < 12: bad.append('칸누락%d' % (12 - s['cells']))
    if s['dy_max'] > 3: bad.append('세로%dpx' % s['dy_max'])
    if s['dx_max'] > 3: bad.append('가로%dpx' % s['dx_max'])
    if s['h_min'] < 0.93 or s['h_max'] > 1.07: bad.append('크기%.2f~%.2f' % (s['h_min'], s['h_max']))
    if s['semi'] or s['mag']: bad.append('잔상')
    if s['crown'] < 300: bad.append('머리없음')
    if s['backface'] > 150: bad.append('뒤칸에얼굴')
    if s['outfit'] > 60: bad.append('옷바뀜')
    return 'OK' if not bad else ' '.join(bad)
