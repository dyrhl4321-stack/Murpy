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
    # ★안락의자는 시트에 **4방향**이 다 있다(대표 발견 2026-08-05).
    #   열: 355=정면 / 387=후면 / 420=좌 / 453=우.  행: 1=로즈 33=민트 65=블루
    #   _d1..3 은 카탈로그에서 dirs 로 묶어 '돌리기' 버튼에 쓴다.
    ('pi_armchair_rose','로즈 안락의자',355,  1, 381,  30, {}),
    ('pi_armchair_rose_d1','로즈 안락의자(뒤)',387,  1, 413,  30, {}),
    ('pi_armchair_rose_d2','로즈 안락의자(좌)',419,  1, 444,  30, {}),
    ('pi_armchair_rose_d3','로즈 안락의자(우)',452,  1, 477,  30, {}),
    ('pi_armchair_teal','민트 안락의자',355, 33, 381,  62, {}),
    ('pi_armchair_teal_d1','민트 안락의자(뒤)',387, 33, 413,  62, {}),
    ('pi_armchair_teal_d2','민트 안락의자(좌)',419, 33, 444,  62, {}),
    ('pi_armchair_teal_d3','민트 안락의자(우)',452, 33, 477,  62, {}),
    ('pi_armchair_blue','블루 안락의자',355, 65, 381,  94, {}),
    ('pi_armchair_blue_d1','블루 안락의자(뒤)',387, 65, 413,  94, {}),
    ('pi_armchair_blue_d2','블루 안락의자(좌)',419, 65, 444,  94, {}),
    ('pi_armchair_blue_d3','블루 안락의자(우)',452, 65, 477,  94, {}),
    ('pi_desk',        '책상',        232, 130, 280, 158, {}),
    ('pi_table',       '테이블',      302, 130, 338, 158, {}),
    ('pi_rug',         '줄무늬 러그', 173, 166, 211, 187, {'flat': True}),
    ('pi_door',        '문',          231, 161, 249, 192, {'wall': True}),
    # ★TV 는 **앞/뒤 한 쌍**이다 (대표 발견 2026-08-05).
    #   356,102 = 앞면(화면) — 예전엔 '전자레인지'로 잘못 읽었다
    #   356,134 = 뒷면(통풍구 + RCA 단자 빨강·노랑·흰색 점 3개) — 예전엔 이걸 'TV'로 썼다
    #   그래서 TV 를 놓으면 뒤통수만 보였다. 안락의자처럼 dirs 로 묶는다.
    ('pi_tv',          'TV',          356, 102, 380, 121, {}),
    ('pi_tv_d1',       'TV(뒤)',      356, 134, 380, 153, {}),
    ('pi_window',      '창문',        225, 229, 253, 249, {'wall': True}),
    # 'pi_microwave' 폐기 — 전자레인지가 아니라 **TV 앞면**이었다. 위 pi_tv 로 옮겼다.
    ('pi_plant',       '화분',        425, 130, 439, 157, {}),
    ('pi_floorlamp',   '플로어 램프', 394, 132, 405, 154, {}),
    ('pi_fridge',      '냉장고',      418, 169, 446, 215, {}),
    ('pi_fridge_white','화이트 냉장고',450, 169, 478, 215, {}),
]

