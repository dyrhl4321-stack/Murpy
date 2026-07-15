# -*- coding: utf-8 -*-
"""char/rooms/*.png 에서 LimeZu 시트에서 딸려온 바닥 그림자 픽셀 제거.

- 그림자색 S=(167,151,150): 전 가구 공통 바닥그림자 → 제거 (tv_wall 제외: 미사용)
- 침대 3종: G=(120,120,120)·F=(176,176,160)도 시트 바닥/그림자 베이크 → 제거
  (tv_wall의 G=화면, F=화면 상단 하이라이트라 보존)
- 제거 후 고립 조각(이웃 모듈 파편) 스캔·보고. --apply 시 최대 컴포넌트만 남김 대상은
  ISLAND_DROP 목록으로 명시.
크기(캔버스)는 절대 변경하지 않음 — 앱 좌표계/z계산이 PNG 크기에 묶여 있음.
"""
import os, sys, collections
from PIL import Image

ROOMS = os.path.join(os.path.dirname(__file__), 'rooms')
S = (167, 151, 150)
G = (120, 120, 120)
F = (176, 176, 160)

BEDS = {'bed_green.png', 'bed_cyan.png', 'bed_white.png'}
SKIP_S = {'tv_wall.png'}          # S 미사용, G/F는 디자인(화면)
ISLAND_DROP = {'sofa_brown.png', 'globe.png'}  # 소파=우측 러그 파편, 지구본=좌측 막대 파편

APPLY = '--apply' in sys.argv


def components(px, w, h):
    seen = [[False]*w for _ in range(h)]
    comps = []
    for sy in range(h):
        for sx in range(w):
            if seen[sy][sx] or px[sx, sy][3] == 0:
                continue
            stack = [(sx, sy)]
            seen[sy][sx] = True
            cells = []
            while stack:
                x, y = stack.pop()
                cells.append((x, y))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = x+dx, y+dy
                        if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and px[nx, ny][3]:
                            seen[ny][nx] = True
                            stack.append((nx, ny))
            comps.append(cells)
    return comps


for f in sorted(os.listdir(ROOMS)):
    if not f.endswith('.png'):
        continue
    path = os.path.join(ROOMS, f)
    im = Image.open(path).convert('RGBA')
    w, h = im.size
    px = im.load()
    kill = {S} if f not in SKIP_S else set()
    if f in BEDS:
        kill |= {G, F}
    removed = 0
    for y in range(h):
        for x in range(w):
            p = px[x, y]
            if p[3] and p[:3] in kill:
                px[x, y] = (0, 0, 0, 0)
                removed += 1
    comps = sorted(components(px, w, h), key=len, reverse=True)
    island_note = ''
    if len(comps) > 1:
        sizes = [len(c) for c in comps]
        island_note = f' islands={sizes[1:]}'
        if f in ISLAND_DROP:
            for c in comps[1:]:
                for x, y in c:
                    px[x, y] = (0, 0, 0, 0)
                removed += len(c)
            island_note += ' -> dropped'
    print(f'{f}: shadow_removed={removed}{island_note}' + ('' if APPLY else ' (dry-run)'))
    if APPLY:
        im.save(path)
