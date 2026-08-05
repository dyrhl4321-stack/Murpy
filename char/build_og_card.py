# -*- coding: utf-8 -*-
"""카톡·SNS 링크 미리보기용 OG 카드(1200x630)를 만든다.

왜 필요한가
  OG 태그가 하나도 없어서 카카오톡이 <title> 과 아무 이미지(머피 코인)를 긁어다 썼다.
  근방단에 링크를 뿌리기 전에 첫인상이 되는 그림이라 제대로 만들어야 한다(대표 지시 2026-08-05).

레이아웃 = 좌우 분할
  왼쪽 500px  #0a0a0a 패널 — 로고 + 카피 + 주소
  오른쪽 700px 히어로 사진(onboarding1.png)
  ★사진 위에 글씨를 얹지 않는다. 이 사진은 인물이 가운데에 있어서 어디에 얹어도
    얼굴이나 팔에 걸린다. 스크림을 진하게 깔면 사진이 죽는다. 그래서 아예 나눈다.

카피는 스플래시 1페이지와 같은 것을 쓴다 — 링크를 눌러 들어오면 같은 문장이 나와야
"같은 서비스"로 읽힌다.

    python char/build_og_card.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

W, H = 1200, 630
PANEL = 500                      # 왼쪽 검정 패널 폭
BG = (10, 10, 10)                # theme-color 와 동일
BLUE = (37, 99, 235)             # 스플래시 액센트와 동일 #2563EB
FONT_B = r"C:\Windows\Fonts\malgunbd.ttf"
FONT_R = r"C:\Windows\Fonts\malgun.ttf"


def main():
    card = Image.new("RGB", (W, H), BG)

    # ---- 오른쪽: 히어로 사진 ----
    photo = Image.open(os.path.join(ROOT, "onboarding1.png")).convert("RGB")
    pw, ph = W - PANEL, H
    # 세로 사진(941x1672)에서 '손 - 얼굴 - 스카이라인 - 다리'가 다 들어가는 띠를 잘라 쓴다.
    # 위쪽 하늘만 잡으면 허전하고, 아래 도로만 잡으면 인물이 잘린다.
    src_w = photo.width
    src_h = int(src_w * ph / pw)
    top = 700                                   # 손끝 조금 위 (실측)
    top = min(top, photo.height - src_h)
    crop = photo.crop((0, top, src_w, top + src_h)).resize((pw, ph), Image.LANCZOS)
    card.paste(crop, (PANEL, 0))

    # 패널과 사진 경계를 부드럽게 — 딱 잘리면 붙여놓은 티가 난다
    fade = Image.new("L", (90, H), 0)
    fd = ImageDraw.Draw(fade)
    for x in range(90):
        fd.line([(x, 0), (x, H)], fill=int(255 * (1 - x / 90)))
    card.paste(Image.new("RGB", (90, H), BG), (PANEL, 0), fade)

    d = ImageDraw.Draw(card)

    # ---- 왼쪽: 로고 ----
    logo = Image.open(os.path.join(ROOT, "logo-nukki.png")).convert("RGBA")
    la = logo.split()[3].getbbox()
    logo = logo.crop(la)
    lh = 132
    logo = logo.resize((round(logo.width * lh / logo.height), lh), Image.LANCZOS)
    card.paste(logo, (64, 92), logo)

    # ---- 카피 (스플래시 1페이지와 동일) ----
    f1 = ImageFont.truetype(FONT_B, 40)
    f2 = ImageFont.truetype(FONT_R, 21)
    f3 = ImageFont.truetype(FONT_B, 20)

    y = 92 + lh + 46
    for line in ["운동을 좋아하는", "사람들은"]:
        d.text((64, y), line, font=f1, fill=(255, 255, 255))
        y += 50

    y += 16
    d.rounded_rectangle([64, y, 64 + 40, y + 4], radius=2, fill=BLUE)
    y += 26

    d.text((64, y), "아직 만나지 못했을 뿐.", font=f2, fill=(255, 255, 255, 200))

    # ---- 주소 ----
    d.text((64, H - 62), "murpy.app", font=f3, fill=BLUE)

    out = os.path.join(ROOT, "og-card.png")
    card.save(out, quality=92)
    print(f"저장 {out}  {card.size}  {os.path.getsize(out):,} bytes")


if __name__ == "__main__":
    main()
