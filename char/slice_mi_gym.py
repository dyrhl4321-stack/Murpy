# -*- coding: utf-8 -*-
"""LimeZu Modern Interiors(48px)에서 **운동기구**를 방 오브젝트로 잘라낸다 (2026-08-17).

    python char/slice_mi_gym.py "<...\\Theme_Sorter_Shadowless_Singles_48x48>"

왜 이 팩인가 / 왜 Shadowless 인가
  기존 가구는 Pixel Interiors(32px) 시트를 4배로 쓴 것이고, 이건 다른 팩(48px)이다.
  섞으면 톤이 갈리므로 5330개 중에서 **우리 가구 팔레트와의 거리를 픽셀로 재서** 추렸다
  (기존 가구 픽셀 47만 개 -> 대표색 16개 -> 후보의 각 픽셀이 그 팔레트에서 떨어진 평균).
  ★Theme_Sorter_Shadowless_Singles = **그림자가 안 구워진** 개별 PNG.
    대표 8-16: "새로 받아온 에셋들 그림자가 좀 개판이다. 우리가 만든 버전으로 다 바꿔야 해."
    -> 애초에 그림자 없는 버전이 따로 있어서 지울 필요가 없다. 접지 그림자는 앱이 CSS로 만든다
       (알파 실측 -> clip-path 평행사변형 1.18배 + blur. 대칭마름모/타원 금지).

배율은 2배다 (기존 가구는 4배)
  원본이 48px 이라 2배면 우리 4배(32px) 가구와 실제 크기가 맞는다 — 실측으로 확인했다
  (우리 책장 96x184 vs 이 팩 옷장 96x192). 정수배만 쓴다(픽셀 아트 하드룰).

대표가 고른 것 (5330 -> 후보 96 -> 30 제안 -> 대표 확정 11)
  "1부터 8 넣고 스피커만 넣자. 나머지는 거의 중복도 많고, 요가 매트라고 가져온 건 그냥 타일임."
  ★요가 매트로 착각한 것은 바닥 타일이었다 — 내 오독. 빼냈다.
  ★대표가 다음순위 폴더에서 **덤벨 방향 변형**을 찾아냈다("오히려 덤벨 방향 바꾼 거였음").
    그래서 방향 짝을 다시 훑어 바벨·덤벨에 세로 버전을 붙였다.
  ★찾다가 걸린 덤벨 랙·케틀벨도 대표 승인으로 넣는다("둘 다 넣고").
"""
import argparse
import os

from PIL import Image

SCALE = 2
ALPHA_CUT = 128
ROOMS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rooms')

GYM = '8_Gym_Singles_Shadowless_48x48/Gym_Singles_Shadowless_48x48_%d.png'
MUS = '6_Music_and_Sport_Shadowless_48x48/Music_and_Sport_Singles_Shadowless_48x48_%d.png'

# (파일명, 표시이름, 원본경로템플릿, 번호)
# ★이름은 **확대해서 보고** 붙였다. 앞서 '주방 카운터'·'하이 테이블'을 쓰임새로 지어내
#   두 번 틀렸다(대표 지적). 재질과 생긴 것을 먼저 본다.
ITEMS = [
    ('mi_barbell',       '바벨',          GYM,  89),   # 봉 + 양쪽 원판
    # ★g98 은 '가로 바벨의 세로 버전'으로 묶지 않았다 — 원판이 둥글고 두꺼워 **같은 물건으로 안 보인다.**
    #   돌렸을 때 다른 물건으로 변하는 것이 하이테이블에서 겪은 실패다(대표가 '크기가 튄다'로 잡아냄).
    #   그래서 별개 아이템 '세워둔 바벨'로 넣는다. 덤벨은 대표가 직접 방향 짝이라고 확인해줘서 묶었다.
    ('mi_barbell_up',    '세워둔 바벨',    GYM,  98),
    # ★g90(봉 아래에 프레임이 하나 더 있는 것)은 뺐다 — 대표 8-17:
    #   "저건 거치대에 올려져 있는 거네. 일단 저건 애매할 수도 있으니 빼자."
    #   바벨인지 거치대인지 한눈에 안 읽히는 물건은 방에 놔도 무슨 물건인지 모른다.
    ('mi_barbell_heavy', '중량 바벨',      GYM,  87),   # 봉이 더 굵고 원판이 크다
    ('mi_dumbbell',      '덤벨',          GYM, 108),
    ('mi_dumbbell_d1',   '덤벨(세로)',     GYM, 142),
    ('mi_dumbbell_heavy','중량 덤벨',      GYM, 140),   # 원판이 여러 겹
    ('mi_plate_tower',   '원판 타워',      GYM, 164),
    ('mi_plate',         '원판',          GYM, 163),
    ('mi_plate_pile',    '원판 무더기',    GYM, 165),
    ('mi_dumbbell_rack', '덤벨 랙',       GYM,  86),   # 2단 거치대에 덤벨이 꽂혀 있다
    ('mi_kettlebell',    '케틀벨',        GYM, 155),   # 손잡이 달린 것
    ('mi_speaker',       '스피커',        MUS, 183),   # 체크무늬는 그릴 텍스처다(반투명 0, 10색 실측)
]


def solid_bbox(im):
    a = im.split()[3]
    return a.point(lambda v: 255 if v >= ALPHA_CUT else 0).getbbox()


def footprint(im):
    """바닥 접지폭 = 하단 12% 구간의 불투명 픽셀 가로 범위. 접지 그림자를 이 폭에 맞춘다."""
    w, h = im.size
    px = im.load()
    band = max(4, int(h * 0.12))
    xs = [x for y in range(h - band, h) for x in range(w) if px[x, y][3] > 0]
    return (max(xs) - min(xs) + 1) if xs else w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('singles_dir', help='Theme_Sorter_Shadowless_Singles_48x48 폴더')
    ap.add_argument('--out', default=ROOMS)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    made = []
    for name, label, tpl, num in ITEMS:
        src = os.path.join(args.singles_dir, tpl % num)
        if not os.path.exists(src):
            print('  없음 %s -> %s' % (name, src))
            continue
        im = Image.open(src).convert('RGBA')
        bb = solid_bbox(im)
        if not bb:
            print('  건너뜀 %s: 내용 없음' % name)
            continue
        im = im.crop(bb)                       # 여백 제거 — 남기면 배치 좌표가 실제 형태와 어긋난다
        r, g, b, a = im.split()
        im = Image.merge('RGBA', (r, g, b, a.point(lambda v: 255 if v >= ALPHA_CUT else 0)))
        w, h = im.size
        big = im.resize((w * SCALE, h * SCALE), Image.NEAREST)
        big.save(os.path.join(args.out, name + '.png'))
        sbw = footprint(big)
        made.append((name, label, big.size[0], big.size[1], sbw))
        print('  %-20s %2dx%-2d -> %3dx%-3d  sbw %-3d  %s'
              % (name, w, h, big.size[0], big.size[1], sbw, label))

    print('\n--- ROOM_ITEMS 코드 ---')
    for name, label, w, h, sbw in made:
        print("  { id:'%s', name:'%s', src:'char/rooms/%s.png?v=1', w:%d, h:%d, sbw:%d, price:TODO },"
              % (name, label, name, w, h, sbw))


if __name__ == '__main__':
    main()