# ===== 핑크 에디션 (대표 8-28: "방꾸미기 핑크를 좋아하는 사람이 많아서 특별에셋으로") =====
# 시트 = 핑크인테리어.png (352x288). ★반투명 픽셀이 하나도 없다(알파 0/255뿐) —
#   구워진 그림자가 없다는 뜻이라, 우리 접지 그림자(_mwShadowHtml)가 그대로 붙는다.
# 좌표는 알파 연결요소 분석 실측값(54덩어리). 여러 개가 한 덩어리로 붙은 곳만 손으로 갈랐다.
PINK_ITEMS = [
    # --- 침대·수납 ---
    ('pk_bed',        '핑크 침대',      1,  90,  31, 143, {}),
    ('pk_wardrobe',   '핑크 옷장',     97, 199, 142, 255, {}),
    ('pk_dresser',    '핑크 서랍장',   50, 215,  94, 255, {}),
    ('pk_drawer_s',   '핑크 3단 서랍', 86, 264, 108, 288, {}),
    ('pk_cabinet_low','핑크 낮은 수납장', 196, 236, 221, 256, {}),
    ('pk_nightstand', '핑크 협탁',    100, 103, 124, 127, {}),
    # --- 의자·탁자 ---
    ('pk_sofa',       '핑크 소파',    294, 217, 345, 240, {}),
    # ('pk_sofa_s') 폐기 — 안락의자의 **옆모습**이었다(대표 8-28). pk_armchair_d1 로 간다
    ('pk_armchair',   '핑크 안락의자', 36, 147,  61, 176, {}),
    ('pk_bench',      '핑크 벤치',    112, 161, 160, 192, {}),
    ('pk_ottoman',    '핑크 스툴',      5, 236,  42, 256, {}),
    ('pk_desk',       '핑크 책상',    162, 163, 206, 192, {}),
    ('pk_desk_long',  '핑크 긴 책상',   2, 259,  46, 288, {}),
    ('pk_chair',      '핑크 의자',      2, 184,  14, 208, {}),
    # --- 주방 ---
    ('pk_fridge',     '핑크 냉장고',  291,  78, 317, 128, {}),
    ('pk_oven',       '핑크 오븐',    262, 100, 282, 128, {}),
    ('pk_microwave',  '핑크 전자레인지', 212, 173, 235, 192, {}),
    # --- 욕실 ---
    ('pk_bath',       '핑크 욕조',    129, 132, 174, 159, {}),
    ('pk_toilet',     '핑크 변기',    257, 166, 272, 192, {}),
    ('pk_sink',       '핑크 세면대',  279,   3, 298,  32, {}),
    ('pk_washstand',  '핑크 세면장',   52, 260,  78, 288, {}),
    # --- 소품·조명 ---
    ('pk_tv',         '딸기 TV',       68,  96,  91, 128, {}),
    ('pk_clock',      '핑크 괘종시계',240, 170, 255, 192, {}),
    ('pk_sewing',     '핑크 재봉틀',  277, 170, 298, 192, {}),
    ('pk_mirror',     '핑크 거울',    260, 208, 284, 240, {}),
    ('pk_vase',       '핑크 꽃병',    211, 200, 222, 222, {}),
    ('pk_vase_rose',  '장미 꽃병',    194, 201, 206, 223, {}),
    ('pk_bin',        '핑크 휴지통',   40, 123,  57, 142, {}),
    ('pk_teapot',     '핑크 주전자',   18, 209,  31, 223, {}),
    ('pk_books',      '핑크 책',      227, 209, 237, 223, {}),
    # --- 벽·바닥 ---
    ('pk_door',       '핑크 문',      212,   9, 237,  48, {'wall': True}),
    ('pk_window',     '핑크 창문',     98, 130, 125, 159, {'wall': True}),
    # ★'커튼'이 아니라 **ㄷ자 조리대**다 (대표 8-28 지적). 벽에 거는 게 아니라 바닥에 놓는다 —
    #   wall:true 로 두면 접지 그림자도 안 그린다.
    ('pk_counter_u',  'ㄷ자 조리대',  216,  53, 264,  96, {}),
    ('pk_rug',        '핑크 러그',    150, 209, 185, 255, {'flat': True}),
    ('pk_rug_heart',  '하트 러그',     34,  93,  62, 111, {'flat': True}),

    # ===== 2차 (대표 8-28: "넣다 말지 말고 다 넣어라고") =====
    # 1차에서 빠진 것 전부. 여러 개가 한 덩어리로 붙어 있던 곳은 4방향 연결요소로 다시 갈랐다.
    ('pk_stool',      '핑크 스툴의자',279,  43, 298,  65, {}),
    ('pk_towel',      '핑크 수건걸이',181,  71, 207,  93, {'wall': True}),
    ('pk_counter_long','긴 싱크대',  128,  98, 256, 128, {}),   # y130 까지 잡으면 아래 선반·책상 윗선이 딸려온다
    ('pk_shelf',      '핑크 선반',   177, 128, 206, 160, {}),
    ('pk_desk_drawer','핑크 서랍책상',212, 128, 252, 160, {}),
    ('pk_plates',     '접시',        150,  75, 170,  93, {}),
    ('pk_gamepad',    '핑크 게임패드',313, 166, 330, 178, {}),   # 308 부터 잡으면 모니터 받침이 붙는다
    ('pk_box_pink',   '핑크 상자',   274, 142, 289, 160, {}),
    ('pk_fireplace',  '핑크 벽난로',  66, 160, 112, 192, {}),   # 위=창문 밑선, 아래=토스터 윗선을 뺀다
    ('pk_toaster',    '토스터',       64, 193,  80, 209, {}),
    ('pk_toaster2',   '핑크 토스터',  80, 193,  96, 212, {}),
    ('pk_table',      '핑크 테이블',  21, 184,  44, 206, {}),
    ('pk_lampstand',  '램프 협탁',   304, 176, 321, 209, {}),
    ('pk_letter',     '편지',          1, 212,  15, 223, {}),
    ('pk_window_b',   '핑크 창문(작은)',69, 130,  93, 160, {'wall': True}),

    # ★액자 3종은 **6배**로 굽는다(구멍 16px x6 = 96px = 그림 표시크기).
    #   ★★8-29 — 6배(168)로 키웠다가 **너무 컸다**(대표: "액자를 저따구로 크게 만들면 어뜨카냐").
    #   원한 건 "아까 거기서 진짜 살짝만" = 4배(112)에서 한 칸 위인 **5배(140)**다.
    #   구멍 80px 이 그림(96px)보다 살짝 작아서 액자가 그림 가장자리를 물고 낑기는 모양이 된다.
    ('pk_frame',      '핑크 액자',   314,  26, 342,  54, {'wall': True, 'scale': 5}),
    ('pk_frame_b',    '꽃무늬 액자',  75,  59, 101,  85, {'wall': True, 'scale': 5}),
    ('pk_frame_c',    '두꺼운 액자', 107,  59, 133,  85, {'wall': True, 'scale': 5}),

    # ★방향이 있는 것 — **좌우 반전이 아니라 시트에 실제로 그려진 다른 각도**다(대표 8-28:
    #   "핑크 1인소파랑 핑크 안락의자랑 똑같은 거임, 그 방향이 서로 다른 거임").
    #   _d1 은 카탈로그에서 dirs 로 묶어 '돌리기' 버튼에 쓴다.
    ('pk_armchair_d1','핑크 안락의자(옆)', 5, 147,  26, 177, {}),
    ('pk_chair_d1',   '핑크 의자(옆)',    50, 184,  63, 209, {}),
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
    ap.add_argument('--set', default='pi', choices=['pi', 'pink'],
                    help='pi=Pixel Interiors(기본) / pink=핑크 에디션')
    ap.add_argument('--out', default=ROOMS)
    ap.add_argument('--contact', default=None, help='이름·크기 확인용 대조표')
    ap.add_argument('--catalog', action='store_true', help='ROOM_ITEMS 코드 출력')
    ap.add_argument('--footprint', action='store_true',
                    help='각 가구 바닥 접지폭(sbw) 측정 출력 — 접지 그림자 폭 기준')
    args = ap.parse_args()

    sheet = Image.open(args.sheet).convert('RGBA')
    os.makedirs(args.out, exist_ok=True)
    made = []

    table = PINK_ITEMS if args.set == 'pink' else ITEMS
    for name, label, x0, y0, x1, y1, extra in table:
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
        # ★항목별 배율. 정수배만 쓴다(픽셀 하드룰). 액자는 안쪽 구멍 16px 이 그림 표시크기
        #   96px 과 맞아떨어지는 6배로 굽는다 — 그래야 그림을 액자에 포개면 딱 들어간다.
        sc = int(extra.get('scale', SCALE))
        big = crop.resize((w * sc, h * sc), Image.NEAREST)
        big.save(os.path.join(args.out, name + '.png'))
        made.append((name, label, big.size[0], big.size[1], extra, big))
        print(f'  {name:18s} {w}x{h} -> {big.size[0]}x{big.size[1]}  {label}')

    if args.catalog:
        print('\n--- ROOM_ITEMS ---')
        for name, label, w, h, extra, _ in made:
            flags = ''.join(f", {k}:true" for k in extra if k != 'scale')
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
