# -*- coding: utf-8 -*-
"""
검정 러닝화(shoes_black) 재추출 — 버그 수정.
문제: 이전 추출이 검정 판정식으로 소스의 '짙은 남색 반바지'까지 신발로 오인 →
      신발이 정강이까지 길어지고 발목 스킨이 반투명 구멍이 됨. 버뮤다와 겹쳐 바지가 투명해 보임.
수정: 발끝 영역(y 0.87~1.0)만, 스킨(살색) 제외하고 추출 → 흰 신발처럼 발에만 컴팩트.
"""
import os
from PIL import Image
import extract_item as E

SSDIR = r"C:\Users\won\Desktop\김현수 컴카드\머피브랜딩\머피월드 캐릭터\캐릭터스프라이트시트\아이템"
SRC = os.path.join(SSDIR, "아이템착용스프라이트시트", "검정러닝화-Photoroom.png")
THUMB_SRC = os.path.join(SSDIR, "검정러닝화-Photoroom.png")  # 대표 제공 아이콘

def shoe_judge(px):
    """발끝 영역 안에서 신발만: 살색(발목 스킨) 제외한 불투명 픽셀."""
    r, g, b, a = px
    if a < 90:                       # 반투명 halo 배제(구멍/비침 방지)
        return False
    is_skin = (r > 110 and r > g + 20 and r > b + 35)   # 발목 스킨 제외
    return not is_skin

CFG = dict(
    src=SRC,
    out="shoes_black",
    rows=[(10, 371), (383, 744), (756, 1116), (1129, 1484)],
    cols=[(10, 223), (246, 456), (481, 691)],
    region=(0.87, 1.00),   # 발끝만(남색 반바지·정강이 배제)
    per_frame=True,        # 걸을 때 발 위치 이동
    min_component=10,      # 잔여 도트 제거
)

def build_thumb():
    im = Image.open(THUMB_SRC).convert("RGBA")
    bb = im.split()[3].point(lambda v: 255 if v > 50 else 0).getbbox()
    if bb: im = im.crop(bb)
    MAXD = 256
    if max(im.size) > MAXD:
        sc = MAXD / max(im.size)
        im = im.resize((round(im.width*sc), round(im.height*sc)), Image.LANCZOS)
    out = os.path.join(E.HERE, "items", "shoes_black_thumb.png")
    im.save(out); print("saved thumb", out, im.size)

if __name__ == "__main__":
    E.build(CFG, judge=shoe_judge)
    build_thumb()
