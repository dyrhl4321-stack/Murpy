# -*- coding: utf-8 -*-
"""플레이스토어 그래픽 이미지(1024x500) — og-card.png 를 그대로 재구성한다.
og-card 는 이미 대표가 승인해서 카톡 공유에 쓰는 카드다. 새로 디자인하지 않는다.
"""
import io, os
from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 500
SRC = 'og-card.png'          # 1200x630
OUT = os.path.join(os.environ.get('TMPDIR', '.'), 'feature_graphic.png')

src = Image.open(SRC).convert('RGB')
sw, sh = src.size

# ── 사진 부분만 잘라 온다. og-card 는 오른쪽 약 58%~ 가 사진이다(실측: x≈500/1200).
PHOTO_X0 = int(sw * 0.415)
photo = src.crop((PHOTO_X0, 0, sw, sh))

# 1024x500 중 오른쪽 56% 를 사진이 차지한다
pw = int(W * 0.56)
# 높이에 맞춰 비율 유지 후 가운데 자르기
scale = H / photo.size[1]
nw = int(photo.size[0] * scale)
photo = photo.resize((nw, H), Image.LANCZOS)
if nw > pw:
    off = (nw - pw) // 2
    photo = photo.crop((off, 0, off + pw, H))
else:
    pw = nw

canvas = Image.new('RGB', (W, H), (10, 10, 10))
canvas.paste(photo, (W - pw, 0))

# ── 사진 왼쪽에 검정 그라데이션을 겹쳐 글자가 사진 위로 자연스럽게 이어지게
grad = Image.new('L', (240, 1), 0)
for x in range(240):
    grad.putpixel((x, 0), int(255 * (1 - x / 240)))
grad = grad.resize((240, H))
black = Image.new('RGB', (240, H), (10, 10, 10))
canvas.paste(black, (W - pw, 0), grad)

d = ImageDraw.Draw(canvas)

def font(sz, bold=True):
    # Pretendard 가 없으면 맑은 고딕. 둘 다 없으면 기본.
    for p in [r'C:\Windows\Fonts\malgunbd.ttf' if bold else r'C:\Windows\Fonts\malgun.ttf',
              r'C:\Windows\Fonts\malgun.ttf']:
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()

# ── 로고 (누끼 원본을 흰 원 안에 그대로)
# ★로고 파일에 MURPY 글자가 이미 들어 있다 — 워드마크를 따로 찍으면 두 번 나온다.
logo = Image.open('logo-nukki.png').convert('RGBA')
LS = 118
logo = logo.resize((LS, LS), Image.LANCZOS)
canvas.paste(logo, (64, 62), logo)

# ── 카피 (og-card 와 같은 문장)
d.text((64, 214), '운동을 좋아하는', font=font(48), fill=(255, 255, 255))
d.text((64, 274), '사람들은', font=font(48), fill=(255, 255, 255))

# 파란 구분선 (브랜드 블루 #3D7EFF)
d.rectangle([64, 348, 118, 352], fill=(61, 126, 255))

d.text((64, 378), '아직 만나지 못했을 뿐.', font=font(23, False), fill=(214, 218, 226))

# 하단 도메인
d.text((64, 434), 'murpy.app', font=font(22), fill=(61, 126, 255))

canvas.save(OUT, quality=95)
print(OUT, canvas.size)
