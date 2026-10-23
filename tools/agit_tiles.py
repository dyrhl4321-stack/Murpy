# 크루 아지트 바닥·벽 타일 — LimeZu Modern Interiors 48px 에서 잘라 낸다 (10-22).
#   대표 10-19 시안 승인본(머피브랜딩\크루기록_최종캡처_20261019\시안_아지트_바닥벽질감_LimeZu.png)과 같은 칸을 쓴다.
#   tex_mock.py 의 ftile(g, r) · wpiece(g, r) 와 같은 좌표식.
#   벽 = 48×192 한 줄(어두운 머리 16 + 벽지 + 걸레받이 + 바닥과 사이 그림자 16) — 앱은 이걸 가로로만 반복한다.
#   LimeZu 라이선스: 상업 사용 가능, 원본 재배포 불가, limezu.itch.io 표기.
#   사용: python tools/agit_tiles.py
import os
from PIL import Image

LZ = r'C:\Users\dyrhl\Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차\외부에셋테스트\moderninteriors-win\1_Interiors\48x48\Room_Builder_subfiles_48x48'
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'char', 'crews')
FL = Image.open(os.path.join(LZ, 'Room_Builder_Floors_48x48.png')).convert('RGBA')
WL = Image.open(os.path.join(LZ, 'Room_Builder_Walls_48x48.png')).convert('RGBA')
CAP, SHADOW, WALL_H = (42, 33, 23), (26, 21, 16), 192   # 머리 #2a2117 · 사이 그림자 #1a1510 (시안과 같은 색)

def ftile(g, r):
    x, y = g * 192 + 48, 96 + r * 96 + 48
    return FL.crop((x, y, x + 48, y + 48))

def wall_strip(g, r):
    p = WL.crop((g * 528 + 48, r * 96, g * 528 + 96, r * 96 + 96))   # 48×96: 위 테두리 0~20 · 벽지 20~68 · 걸레받이까지 20~96
    im = Image.new('RGBA', (48, WALL_H), SHADOW + (255,))
    im.paste(Image.new('RGBA', (48, 16), CAP + (255,)), (0, 0))
    im.paste(p.crop((0, 0, 48, 20)), (0, 12))
    for y in (32, 80):                                   # 벽지 몸통 두 장(아래 장은 걸레받이에 반쯤 덮인다)
        im.paste(p.crop((0, 20, 48, 68)), (0, y))
    bottom = p.crop((0, 20, 48, 96))                     # 76 높이(벽지+걸레받이)
    im.paste(bottom, (0, WALL_H - 16 - bottom.height))  # 걸레받이가 바닥 위 16 그림자 바로 위에 오게
    return im

THEMES = {'club': ((1, 5), (0, 3))}   # 클럽하우스: 나무 마루 · 크림 벽
for name, (fl, wl) in THEMES.items():
    ftile(*fl).save(os.path.join(OUT, 'agit_floor_%s.png' % name), optimize=True)
    wall_strip(*wl).save(os.path.join(OUT, 'agit_wall_%s.png' % name), optimize=True)
    print(name, 'ok')
