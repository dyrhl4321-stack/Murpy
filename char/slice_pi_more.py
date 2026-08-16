# -*- coding: utf-8 -*-
"""Pixel Interiors 시트에서 **방향 변형이 실제로 있는** 가구를 더 잘라낸다 (2026-08-16).

    python char/slice_pi_more.py "<Pixel Interiors 32x32pxl.png>"

왜 이 스크립트가 따로 있나
  slice_pi_furniture.py 는 첫 도입(8-05) 때 쓴 좌표표다. 그때는 '정면 한 장'만 골랐다.
  대표 8-16: "의자·티비 같은 일부만 돌릴 수 있어서 사람들이 아쉬워한다. 4방향이 아니어도
  위아래·좌우 2방향이면 된다." → 시트를 알파 연결요소로 **전부**(106개) 다시 훑어서
  같은 물건의 다른 각도가 있는 것만 추려냈다. 그 결과가 아래 표다.

★좌우 반전(scaleX(-1))은 쓰지 않는다 (대표 8-16 강명령).
  반전은 회전이 아니라 **다른 물건**이 된다 — 손잡이가 반대로 가고, 픽셀 아트는 광원이
  고정이라 명암까지 뒤집힌다. 돌리기는 실제 방향 그림이 있을 때만 준다.

좌표는 연결요소 실측이다(char 폴더에서 다시 재려면 아래 find_boxes 참조).
"""
import argparse
import os

from PIL import Image

SCALE = 4
SHADOW_CUT = 200          # 시트에 구워진 그림자(반투명)를 날린다 — 접지 그림자는 앱이 CSS로 만든다
ROOMS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rooms')

# (파일명, 표시이름, x0, y0, x1, y1)
# ── 기존 가구에 '뒷면'을 붙이는 것 ────────────────────────────────
#    앞면은 손잡이가 보이고 뒷면은 판만 있다 — 벽을 등지고 놓을 때 뒷면이 맞다.
ITEMS = [
    ('pi_nightstand_d1', '협탁(뒤)',        199,  69, 217,  89),
    ('pi_lowtable_d1',   '낮은 탁자(뒤)',   162,  69, 190,  89),

    # ── 신규: 나무 의자 4방향 ────────────────────────────────────
    #    안락의자 말고 **식탁 의자**다. 시트에 4방향이 온전히 있다.
    #    ★방향을 확대해서 눈으로 확인하고 바로잡았다 — 좌석이 **앞으로 나온 쪽**이 정면이다.
    #      처음엔 반대로 넣었다가 검수 미리보기에서 걸렀다.
    #      측면은 등받이 기둥이 있는 쪽이 뒤 → 기둥이 오른쪽이면 왼쪽을 보는 것.
    ('pi_chair',    '나무 의자',       265,  66, 280,  92),
    ('pi_chair_d1', '나무 의자(뒤)',   233,  69, 248,  92),
    ('pi_chair_d2', '나무 의자(좌)',   265,  98, 280, 124),
    ('pi_chair_d3', '나무 의자(우)',   233,  98, 248, 124),

    # ── 신규: 하이 테이블 2방향 ──────────────────────────────────
    ('pi_hightable',    '하이 테이블',      164, 106, 187, 153),
    ('pi_hightable_d1', '하이 테이블(뒤)',  197, 111, 220, 153),

    # ── 신규: 조리대 2종 × 2방향 ────────────────────────────────
#    ★'주방 카운터'라고 붙였다가 대표 지적으로 고쳤다 — **싱크가 없다.**
#      시트에는 싱크 달린 것이 따로 있다(163,224~221,254). 그건 '싱크대'다.
#      상판+문짝 = 조리대 / 상판+서랍 = 주방 서랍장.
    ('pi_counter',        '조리대',       171, 195, 212, 222),
    ('pi_counter_d1',     '조리대(뒤)',   171, 259, 212, 286),
    ('pi_counter_s',      '주방 서랍장',       229, 195, 251, 222),
    ('pi_counter_s_d1',   '주방 서랍장(뒤)',   229, 259, 251, 286),
]


def solid_bbox(im):
    """반투명(구운 그림자)을 뺀 **본체**의 bbox. 여백째 저장하면 배치 좌표가 어긋난다."""
    a = im.split()[3]
    return a.point(lambda v: 255 if v >= SHADOW_CUT else 0).getbbox()


def footprint(im):
    """바닥 접지폭 = 하단 12% 구간의 불투명 픽셀 가로 범위. 접지 그림자를 이 폭에 맞춘다."""
    w, h = im.size
    px = im.load()
    band = max(4, int(h * 0.12))
    xs = [x for y in range(h - band, h) for x in range(w) if px[x, y][3] > 0]
    return (max(xs) - min(xs) + 1) if xs else w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sheet')
    ap.add_argument('--out', default=ROOMS)
    args = ap.parse_args()

    sheet = Image.open(args.sheet).convert('RGBA')
    os.makedirs(args.out, exist_ok=True)
    made = []
    for name, label, x0, y0, x1, y1 in ITEMS:
        crop = sheet.crop((x0, y0, x1, y1))
        bb = solid_bbox(crop)
        if not bb:
            print('  건너뜀 %s: 내용 없음' % name)
            continue
        crop = crop.crop(bb)
        r, g, b, a = crop.split()
        crop = Image.merge('RGBA', (r, g, b, a.point(lambda v: 255 if v >= SHADOW_CUT else 0)))
        w, h = crop.size
        big = crop.resize((w * SCALE, h * SCALE), Image.NEAREST)
        big.save(os.path.join(args.out, name + '.png'))
        made.append((name, label, big, footprint(big)))
        print('  %-20s %2dx%-2d -> %3dx%-3d  sbw %-3d  %s'
              % (name, w, h, big.size[0], big.size[1], footprint(big), label))

    print('\n--- dirs 코드 조각 ---')
    for name, label, big, sbw in made:
        print("{src:'char/rooms/%s.png?v=1',w:%d,h:%d,sbw:%d}," % (name, big.size[0], big.size[1], sbw))


if __name__ == '__main__':
    main()
