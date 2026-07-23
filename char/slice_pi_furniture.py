# -*- coding: utf-8 -*-
"""Pixel Interiors 시트에서 방 가구를 4배로 잘라낸다.

    python char/slice_pi_furniture.py <PixelInteriors시트.png>
    python char/slice_pi_furniture.py <시트.png> --contact 확인용.png

왜 4배인가
  캐릭터가 3.3타일(158유닛)로 유난히 커서, 원본 1배(문 18x31 -> 18유닛)로는 장난감이 된다.
  4배면 옷장·책장이 96x184로 캐릭터(158)보다 커져 비율이 성립한다. 5배는 방을 다 먹는다.
  정수배만 쓴다(픽셀 아트 하드룰) — 4.4배가 이론상 맞지만 비정수배는 반투명 픽셀을 만든다.
  방 바닥(field_room.png)도 4배라 아트픽셀 크기가 방 전체에서 일치한다.

시트 특성
  스프라이트가 투명 여백으로 완전히 분리돼 있다(연결요소 106개, 실측). LimeZu 시트처럼
  이웃 모듈이 외곽선으로 맞붙는 문제가 없어 bbox를 그대로 믿어도 된다.

좌표는 알파 연결요소 분석으로 뽑은 실측값이다. 시트를 바꾸면 다시 재야 한다.
"""
import argparse
import os

from PIL import Image

SCALE = 4

# (파일명, 표시이름, x0, y0, x1, y1, 추가속성)
ITEMS = [
    ('pi_bed_wood',    '원목 침대',   162,  10, 190,  56, {}),
    ('pi_bed_pink',    '핑크 침대',   322, 171, 350, 216, {}),
    ('pi_bookshelf',   '책장',        228,   9, 252,  55, {}),
    ('pi_wardrobe',    '키큰 수납장', 260,   9, 284,  55, {}),
    ('pi_cabinet',     '원목 옷장',   290,  10, 318,  54, {}),   # 손잡이 달린 양문 = 옷장
    ('pi_cabinet_tall','나무 캐비닛', 322,  10, 350,  54, {}),
    ('pi_nightstand',  '협탁',        199,   5, 217,  25, {}),
    ('pi_lowtable',    '낮은 탁자',   194,  37, 222,  57, {}),
    ('pi_armchair_rose','로즈 안락의자',355,  1, 381,  30, {}),
    ('pi_armchair_teal','민트 안락의자',355, 33, 381,  62, {}),
    ('pi_armchair_blue','블루 안락의자',355, 65, 381,  94, {}),
    ('pi_desk',        '책상',        232, 130, 280, 158, {}),
    ('pi_table',       '테이블',      302, 130, 338, 158, {}),
    ('pi_rug',         '줄무늬 러그', 173, 166, 211, 187, {'flat': True}),
    ('pi_door',        '문',          231, 161, 249, 192, {'wall': True}),
    ('pi_tv',          'TV',          356, 134, 380, 153, {}),
    ('pi_microwave',   '전자레인지',  356, 102, 380, 121, {}),
    ('pi_plant',       '화분',        425, 130, 439, 157, {}),
    ('pi_floorlamp',   '플로어 램프', 394, 132, 405, 154, {}),
    ('pi_fridge',      '냉장고',      418, 169, 446, 215, {}),
    ('pi_fridge_white','화이트 냉장고',450, 169, 478, 215, {}),
]

ROOMS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rooms')


# ★그림자 임계값. Pixel Interiors는 접지 그림자를 RGB(47,47,46) alpha 131 단일값으로
# 구워 넣었다(실측: 반투명 픽셀이 전부 alpha 131 하나뿐 = 안티에일리어싱 없음).
# 임계값 128로 이진화하면 131>=128이라 그림자가 불투명 회색 얼룩으로 굳어 가구 아래에 남는다
# (LimeZu 때와 같은 문제, 대표 지적 7-23). 200으로 올리면 그림자(131)만 투명해지고
# 본체(alpha 255)는 그대로 살아, 우리 CSS 접지 그림자(_mwShadowHtml)로 통일된다.
SHADOW_CUT = 200


