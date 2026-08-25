# -*- coding: utf-8 -*-
"""산 펫 팩(Top-Down-Pet-Pack v1.1)을 앱에서 쓸 시트로 정규화한다.

    python char/build_pet_sheets.py

출력: char/pets/{펫id}.png   (셀 32x32, 6열 x 30행 고정 배치)
      char/pets/pets.json    (행마다 실제 프레임 수 — 행 배치는 아래 ROW_MAP 고정)
      char/rooms/pet_*.png   (밥그릇·캣타워·개집 등 방 가구로 등록할 소품)

★왜 다시 조립하는가
팩은 동작마다 파일이 따로고(펫 하나에 9장), 행 구성이 동작마다 다르다.
그대로 쓰면 **6종 x 9장 = 54번 요청**이 나가고, 행 규칙을 앱 코드가 동작별로 알아야 한다.
한 장으로 합치면 요청 1번 · 디코딩 1번이고, 앱은 "행 = ROW_MAP" 하나만 알면 된다.

★팩의 행 구성 (실물 확인. Navigation.txt 만 믿으면 틀린다)

  공통 이동계(걷기/먹기/핥기/관찰/냄새/장난) = 행 0~3 이 앞·좌·뒤·우.

  고양이 SITTING·LAYING (8행) : 짝수행 = 서기↔앉기 전환, 홀수행 = 앉은 정지.
                                 (앞 0/1, 좌 2/3, 뒤 4/5, 우 6/7)
  고양이 SLEEPING   (3행)      : 0 = 왼쪽 웅크림(식빵), 1 = 오른쪽 웅크림, 2 = 쭉 뻗은 자세 2컷
  강아지 STANDING   (8행)      : 짝수행 = 정지, 홀수행 = 꼬리 흔들기 (앞 0/1, 좌 2/3, 뒤 4/5, 우 6/7)
  강아지 WALKING    (7행)      : 0 앞 · 2 좌 · 4 뒤 · 5 우 (1·3·6 은 짖으며 걷기 교체용)
  강아지 SITTING    (11행)     : 전환 0·2·5·8 / 정지 1·3·6·9 / 꼬리 4·7·10
  강아지 LAYING     (8행)      : 고양이와 같음 (짝수 전환, 홀수 정지)
  강아지 SLEEPING   (2행)      : 0 왼쪽, 1 오른쪽

★뚱냥이(Cat Fat)만 시트 폭이 다르다 (SITTING 3열, STANDING 4열).
  그래서 프레임 수는 **행마다 실제로 세어서** 기록한다. 상수로 박으면 뚱냥이가 깨진다.

★안 가져오는 것
  RUNNING — 자유 행동에 뛰기가 없다(설계서). 필요해지면 그때 추가한다.
  전환(서기↔앉기) — v1 은 자세만 바꾼다. 행을 비워 두었으니 나중에 채우면 된다.
"""
from __future__ import annotations

import json
import os
import sys

from PIL import Image

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'pets')
PACK = os.path.join(os.path.expanduser('~'), 'Desktop', '머피브랜딩', '머피월드 캐릭터',
                    '커스터마이징 3차', '외부에셋테스트', '펫에셋', 'Top-Down-Pet-Pack v1.1')

CELL = 32
COLS = 6                      # 가장 프레임이 많은 행(고양이 앉은 정지 6프레임)에 맞춘다

# 출력 행 배치 — 앱은 이 순서만 알면 된다. dir 순서는 앞·좌·뒤·우(팩과 동일).
ANIMS = ['walk', 'stand', 'sit', 'eat', 'act1', 'act2', 'sleep', 'lay']
ROW_MAP = {                   # 동작 -> 출력 시작 행
    'walk': 0, 'stand': 4, 'sit': 8, 'eat': 12,
    'act1': 16, 'act2': 20,   # 고양이 = 핥기/관찰, 강아지 = 냄새맡기/장난치기
    'sleep': 24,              # 2행만 쓴다(좌/우)
    'lay': 26,
}
ROWS = 30

PETS = {
    'cat_black': ('Cat Black', 'BLACK_CAT', 'cat'),
    'cat_fat':   ('Cat Fat', 'FAT_CAT', 'cat'),
    'cat_milky': ('Cat Milky', 'MILKY_CAT', 'cat'),
    'dog_brown': ('Dog Brown', 'BROWN_DOG', 'dog'),
    'dog_small': ('Dog Small', 'SMALL_DOG', 'dog'),
    'dog_white': ('Dog White', 'WHITE_DOG', 'dog'),
}

