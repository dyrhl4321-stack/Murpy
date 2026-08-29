# -*- coding: utf-8 -*-
"""테스터 모집 인스타 스토리 이미지 (1080x1920).

플레이스토어 비공개 테스트에 12명이 필요해서 근방단에 도움을 청하는 카드다.
★안드로이드 전용이라는 것을 **눈에 띄게** 넣는다 — 아이폰 유저가 지메일만 주면
  카운트가 안 된다(테스터는 플레이스토어에서 실제 설치까지 해야 인정된다).

    python docs/promo/store/make_tester_story.py      # 저장소 루트에서 실행
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
OUT_DIR = os.path.join('docs', 'promo', 'store')
OUT = os.path.join(OUT_DIR, 'tester_story_1080x1920.png')

# ── 배경: og-card 사진을 세로로 깔고 어둡게
src = Image.open('og-card.png').convert('RGB')
sw, sh = src.size
photo = src.crop((int(sw * 0.415), 0, sw, sh))
scale = max(W / photo.size[0], H / photo.size[1])
photo = photo.resize((int(photo.size[0] * scale) + 1, int(photo.size[1] * scale) + 1), Image.LANCZOS)
ox = (photo.size[0] - W) // 2
oy = int((photo.size[1] - H) * 0.35)
canvas = photo.crop((ox, oy, ox + W, oy + H))
canvas = Image.blend(canvas, Image.new('RGB', (W, H), (8, 9, 12)), 0.72)

# 가운데를 더 눌러 글자가 어디서나 읽히게
vign = Image.new('L', (W, H), 0)
ImageDraw.Draw(vign).ellipse([-W * 0.2, H * 0.02, W * 1.2, H * 0.98], fill=140)
vign = vign.filter(ImageFilter.GaussianBlur(140))
canvas.paste(Image.new('RGB', (W, H), (8, 9, 12)), (0, 0), vign)

d = ImageDraw.Draw(canvas)
BLUE = (61, 126, 255)
GOLD = (245, 194, 75)


def font(sz, bold=True):
    noto = r'C:\Windows\Fonts\NotoSansKR-VF.ttf'
    if os.path.exists(noto):
        f = ImageFont.truetype(noto, sz)
        try:
            f.set_variation_by_name('Bold' if bold else 'Regular')
        except Exception:
            pass
        return f
    return ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', sz)


def center(y, text, f, fill):
    w = d.textbbox((0, 0), text, font=f)[2]
    d.text(((W - w) // 2, y), text, font=f, fill=fill)
    return y


# ── 로고
LS = 190
logo = Image.open('logo-nukki.png').convert('RGBA').resize((LS, LS), Image.LANCZOS)
canvas.paste(logo, ((W - LS) // 2, 210), logo)

# ── 제목
center(470, '머피 앱', font(76), (255, 255, 255))
center(560, '출시 준비 중', font(76), (255, 255, 255))

d.rectangle([(W - 90) // 2, 690, (W + 90) // 2, 696], fill=BLUE)

center(740, '플레이스토어 정식 출시 전', font(38, False), (214, 218, 226))
center(796, '테스터 12분을 찾습니다', font(44), (255, 255, 255))

# ── ★안드로이드 전용 (가장 눈에 띄어야 한다)
bx0, bx1, by0, by1 = 150, W - 150, 900, 1030
d.rounded_rectangle([bx0, by0, bx1, by1], radius=20, fill=(28, 18, 20),
                    outline=(232, 131, 138), width=4)
center(925, '안드로이드 폰만 가능', font(46), (255, 255, 255))
center(984, '아이폰은 설치가 안 돼요', font(28, False), (232, 131, 138))

# ── 할 일
center(1104, '순서', font(34), BLUE)
# ★"링크 눌러 테스터 되기"로 적었더니 **아무나 링크만 누르면 되는 것처럼** 읽혔다(대표 8-29).
#   실제로는 그 계정을 테스터 목록에 **먼저 등록**해야 링크가 열린다. 순서를 그대로 적는다.
steps = [
    ('1.', 'DM으로 지메일 주소 보내기'),
    ('2.', '등록해 드리면 링크를 보내요'),
    ('3.', '링크 눌러 설치 · 14일 두기'),
]
y = 1174
for num, txt in steps:
    fb, fr = font(38), font(38, False)
    full = num + '  ' + txt
    x = (W - d.textbbox((0, 0), full, font=fr)[2]) // 2
    d.text((x, y), num, font=fb, fill=BLUE)
    d.text((x + d.textbbox((0, 0), num + '  ', font=fr)[2], y), txt, font=fr, fill=(232, 236, 244))
    y += 66

# ── 보상
center(1430, '참여해 주신 분께', font(30, False), (206, 212, 224))
center(1482, '머피 500 지급', font(52), GOLD)

# ── CTA
cy0, cy1 = 1610, 1720
d.rounded_rectangle([150, cy0, W - 150, cy1], radius=22, fill=BLUE)
center(1642, 'DM으로 지메일 주소 주세요', font(40), (255, 255, 255))

center(1790, 'murpy.app', font(32), (255, 255, 255))

os.makedirs(OUT_DIR, exist_ok=True)
canvas.save(OUT, quality=95)
print(OUT, canvas.size)