def solid_bbox(im):
    """본체(alpha >= SHADOW_CUT)만 내용으로 본다. 구워진 그림자에 bbox가 끌려가지 않게."""
    W, H = im.size
    a = im.getchannel('A').tobytes()
    x0, y0, x1, y1 = W, H, -1, -1
    for y in range(H):
        row = y * W
        for x in range(W):
            if a[row + x] >= SHADOW_CUT:
                x0 = min(x0, x); x1 = max(x1, x)
                y0 = min(y0, y); y1 = max(y1, y)
    return None if x1 < 0 else (x0, y0, x1 + 1, y1 + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sheet')
    ap.add_argument('--out', default=ROOMS)
    ap.add_argument('--contact', default=None, help='이름·크기 확인용 대조표')
    ap.add_argument('--catalog', action='store_true', help='ROOM_ITEMS 코드 출력')
    ap.add_argument('--footprint', action='store_true',
                    help='각 가구 바닥 접지폭(sbw) 측정 출력 — 접지 그림자 폭 기준')
    args = ap.parse_args()

    sheet = Image.open(args.sheet).convert('RGBA')
    os.makedirs(args.out, exist_ok=True)
    made = []

    for name, label, x0, y0, x1, y1, extra in ITEMS:
        crop = sheet.crop((x0, y0, x1, y1))
        bb = solid_bbox(crop)
        if not bb:
            print(f'  건너뜀 {name}: 내용 없음')
            continue
        crop = crop.crop(bb)                      # 여백 제거 — 배치 좌표가 실제 형태와 어긋나지 않게
        # 알파 이진화(임계 SHADOW_CUT). 구워진 그림자(alpha 131)를 투명으로 날리고 본체만 남긴다.
        r, g, b, a = crop.split()
        crop = Image.merge('RGBA', (r, g, b, a.point(lambda v: 255 if v >= SHADOW_CUT else 0)))
        w, h = crop.size
        big = crop.resize((w * SCALE, h * SCALE), Image.NEAREST)
        big.save(os.path.join(args.out, name + '.png'))
        made.append((name, label, big.size[0], big.size[1], extra, big))
        print(f'  {name:18s} {w}x{h} -> {big.size[0]}x{big.size[1]}  {label}')

    if args.catalog:
        print('\n--- ROOM_ITEMS ---')
        for name, label, w, h, extra, _ in made:
            flags = ''.join(f", {k}:true" for k in extra)
            print(f"  {{ id:'{name}', name:'{label}', src:'char/rooms/{name}.png?v=1', w:{w}, h:{h}{flags} }},")

    if args.footprint:
        # 바닥 접지폭 = 하단 12% 구간의 불투명 픽셀 가로 범위. 접지 그림자를 이 폭에 맞춘다.
        print('\n--- sbw (바닥 접지폭) ---')
        for name, label, w, h, extra, im in made:
            px = im.load()
            band = max(4, int(h * 0.12))
            xs = [x for y in range(h - band, h) for x in range(w) if px[x, y][3] > 0]
            print(f"  {name:18s} sbw:{max(xs) - min(xs) + 1}" if xs else f"  {name}: 없음")

    if args.contact:
        # 캐릭터(158유닛)를 맨 앞에 세워 비율을 눈으로 확인한다
        walk = Image.open(os.path.join(os.path.dirname(ROOMS), 'char', 'walk.png')
                          if False else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'walk.png')).convert('RGBA')
        fw, fh = walk.size[0] // 3, walk.size[1] // 4
        body = walk.crop((0, 0, fw, fh)).resize((round(158 * fw / fh), 158), Image.NEAREST)
        tiles = [('캐릭터', body)] + [(n, im) for n, _l, _w, _h, _e, im in made]
        cols = 7
        cw = max(t[1].size[0] for t in tiles) + 16
        ch = max(t[1].size[1] for t in tiles) + 16
        rows = (len(tiles) + cols - 1) // cols
        sheet_img = Image.new('RGBA', (cols * cw, rows * ch), (24, 30, 46, 255))
        for i, (n, im) in enumerate(tiles):
            cx = (i % cols) * cw + (cw - im.size[0]) // 2
            cy = (i // cols) * ch + (ch - im.size[1])      # 바닥 정렬 — 키 비교가 목적
            sheet_img.alpha_composite(im, (cx, cy))
        sheet_img.convert('RGB').save(args.contact)
        print(f'\n확인용: {args.contact} (맨 앞이 캐릭터 158유닛, 바닥 정렬)')


if __name__ == '__main__':
    main()