# (파일, 그 파일에서 앞·좌·뒤·우에 해당하는 원본 행)
SRC = {
    'cat': {
        'walk':  ('WALKING',   [0, 1, 2, 3]),
        'stand': ('STANDING',  [0, 1, 2, 3]),
        'sit':   ('SITTING',   [1, 3, 5, 7]),      # 홀수행 = 앉은 정지
        'eat':   ('EATING',    [0, 1, 2, 3]),
        'act1':  ('LICKING',   [0, 1, 2, 3]),      # 그루밍
        'act2':  ('OBSERVING', [0, 1, 2, 3]),      # 가만히 관찰
        'sleep': ('SLEEPING',  [0, 1]),            # 좌·우 웅크림(식빵)
        'lay':   ('LAYING',    [1, 3, 5, 7]),      # 홀수행 = 누운 정지
    },
    'dog': {
        'walk':  ('WALKING',   [0, 2, 4, 5]),      # 1·3·6 은 짖으며 걷기
        'stand': ('STANDING',  [0, 2, 4, 6]),      # 홀수행은 꼬리 흔들기
        'sit':   ('SITTING',   [1, 3, 6, 9]),
        'eat':   ('EATING',    [0, 1, 2, 3]),
        'act1':  ('SNIFFING',  [0, 1, 2, 3]),      # 냄새 맡기
        'act2':  ('PLAYFUL',   [0, 1, 2, 3]),      # 장난치기
        'sleep': ('SLEEPING',  [0, 1]),
        'lay':   ('LAYING',    [1, 3, 5, 7]),
    },
}


def frames_in_row(im, row):
    """그 행에 실제로 그림이 있는 칸 수. 왼쪽부터 세다가 빈 칸이 나오면 멈춘다."""
    cols = im.width // CELL
    n = 0
    for c in range(cols):
        box = (c * CELL, row * CELL, (c + 1) * CELL, (row + 1) * CELL)
        if im.crop(box).getbbox():
            n += 1
        else:
            break
    return n


def build_pet(pet_id, folder, prefix, kind):
    src_dir = os.path.join(PACK, folder, 'SpriteSheets')
    sheet = Image.new('RGBA', (COLS * CELL, ROWS * CELL), (0, 0, 0, 0))
    counts = [0] * ROWS
    warn = []

    for anim, (fname, rows) in SRC[kind].items():
        path = os.path.join(src_dir, '%s_%s.png' % (prefix, fname))
        if not os.path.exists(path):
            raise SystemExit('없는 파일: ' + path)
        im = Image.open(path).convert('RGBA')
        avail = im.height // CELL
        for d, srow in enumerate(rows):
            if srow >= avail:
                warn.append('%s %s 행 %d 없음(총 %d행)' % (pet_id, anim, srow, avail))
                continue
            n = frames_in_row(im, srow)
            if n == 0:
                warn.append('%s %s 행 %d 이 비어 있다' % (pet_id, anim, srow))
                continue
            if n > COLS:
                warn.append('%s %s 행 %d 프레임 %d개 — %d개로 자른다' % (pet_id, anim, srow, n, COLS))
                n = COLS
            trow = ROW_MAP[anim] + d
            strip = im.crop((0, srow * CELL, n * CELL, (srow + 1) * CELL))
            sheet.paste(strip, (0, trow * CELL), strip)
            counts[trow] = n

    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, pet_id + '.png')
    sheet.save(dst)
    # 접지폭 = 서 있는 4방향 중 가장 넓은 것(옆모습이 가장 넓다). 앱의 그림자 타원 폭 기준.
    sbw = max(ground_w(sheet.crop((0, (ROW_MAP['stand'] + d) * CELL, CELL,
                                   (ROW_MAP['stand'] + d + 1) * CELL))) for d in range(4))
    return counts, warn, os.path.getsize(dst), sbw


# ===== 소품 =====
# 방 가구로 등록할 것들. ROOM_ITEMS 의 w/h 는 **PNG 실측이어야 하므로**
# 여기서 최종 표시 크기로 저장한다 = 소스의 2배(NEAREST).
# ★배율은 **펫과 같아야 한다.** 펫을 3배(96유닛)로 키웠는데 소품만 2배로 두었더니
#   밥그릇·뼈다귀가 펫 옆에서 절반 크기로 보였다(대표 8-25: "밥그릇 존나 작아").
#   PET_SCALE(index.html) 과 이 값은 **항상 같이 움직인다.**
PROP_SCALE = 3
ROOMS_DIR = os.path.join(HERE, 'rooms')

# PET_PROPS (6x2 칸). (열, 행) 좌표.
PROPS = [
    ('pet_bone',  (0, 0), None),
    ('pet_fish',  (1, 0), None),
    ('pet_toy',   (1, 1), None),
    # 밥그릇 — 빈 것과 찬 것은 **같은 상자**로 잘라야 밥을 채울 때 그릇이 안 튄다
    ('pet_bowl_red',   (2, 0), (2, 1)),
    ('pet_bowl_blue',  (3, 0), (3, 1)),
    ('pet_bowl_green', (4, 0), (4, 1)),
    ('pet_bowl_wood',  (5, 0), (5, 1)),
]
# 64x64 짜리 큰 소품 (192x64 안에 3개)
BIG = [('CAT_TOWER.png', ['pet_tower_cream', 'pet_tower_purple', 'pet_tower_green']),
       ('DOG_HOUSE.png', ['pet_house_blue', 'pet_house_red', 'pet_house_green'])]


