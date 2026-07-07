# -*- coding: utf-8 -*-
"""
회색 버뮤다 팬츠(bottom_bermuda) 추출.
소스: 우리 캐릭터가 회색 7부 버뮤다를 입은 4방향 시트(투명 PNG).
회색=중성색(chroma 낮음, 중간밝기)만 하반신 영역에서 per-frame 추출 →
base walk.png의 남색 반바지를 완전히 덮는 회색 7부 바지 레이어.
"""
import os
from PIL import Image
import extract_item as E

SRC = r"C:\Users\won\Desktop\김현수 컴카드\머피브랜딩\머피월드 캐릭터\캐릭터스프라이트시트\아이템\아이템착용스프라이트시트\버뮤다팬츠-Photoroom.png"

def gray_judge(px):
    """회색 바지: 중성색(무채도) + 중간밝기. 살색(주황·고채도)·파란셔츠·갈색신발·검정외곽선 제외."""
    r, g, b, a = px
    if a < 60:
        return False
    br = max(r, g, b); mn = min(r, g, b)
    chroma = br - mn
    return chroma <= 24 and 92 <= br <= 216

CFG = dict(
    src=SRC,
    out="bottom_bermuda",
    # detect_grid()로 측정한 소스 4행×3열 밴드
    rows=[(10, 367), (384, 741), (760, 1116), (1134, 1487)],
    cols=[(9, 223), (246, 457), (482, 693)],
    region=(0.50, 0.90),   # 허리 아래 ~ 신발 바로 위(7부). 셔츠(상)·신발(하) 배제
    per_frame=True,        # 걸을 때 다리 움직임 → 프레임별 추출
    min_component=12,      # 잔여 도트 제거
    dilate=1, dilate_ymin=0.50, dilate_solid=False,  # 가장자리 1px 팽창(밑옷 삐짐 방지)
)

# 대표가 준 아이템 아이콘(썸네일용). 가이드: 캐릭터 자동크롭 ❌, 대표 아이콘 엄격 알파크롭.
THUMB_SRC = r"C:\Users\won\Desktop\김현수 컴카드\머피브랜딩\머피월드 캐릭터\캐릭터스프라이트시트\아이템\회색버뮤다팬츠-Photoroom.png"

def build_thumb():
    im = Image.open(THUMB_SRC).convert("RGBA")
    # 엄격 알파(>50)로 여백 바짝 크롭
    a = im.split()[3]
    mask = a.point(lambda v: 255 if v > 50 else 0)
    bb = mask.getbbox()
    if bb:
        im = im.crop(bb)
    # 다른 아이템 썸네일 규격(최대 256px)에 맞춰 축소
    MAXD = 256
    if max(im.size) > MAXD:
        sc = MAXD / max(im.size)
        im = im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS)
    out = os.path.join(E.HERE, "items", "bottom_bermuda_thumb.png")
    im.save(out)
    print("saved thumb", out, im.size)

if __name__ == "__main__":
    E.build(CFG, judge=gray_judge)
    build_thumb()
