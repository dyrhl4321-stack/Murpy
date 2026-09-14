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

def facing_offset(cell):
    """칸 하나의 얼굴 방향 — 머리 구역(y 8~110)에서 **살색 무게중심 x − 머리 전체 무게중심 x**.
    옆모습은 얼굴(살)이 한쪽으로 쏠리고 뒤통수(머리카락)가 반대쪽이라 부호가 곧 방향이다:
      음수 = 왼쪽을 본다 · 양수 = 오른쪽 · 0 근처 = 정면(또는 살이 없는 뒷모습).
    ★9-14 실측(운영 커마 27장): 옆 행은 |d| 11~22, 정면 행은 |d| ≤ 1. 살이 30px 미만이면 판정 불가(None).
    ★왜 필요한가: '윤이형' 시트가 왼쪽 걷기 행의 3번째 칸만 오른쪽을 봐서 **왼쪽으로 걸을 때 좌우가 번갈아 뒤집혔다**
      (대표 9-14). 12칸 존재·정합·잔상 검사는 전부 통과했다 — 방향은 아무도 안 보고 있었다."""
    a = cell.astype(int)
    head = a[8:110, :, 3] > 128
    sk = _skin(a[8:110]) & head
    if sk.sum() < 30 or head.sum() < 100: return None
    return float(np.where(sk)[1].mean() - np.where(head)[1].mean())

SIDE_MIN, FRONT_MAX = 6.0, 5.0   # 옆 행 최소 쏠림 / 정면 행 최대 쏠림 (px, 실측 11~22 vs ≤1 의 중간)

def facing_errors(A):
    """행 0 = 정면(전 칸 |d|≤FRONT_MAX) · 행 2 = 왼쪽(전 칸 d≤−SIDE_MIN) · 행 3 = 오른쪽(전 칸 d≥SIDE_MIN).
    행 1(뒷모습)은 살이 없는 게 정상이라 여기서 안 본다(backface 가 따로 본다). 어긋난 칸을 'r행c열' 로 돌려준다."""
    bad = []
    for r, want in ((0, 'front'), (2, 'left'), (3, 'right')):
        for c in range(3):
            d = facing_offset(A[r*CH:(r+1)*CH, c*CW:(c+1)*CW])
            if d is None: bad.append('r%dc%d?' % (r, c)); continue
            ok = (abs(d) <= FRONT_MAX) if want == 'front' else (d <= -SIDE_MIN if want == 'left' else d >= SIDE_MIN)
            if not ok: bad.append('r%dc%d%+.0f' % (r, c, d))
    return bad

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

def score(ai_path, base_path, hair_px=0, fringe_src=None):
    """fringe_src = 잔상 검사를 할 시트(기본 ai_path). 머리 이식본은 base 몸통의 원래 반투명 픽셀을 물려받으니
    이식 **전** AI 시트로 잔상을 본다(9-07 로컬 하네스에서 이식본이 전부 '잔상'으로 걸림)."""
    A = np.array(Image.open(ai_path).convert('RGBA')).astype(int); B = np.array(Image.open(base_path).convert('RGBA')).astype(int)
    cm = [m for m in cell_metrics(A, B) if m]
    F = np.array(Image.open(fringe_src).convert('RGBA')).astype(int) if fringe_src else A
    al = F[..., 3]; mx = F[..., :3].max(-1)
    semi = int(((al > 0) & (al < 255)).sum())
    mag = int(((al == 255) & (mx > 100) & (F[..., 0] > F[..., 1] + 40) & (F[..., 2] > F[..., 1] + 40)).sum())
    crown = A[8:40, 30:111]; crown_px = int(((crown[..., 3] > 128) & ~_skin(crown)).sum())
    # ★9-10 '머리가 칸 위로 잘림'(대표: 뒷머리가 수평으로 잘린다). 발을 base 에 맞춰 앉히는 구조라
    #   머리가 224px 을 넘으면 위가 **평평하게 잘려** 나간다(보우야 3칸). 손제작 자산은 y=0 에 절대 안 닿는다.
    #   여기서 걸러 재생성시킨다 — 스케일을 줄이면 목선이 base 와 어긋나 이식에 구멍이 난다.
    clipped = sum(1 for r in range(4) for c in range(3)
                  if (A[r * CH, c * CW:(c + 1) * CW, 3] > 128).any())
    back = A[CH + 30:CH + 110, 40:100]; backface = int(((back[..., 3] > 128) & _skin(back)).sum())
    # ★상의 띠(y128~170)만 보다가 **흰 바지**(하의 바뀜)를 통과시켰다(9-07 대표 실전 1호). 상·하의 띠 둘 다, 큰 쪽.
    outfit = 0
    for (y0, y1) in ((128, 170), (168, 200)):
        ta, tb = A[y0:y1, 50:92], B[y0:y1, 50:92]; ma, mb = ta[..., 3] > 128, tb[..., 3] > 128
        if ma.sum() >= 50 and mb.sum() >= 50:
            outfit = max(outfit, int(round(float(np.sqrt(((ta[ma][:, :3].mean(0) - tb[mb][:, :3].mean(0)) ** 2).sum())))))
    return {'cells': len(cm),
            'dy_max': max((abs(m['dy']) for m in cm), default=99), 'dx_max': max((abs(m['dx']) for m in cm), default=99),
            'h_min': round(min((m['h'] for m in cm), default=0), 3), 'h_max': round(max((m['h'] for m in cm), default=0), 3),
            'semi': semi, 'mag': mag, 'hair': int(hair_px), 'crown': crown_px, 'backface': backface,
            'outfit': outfit, 'clipped': clipped,
            'facing': facing_errors(A)}

def verdict(s):
    bad = []
    if s['cells'] < 12: bad.append('칸누락%d' % (12 - s['cells']))
    if s['dy_max'] > 3: bad.append('세로%dpx' % s['dy_max'])
    if s['dx_max'] > 3: bad.append('가로%dpx' % s['dx_max'])
    if s['h_min'] < 0.93 or s['h_max'] > 1.07: bad.append('크기%.2f~%.2f' % (s['h_min'], s['h_max']))
    if s['semi'] or s['mag']: bad.append('잔상')
    if s['crown'] < 300: bad.append('머리없음')
    if s.get('clipped'): bad.append('머리잘림%d칸' % s['clipped'])
    if s['backface'] > 150: bad.append('뒤칸에얼굴')
    if s['outfit'] > 45: bad.append('옷바뀜')
    if s.get('facing'): bad.append('방향' + ','.join(s['facing']))
    return 'OK' if not bad else ' '.join(bad)
