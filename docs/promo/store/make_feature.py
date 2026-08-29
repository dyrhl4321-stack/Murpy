# -*- coding: utf-8 -*-
"""플레이스토어 그래픽 이미지(1024x500).

★구글은 이 배너를 기기·지면마다 **다르게 잘라서** 보여준다(좌우 또는 위아래).
  그래서 중요한 것(로고·한 문장)은 반드시 **가운데**에 있어야 살아남는다.
  왼쪽에 몰아 두면 미리보기부터 글자가 날아간다(대표 8-29 확인).

사진·문장은 og-card.png(카톡 공유 카드, 대표 승인본)와 같은 것을 쓴다.
새로 디자인하지 않는다.

    python docs/promo/store/make_feature.py         # 저장소 루트에서 실행
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1024, 500
SRC = 'og-card.png'
OUT_DIR = os.path.join('docs', 'promo', 'store')
OUT = os.path.join(OUT_DIR, 'feature_graphic_1024x500.png')

# ── 배경: og-card 의 사진을 화면 전체에 깐다(잘려도 사진은 어디를 봐도 사진이다)
src = Image.open(SRC).convert('RGB')
sw, sh = src.size
photo = src.crop((int(sw * 0.415), 0, sw, sh))      # 오른쪽 사진 부분만

scale = max(W / photo.size[0], H / photo.size[1])
photo = photo.resize((int(photo.size[0] * scale) + 1, int(photo.size[1] * scale) + 1),
                     Image.LANCZOS)
ox = (photo.size[0] - W) // 2
oy = int((photo.size[1] - H) * 0.42)                # 인물 얼굴/상체가 살도록 살짝 위에서
canvas = photo.crop((ox, oy, ox + W, oy + H))

# ── 사진 위에 어두운 막을 덮는다. 글자가 어디에 놓여도 읽힌다.
veil = Image.new('RGB', (W, H), (8, 9, 12))
canvas = Image.blend(canvas, veil, 0.62)

# 가운데를 한 번 더 눌러 준다(비네트) — 글자 뒤가 가장 어둡다
vign = Image.new('L', (W, H), 0)
vd = ImageDraw.Draw(vign)
vd.ellipse([-W * 0.15, -H * 0.55, W * 1.15, H * 1.55], fill=150)
vign = vign.filter(ImageFilter.GaussianBlur(90))
canvas.paste(Image.new('RGB', (W, H), (8, 9, 12)), (0, 0), vign)

d = ImageDraw.Draw(canvas)


def font(sz, bold=True):
    for p in [(r'C:\Windows\Fonts\malgunbd.ttf' if bold else r'C:\Windows\Fonts\malgun.ttf'),
              r'C:\Windows\Fonts\malgun.ttf']:
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def center(y, text, f, fill):
    w = d.textbbox((0, 0), text, font=f)[2]
    d.text(((W - w) // 2, y), text, font=f, fill=fill)


# ── 로고 (가운데 위). 로고 파일에 MURPY 글자가 이미 들어 있다 — 워드마크를 또 찍지 않는다.
logo = Image.open('logo-nukki.png').convert('RGBA').resize((104, 104), Image.LANCZOS)
canvas.paste(logo, ((W - 104) // 2, 62), logo)

# ── 한 문장 (og-card 와 같은 카피를 한 줄로)
center(196, '운동을 좋아하는 사람들은', font(52), (255, 255, 255))
center(266, '아직 만나지 못했을 뿐.', font(52), (255, 255, 255))

# 브랜드 블루 구분선
d.rectangle([(W - 64) // 2, 348, (W + 64) // 2, 352], fill=(61, 126, 255))

center(378, '같이 운동할 사람을 찾고, 인증하고, 기록하는 운동 커뮤니티',
       font(24, False), (206, 212, 224))
center(430, 'murpy.app', font(24), (61, 126, 255))

os.makedirs(OUT_DIR, exist_ok=True)
canvas.save(OUT, quality=95)
print(OUT, canvas.size)
