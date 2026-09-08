# -*- coding: utf-8 -*-
"""이름표 스킨(도트 판) 생성기 — 9-08 대표 #43: "불투명 사각형 대신 도트 판 위에 닉네임, 기존 이름표보다 살짝 큰 정도, 여자애들이 좋아할 귀여운 오리지널".
메이플 명찰반지 문법(작은 파스텔 판 + 한쪽 끝 마스코트)을 머피식으로 — 나노바나나 산출물은 픽셀 블록이 8~10px 라 라벨 크기로 못 줄여서 진짜 해상도로 직접 찍는다.

    python tools/gen_nametags.py            # char/ui/tag_<id>.png (1배 픽셀, 폭 W 높이 22) + 검수 폴더 미리보기(6배)

CSS 쪽 규격(index.html .mw-tag-*): border-image-slice = 위 7 / 오른쪽 R / 아래 3 / 왼쪽 L, fill. outset 은 판이 라벨 밖으로 2px 씩 + 마스코트 폭.
"""
import os, sys, io, datetime
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'char', 'ui')
REVIEW = os.path.join(r'C:\Users\dyrhl\Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차\에셋검수', datetime.date.today().strftime('%Y-%m-%d') + '_이름표스킨')

H = 22; PT = 4; PB = 21            # 판: y 4..21 (18px), 위 4px 는 마스코트가 삐져나오는 자리

def hx(s): s = s.lstrip('#'); return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4)) + (255,)

def plate(img, x0, x1, pal):
    """둥근 도트 판: 외곽선 K, 윗줄 하이라이트 H, 몸통 B, 아랫줄 그늘 S. 모서리 1px 깎음."""
    px = img.load()
    for y in range(PT, PB + 1):
        for x in range(x0, x1 + 1):
            edge_x = x in (x0, x1); edge_y = y in (PT, PB)
            corner = (x in (x0, x1)) and (y in (PT, PB))
            if corner: continue
            corner2 = (x in (x0 + 1, x1 - 1)) and (y in (PT, PB))
            corner3 = (x in (x0, x1)) and (y in (PT + 1, PB - 1))
            if edge_x or edge_y or corner2 or corner3: px[x, y] = pal['K']; continue
            if y == PT + 1 or (y == PT + 2 and x in (x0 + 1, x1 - 1)) or (x == x0 + 1 and y < PB - 2): px[x, y] = pal['H']
            elif y == PB - 1 or (y == PB - 2 and x in (x0 + 1, x1 - 1)) or (x == x1 - 1 and y > PT + 2): px[x, y] = pal['S']
            else: px[x, y] = pal['B']
    # 모서리 둥글게: 대각 픽셀
    for (cx, cy) in ((x0 + 1, PT + 1), (x1 - 1, PT + 1), (x0 + 1, PB - 1), (x1 - 1, PB - 1)): px[cx, cy] = pal['K']

def blit(img, art, ox, oy, pal):
    px = img.load()
    for j, row in enumerate(art):
        for i, ch in enumerate(row):
            if ch == '.': continue
            px[ox + i, oy + j] = pal[ch]

BUNNY = """
..KK....KK..
.KpPK..KpPK.
.KpPK..KpPK.
.KpPK..KpPK.
KKWWKKKKWWKK
KWWWWWWWWWWK
KWWEWWWWEWWK
KWpWWWWWWpWK
KWWWWKKWWWWK
.KWWWWWWWWK.
..KKKKKKKK..
""".strip().splitlines()

HEART = """
.KK...KK.
KWpPKPPPK
KpPPPPPPK
KPPPPPPPK
.KPPPPPK.
..KPPPK..
...KPK...
....K....
""".strip().splitlines()

SPROUT = """
..KK...KK..
.KgGK.KGgK.
.KGGGKGGGK.
..KGGKGGK..
...KKKKK...
.....K.....
.....K.....
""".strip().splitlines()

RIBBON = """
.KK.....KK.
KppK.K.KppK
KpPPKKKPPpK
KPPPKKKPPPK
.KPPKKKPPK.
..KK.K.KK..
...K...K...
""".strip().splitlines()

WEIGHT = """
.KKKK.
KHHHBK
KHBBBK
KBBBBK
KBBBBK
KBBBBK
KBBBBK
KBBBBK
KBBBBK
KBBBBK
KBBBBK
KBBBBK
KBBBBK
KBBBBK
KBBBBK
KBBBBK
KBBBBK
KBBBBK
KBBBBK
KSSSBK
KSSSSK
.KKKK.
""".strip().splitlines()

