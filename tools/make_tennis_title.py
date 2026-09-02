# -*- coding: utf-8 -*-
"""테니스 타이틀 합성 — AI 배경(글자 없음) + Galmuri14 로 직접 그린 제목.

    python tools/make_tennis_title.py

★왜 이렇게 하나 (9-02): 제미나이가 '머피 테니스' 철자를 네 번 연속 틀렸다
  (테느스 ×3, 며표 테니스 ×1). 한글 철자를 못 믿는다.
  그래서 배경은 AI 로 받고(char/game/tennis_title.raw.png = 글자 없는 판),
  제목은 앱이 머피월드 전체에 실제로 쓰는 픽셀 폰트 Galmuri14 로 얹는다.
  획 테두리·그림자·글자별 튀는 배치로 게임 타이틀 느낌을 낸다.

폰트 준비(최초 1회 — 앱이 쓰는 그 CDN):
    curl -sL -o tools/galmuri14.woff2 https://cdn.jsdelivr.net/npm/galmuri@2.40.3/dist/Galmuri14.woff2
    python -c "from fontTools.ttLib import TTFont; f=TTFont('tools/galmuri14.woff2'); f.flavor=None; f.save('tools/galmuri14.ttf')"
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
BG = os.path.join(HERE, '..', 'char', 'game', 'tennis_title.raw.png')   # 글자 없는 배경
OUT = os.path.join(HERE, '..', 'char', 'game', 'tennis_title.png')
FONT = os.path.join(HERE, 'galmuri14.ttf')

bg = Image.open(BG).convert('RGBA')
W, H = bg.size                       # 720x1290

TITLE = '머피 테니스'
NAVY = (31, 42, 68, 255)             # 진한 남색 테두리(덤벨·골프 제목과 같은 계열)
WHITE = (255, 255, 255, 255)

font = ImageFont.truetype(FONT, 104)

# 글자마다 따로 그려서 살짝 아래위로 튀게 — 일렬로 쭉 쓰면 문서 제목처럼 굳는다
layer = Image.new('RGBA', (W, 300), (0, 0, 0, 0))
d = ImageDraw.Draw(layer)
bounce = [0, 10, 0, -8, 6, -4]       # '머 피 (공백) 테 니 스'
widths = []
for ch in TITLE:
    bb = d.textbbox((0, 0), ch, font=font, stroke_width=8)
    widths.append(bb[2] - bb[0] if ch != ' ' else 34)
x = (W - sum(widths)) // 2
for i, ch in enumerate(TITLE):
    if ch == ' ':
        x += widths[i]
        continue
    y = 80 + bounce[i]
    # 그림자 → 테두리 → 본체
    d.text((x + 6, y + 10), ch, font=font, fill=(15, 20, 35, 160), stroke_width=8, stroke_fill=(15, 20, 35, 160))
    d.text((x, y), ch, font=font, fill=WHITE, stroke_width=8, stroke_fill=NAVY)
    x += widths[i]

# 제목 밴드 위치 = 덤벨·골프와 같은 위쪽 1/3 지점
bg.alpha_composite(layer, (0, int(H * 0.135)))
bg.convert('RGB').save(OUT)
print('저장:', OUT, bg.size)
