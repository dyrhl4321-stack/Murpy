# -*- coding: utf-8 -*-
"""Pixel Interiors 시트에 **이미 들어 있던 애니메이션 프레임**을 APNG로 묶는다 (2026-08-18).

    python char/animate_pi_props.py "<Pixel Interiors 32x32pxl.png>"

발견
  미사용 스프라이트를 훑다가 머그컵이 24개, 토스터가 8개 나왔다. 처음엔 색상 변형인 줄
  알았는데 크기가 52x48 -> 52x52 -> 52x56 으로 커진다. **애니메이션 프레임이었다** —
  머그는 김이 올라오고, 토스터는 빵이 튀어나온다.
  카탈로그에 32개를 늘어놓을 게 아니라 움직이는 오브젝트 3개로 묶는 게 맞다.

왜 APNG인가 (캠프파이어·공룡과 같은 이유)
  방 렌더(mwFurnHtml)는 아이템을 <img>로 그리고 편집기 드래그도 img[data-idx]를 찾는다.
  스프라이트시트 + CSS steps() 로 가려면 <img>를 div 로 바꿔야 하고 그러면 드래그가 깨진다.
  APNG 는 파일만 갈면 되므로 앱 코드를 한 줄도 안 건드린다.
  저장은 disposal=1(배경 복원) + blend=0(덮어쓰기) — 매 프레임을 통짜로 교체한다.

정렬
  프레임마다 내용 높이가 다르다(김이 길어지니까). 각자 트림하면 컵이 위아래로 튄다.
  -> 세트 전체의 **공통 bbox** 를 먼저 구하고 모든 프레임을 그 상자로 자른다.
"""
import argparse
import os

from PIL import Image

SCALE = 4
ALPHA_CUT = 200          # 시트에 구워진 반투명 그림자를 날린다
ROOMS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rooms')

# (출력이름, 표시이름, 행 y0, y1, 시작 x, 프레임수, 프레임당 ms)
#   x 는 16px 간격이다(시트 격자).
SETS = [
    ('pi_mug_blue',  '파란 머그컵',   300, 320, 350, 6, 260),
    ('pi_mug_red',   '빨간 머그컵',   300, 320, 446, 6, 260),
    # ★시작 x 를 476 -> 480 으로 바로잡았다. 476 이면 격자가 4px 밀려
    #   옆 스프라이트의 세로 조각이 오른쪽에 딸려 들어온다(검수 이미지에서 발견).
    ('pi_toaster_a', '토스터',        232, 258, 480, 4, 320),
]


def frames_of(sheet, y0, y1, x0, n):
    """고정 격자로 잘라낸 뒤 **세트 공통 bbox** 로 다시 자른다(프레임 간 흔들림 방지)."""
    raw = []
    for i in range(n):
        c = sheet.crop((x0 + 16 * i, y0, x0 + 16 * (i + 1), y1))
        r, g, b, a = c.split()
        raw.append(Image.merge('RGBA', (r, g, b, a.point(lambda v: 255 if v >= ALPHA_CUT else 0))))
    boxes = [im.split()[3].getbbox() for im in raw]
    boxes = [b for b in boxes if b]
    if not boxes:
        return []
    L = min(b[0] for b in boxes); T = min(b[1] for b in boxes)
    R = max(b[2] for b in boxes); B = max(b[3] for b in boxes)
    return [im.crop((L, T, R, B)) for im in raw]


def footprint(im):
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

    print('--- ROOM_ITEMS 코드 ---')
    for name, label, y0, y1, x0, n, dur in SETS:
        fr = frames_of(sheet, y0, y1, x0, n)
        if not fr:
            print('  건너뜀 %s' % name)
            continue
        big = [f.resize((f.width * SCALE, f.height * SCALE), Image.NEAREST) for f in fr]
        dst = os.path.join(args.out, name + '.png')
        big[0].save(dst, save_all=True, append_images=big[1:],
                    duration=dur, loop=0, disposal=1, blend=0)
        w, h = big[0].size
        print("  { id:'%s', name:'%s', src:'char/rooms/%s.png?v=1', w:%d, h:%d, sbw:%d, prop:true, price:15 },"
              % (name, label, name, w, h, footprint(big[0])))
        print('      # %d프레임 %dms  %dx%d' % (len(big), dur, w, h))


if __name__ == '__main__':
    main()
