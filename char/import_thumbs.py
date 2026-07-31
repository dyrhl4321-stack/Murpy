# -*- coding: utf-8 -*-
"""대표가 준 아이콘을 앱 썸네일 크기로 줄여 items/ 에 넣는다.

★썸네일은 대표가 준 아이콘 파일만 쓴다. **자동 크롭 금지** — 줄이기만 한다.
   (헤어만 예외로 정면 전신 렌더를 쓴다 → char/rebuild_hair_thumb.py)
정수배 축소라 NEAREST 로 깔끔하게 줄어든다.

    python char/import_thumbs.py
"""
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "items")
DESK = r"C:\Users\allys\Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차"
DIV = 8          # 정수배 축소 (2048 -> 256)

MAP = [
    ("top_f_hoodzip", r"상의\여캐\썸네일\회색후드집업.png"),
    ("top_f_zipup", r"상의\여캐\썸네일\보라색 후드집업.png"),
    ("bottom_f_leggings", r"바지\여캐\썸네일\챠콜레깅스.png"),
    ("bottom_f_sweatpants", r"바지\여캐\썸네일\회색 츄리닝바지.png"),
]


def main():
    for item, rel in MAP:
        src = os.path.join(DESK, rel)
        if not os.path.exists(src):
            print(f"!! 없음 {rel}")
            continue
        im = Image.open(src).convert("RGBA")
        w, h = im.width // DIV, im.height // DIV
        out = im.resize((w, h), Image.NEAREST)
        p = os.path.join(ITEMS, item + "_thumb.png")
        out.save(p)
        print(f"{im.width}x{im.height} -> {w}x{h}   {item}_thumb.png")


if __name__ == "__main__":
    main()