def ground_w(im, band_px=2):
    """바닥 접지폭 = 맨 아랫줄 몇 줄에서 불투명 픽셀이 걸친 가로 폭.

    ROOM_ITEMS 의 sbw 가 이 값이다. 접지 그림자(_mwShadowHtml)가 이걸 기준으로 타원 폭을 잡는다.
    ★그림자는 그림에 굽지 않는다 — 팩 스프라이트에 그림자가 없는 것을 확인했다(알파가 0/255 뿐).
      우리 방식(평평한 타원 div)을 앱에서 얹는다. drop-shadow 필터는 모바일에서 이동할 때
      잔상을 남겨 금지다(index.html .cw-shadow 주석).
    """
    import numpy as _np
    a = _np.asarray(im.convert('RGBA'))[..., 3] > 100
    rows = _np.where(a.any(1))[0]
    if not len(rows):
        return im.width
    bot = rows[-1]
    band = a[max(0, bot - band_px):bot + 1]
    xs = _np.where(band.any(0))[0]
    return int(xs[-1] - xs[0] + 1)


def up(im):
    return im.resize((im.width * PROP_SCALE, im.height * PROP_SCALE), Image.NEAREST)


def union_box(*ims):
    boxes = [i.getbbox() for i in ims if i.getbbox()]
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def build_props():
    src = Image.open(os.path.join(PACK, 'PET_PROPS.png')).convert('RGBA')
    made = []
    for name, a, b in PROPS:
        ca = src.crop((a[0] * CELL, a[1] * CELL, (a[0] + 1) * CELL, (a[1] + 1) * CELL))
        if b is None:
            box = ca.getbbox()
            out = {name: ca.crop(box)}
        else:
            cb = src.crop((b[0] * CELL, b[1] * CELL, (b[0] + 1) * CELL, (b[1] + 1) * CELL))
            box = union_box(ca, cb)
            out = {name: ca.crop(box), name + '_on': cb.crop(box)}
        for n, im in out.items():
            im = up(im)
            im.save(os.path.join(ROOMS_DIR, n + '.png'))
            made.append((n, im.size, ground_w(im, 2 * PROP_SCALE)))

    for fname, names in BIG:
        im = Image.open(os.path.join(PACK, fname)).convert('RGBA')
        w = im.width // len(names)
        for i, n in enumerate(names):
            part = im.crop((i * w, 0, (i + 1) * w, im.height))
            box = part.getbbox()
            if not box:
                continue
            p = up(part.crop(box))
            p.save(os.path.join(ROOMS_DIR, n + '.png'))
            made.append((n, p.size, ground_w(p, 2 * PROP_SCALE)))
    return made


def main():
    meta = {'cell': CELL, 'cols': COLS, 'rows': ROWS, 'anims': ANIMS,
            'rowMap': ROW_MAP, 'dirs': ['front', 'left', 'back', 'right'],
            'scale': PROP_SCALE, 'pets': {}}
    total = 0
    for pet_id, (folder, prefix, kind) in PETS.items():
        counts, warn, size, sbw = build_pet(pet_id, folder, prefix, kind)
        meta['pets'][pet_id] = {'kind': kind, 'frames': counts, 'sbw': sbw}
        total += size
        print('%-10s %s  접지폭 %d/32  %5.1fKB'
              % (pet_id, ''.join(str(min(c, 9)) for c in counts), sbw, size / 1024))
        for w in warn:
            print('   경고: ' + w)

    with open(os.path.join(OUT, 'pets.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print('\n합계 %.1fKB · char/pets/pets.json 기록' % (total / 1024))
    print('행 배치:', ', '.join('%s=%d' % (a, ROW_MAP[a]) for a in ANIMS))

    print('')
    print('--- 소품 (char/rooms/, 표시 크기 = 소스 x%d) ---' % PROP_SCALE)
    for n, size, sbw in build_props():
        print('  %-20s w:%-3d h:%-3d sbw:%d' % (n, size[0], size[1], sbw))
    print('★ROOM_ITEMS 등록 시 w/h/sbw 는 위 실측값 그대로. sbw = 바닥 접지폭(그림자 폭 기준)')


if __name__ == '__main__':
    main()

# ※카탈로그용 그림(char/pets/{id}_face.png)은 서 있는 앞모습 첫 칸을 잘라 2배로 키운 것이다.
#   시트를 그대로 <img> 로 넣으면 30행이 통째로 보인다.
#   ★이름을 _thumb 로 짓지 않았다 — *_thumb.png 는 대표가 직접 준 아이콘 파일만 쓰는 자리다.
