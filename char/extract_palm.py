# -*- coding: utf-8 -*-
"""머피 범프 손바닥 이펙트 누끼 — 형광초록 배경 제거 + 흰색 통일 + 트림 + 축소.

나노바나나(제미나이)는 투명 배경을 못 그리므로 #00FF00 배경으로 받아서 여기서 뗀다.
([[feedback_nanobanana_chroma_green]])

입력: Desktop\머피브랜딩\...\머피범프이펙트\Gemini_Generated_Image_*.png
출력: char/fx/palm.png  (가로 256, NEAREST — 픽셀아트라 정수 축소·보간 금지)

내부 디테일이 없는 실루엣이므로, 남은 픽셀은 전부 순백으로 통일한다.
그러면 초록 스필(경계에 남는 초록끼)이 원천적으로 사라진다.
"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = (r'C:\Users\allys\Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차'
       r'\머피범프이펙트\Gemini_Generated_Image_368gn9368gn9368g.png')
OUT_DIR = os.path.join(HERE, 'fx')
OUT = os.path.join(OUT_DIR, 'palm.png')
TARGET_W = 256


def is_green(r, g, b):
    """형광초록 계열이면 True. 제미나이 ✦ 워터마크(연초록)도 함께 걸린다."""
    return g > 90 and g > r * 1.12 and g > b * 1.12


def main():
    if not os.path.exists(SRC):
        sys.exit('원본 없음: ' + SRC)
    im = Image.open(SRC).convert('RGBA')
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0 or is_green(r, g, b):
                px[x, y] = (0, 0, 0, 0)
            else:
                px[x, y] = (255, 255, 255, 255)   # 실루엣이므로 순백 통일 = 스필 제거
    bb = im.getbbox()
    if not bb:
        sys.exit('내용이 없습니다 — 초록 판정 기준을 확인하세요')
    im = im.crop(bb)
    print('트림 후 크기:', im.size)
    ratio = TARGET_W / im.size[0]
    out = im.resize((TARGET_W, max(1, round(im.size[1] * ratio))), Image.NEAREST)
    os.makedirs(OUT_DIR, exist_ok=True)
    out.save(OUT)
    print('저장:', OUT, out.size)


if __name__ == '__main__':
    main()