CARROT = """
..KK.KK.
.KgGKGgK
..KGGGK.
..KOoOK.
.KOoOOOK
.KOOOOOK
.KOOOOOK
..KOOOK.
..KOOOK.
...KOK..
...KOK..
....K...
""".strip().splitlines()

SPARK = """
...K...
..KyK..
.KyyyK.
KyyyyyK
.KyyyK.
..KyK..
...K...
""".strip().splitlines()

STAR = """
....K....
...KyK...
...KyK...
KKKKyKKKK
.KyyyyyK.
..KyyyK..
..KyKyK..
.KK...KK.
""".strip().splitlines()

SKINS = [
  # id, 이름, 팔레트, 왼쪽 아트,(ox,oy), 오른쪽 아트(None=왼쪽 좌우반전),(오른쪽 끝에서 ox, oy), 판 x0, 캡 폭(양쪽 같음), 글자색
  ('bunny',   '토끼 이름표', dict(K='#6b4a3a', B='#fff6e6', H='#ffffff', S='#f0dcc4', W='#ffffff', P='#ffb0c4', p='#ffd6e0', E='#3a2620', O='#ff9a3c', o='#ffc27a', G='#4fc27f', g='#a7e9c1'), BUNNY, (1, 2), CARROT, (1, 1), 4, 15, '#4a3328'),
  ('heart',   '하트 이름표', dict(K='#b03a5a', B='#ffc2d2', H='#ffe0ea', S='#ffa4bc', W='#ffffff', P='#ff6f91', p='#ff9fb6'), HEART, (2, 1), None, (2, 1), 3, 12, '#5a1f33'),
  ('sprout',  '새싹 이름표', dict(K='#2f7a55', B='#d6f5e6', H='#f0fff7', S='#b6e8cf', G='#4fc27f', g='#a7e9c1'), SPROUT, (2, 0), None, (2, 0), 3, 14, '#1f4a35'),
  ('ribbon',  '리본 이름표', dict(K='#5a3f9a', B='#e8dcff', H='#f7f2ff', S='#d2c0f5', P='#b48cff', p='#d9c4ff'), RIBBON, (2, 0), None, (2, 0), 3, 14, '#3a2866'),
  ('dumbbell','덤벨 이름표', dict(K='#26386e', B='#a8c4ff', H='#dbe7ff', S='#7f9ee6'), WEIGHT, (0, 0), 'weight', (0, 0), 5, 8, '#16244a'),
  ('star',    '별 이름표',   dict(K='#8a6a1e', B='#fff2b8', H='#fffbe0', S='#f2dd8c', y='#ffd84a'), STAR, (2, 0), SPARK, (3, 1), 3, 12, '#4a3a10'),
]

def make(skin):
    sid, name, pal, art, (ox, oy), rart, (rx, ry), x0, C, tc = skin
    pal = {k: hx(v) for k, v in pal.items()}
    W = C * 2 + 14                                   # 중간 stretch 구간 14px(어차피 늘어난다)
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if rart == 'weight':
        plate(img, x0, W - 6, pal)
        blit(img, WEIGHT, 0, 0, pal); blit(img, WEIGHT, W - 6, 0, pal)
    else:
        plate(img, x0, W - 1 - x0, pal)
        blit(img, art, ox, oy, pal)
        r = rart or [row[::-1] for row in art]
        blit(img, r, W - rx - len(r[0]), ry, pal)
    p = os.path.join(OUT, 'tag_%s.png' % sid); img.save(p)
    return p, img, C, C, tc, name

def main():
    os.makedirs(REVIEW, exist_ok=True)
    rows = []; names = []
    for s in SKINS:
        p, img, L, R, tc, name = make(s)
        big = img.resize((img.width * 6, img.height * 6), Image.NEAREST)
        bg = Image.new('RGBA', big.size, (40, 44, 56, 255)); bg.alpha_composite(big)
        bg.save(os.path.join(REVIEW, 'tag_%s_x6.png' % s[0]))
        rows.append("  .mw-frame-%s { color:%s !important; border-image-source:url('char/ui/tag_%s.png?v=2') !important; border-image-slice:7 %d 3 %d fill !important; border-image-width:7px %dpx 3px %dpx !important; border-image-outset:6px %dpx 2px %dpx !important }" % (s[0], tc, s[0], R, L, R, L, R - 2, L - 2))
        names.append("%s: '%s'" % (s[0], name))
        print(p, img.size, 'slice L', L, 'R', R)
    print('\n'.join(rows)); print('window._MW_FRAMES = { ' + ', '.join(names) + ' };')

if __name__ == '__main__':
    main()
