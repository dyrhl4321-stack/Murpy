# -*- coding: utf-8 -*-
"""테니스 타이틀 합성 — AI 배경(글자 없음) + 제미나이 레터링 낱말 두 줄 조립.

    python tools/make_tennis_title.py

★내력 (9-02)
  1차: 제미나이에게 통째로 → '머피 테니스' 철자를 다섯 번 틀림(테느스 ×3, 며표, 태니스).
  2차: 앱 폰트(Galmuri14) → 대표: "글씨가 좀 별론데, 제미나이로 뽑으면 이쁘던데".
  3차(지금): **골프 타이틀의 '홀인 머피'에서 '머피'를 색 마스크로 추출**(철자·레터링 보장) +
       '테니스'는 그것을 레퍼런스로 낱말만 생성한 뒤(철자 눈으로 검수) **형태학 팽창으로 획을
       머피와 같은 두께로** 맞췄다. 두 줄로 쌓아 남은 무게 차이도 안 보이게 했다.
       레터링은 제미나이 그대로, 철자는 사람이 보증한다.

재료(전부 gitignore — 로컬 + 드라이브 백업에만 있다):
  char/game/tennis_title.raw.png        글자 없는 배경 (제미나이)
  char/game/tennis_word_murpy.raw.png   '머피'  (golf_title 추출)
  char/game/tennis_word_tennis.raw.png  '테니스' (제미나이 생성 + 획 팽창)
"""
import os, sys
from PIL import Image

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
G = lambda n: os.path.join(HERE, '..', 'char', 'game', n)


def despeck(im, min_px=30):
    """외딴 잡티 제거 — min_px 미만짜리 연결 조각을 지운다(팽창·추출 과정의 부스러기)."""
    im = im.convert('RGBA')
    w, h = im.size
    a = im.getchannel('A').load()
    seen = [[False] * w for _ in range(h)]
    px = im.load()
    for y in range(h):
        for x in range(w):
            if seen[y][x] or a[x, y] <= 10:
                continue
            stack = [(x, y)]; comp = []
            seen[y][x] = True
            while stack:
                cx, cy = stack.pop(); comp.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and a[nx, ny] > 10:
                        seen[ny][nx] = True; stack.append((nx, ny))
            if len(comp) < min_px:
                for cx, cy in comp:
                    px[cx, cy] = (0, 0, 0, 0)
    return im


bg = Image.open(G('tennis_title.raw.png')).convert('RGBA')
W, H = bg.size                                    # 720x1290

mu = despeck(Image.open(G('tennis_word_murpy.raw.png')))
te = despeck(Image.open(G('tennis_word_tennis.raw.png')))
mu = mu.crop(mu.getbbox())
te = te.crop(te.getbbox())

# 두 줄 — 위 '머피', 아래 '테니스'. 나란히 쓰면 낱말 간 무게 차이가 도드라진다.
CAP = 148
mu2 = mu.resize((round(mu.size[0] * CAP / mu.size[1]), CAP), Image.LANCZOS)
te2 = te.resize((round(te.size[0] * CAP / te.size[1]), CAP), Image.LANCZOS)

y = int(H * 0.085)
bg.alpha_composite(mu2, ((W - mu2.size[0]) // 2, y))
bg.alpha_composite(te2, ((W - te2.size[0]) // 2, y + CAP + 18))

bg.convert('RGB').save(G('tennis_title.png'))
print('저장:', G('tennis_title.png'), bg.size)
