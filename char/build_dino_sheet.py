# -*- coding: utf-8 -*-
"""아기 공룡 APNG(둥가둥가)를 가로 스프라이트 시트로 펼친다.

    python char/build_dino_sheet.py

왜 필요한가 — 방에 **움직이는** 공룡(펫/어슬렁)은 <img> APNG 로는 못 그린다.
APNG 는 재생 위치를 코드가 못 잡아서 걷기↔대기 전환이 안 되고, 마리마다 디코딩이 따로 돈다.
가로 시트 + CSS steps 는 디코딩 1회를 전 마리가 공유하고 전환도 클래스 하나로 끝난다.

★그림은 한 픽셀도 안 바꾼다. s2608_dino.png 의 8프레임을 그대로 옆으로 늘어놓기만 한다.
  프레임 간격도 균등 120ms(실측)라 CSS `steps(8)` + `0.96s` 로 동일하게 재생된다.

★가만히 있는 공룡(기존 방에 놓인 장식)은 이 시트를 안 쓴다. 지금처럼 APNG <img> 그대로다 —
  mwFurnHtml 이 <img> 라서 스프라이트로 바꾸면 꾸미기 배치 드래그가 깨진다(animate_dino.py 주석).

출력: char/rooms/s2608_dino_idle_sheet.png  (94*8 x 105)
"""
from PIL import Image
import os

SRC = os.path.join('char', 'rooms', 's2608_dino.png')
OUT = os.path.join('char', 'rooms', 's2608_dino_idle_sheet.png')


def main():
    im = Image.open(SRC)
    n = getattr(im, 'n_frames', 1)
    if n < 2:
        raise SystemExit('APNG 가 아닙니다(프레임 1개). 애니 원본을 확인하세요: ' + SRC)
    w, h = im.size
    sheet = Image.new('RGBA', (w * n, h), (0, 0, 0, 0))
    prev = None
    for i in range(n):
        im.seek(i)
        f = im.convert('RGBA')
        # 같은 그림이 연속으로 나오면 PIL 이 합성을 못 한 것 — 조용히 넘어가면 애니가 죽는다.
        if prev is not None and f.tobytes() == prev:
            print('  경고: 프레임 %d 가 앞 프레임과 완전히 같습니다' % i)
        prev = f.tobytes()
        sheet.paste(f, (w * i, 0))
    sheet.save(OUT)
    print('%s  (%dx%d, %d프레임, 셀 %dx%d)' % (OUT, sheet.width, sheet.height, n, w, h))


if __name__ == '__main__':
    main()
