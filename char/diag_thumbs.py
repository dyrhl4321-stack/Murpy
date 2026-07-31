# -*- coding: utf-8 -*-
"""썸네일을 체크무늬 위에 나란히 놓고 누끼 상태를 본다.

    python char/diag_thumbs.py top_f_hoodzip top_f_zipup bottom_f_leggings bottom_f_sweatpants
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "items")
BOX = 300
SCALE = 1


def main():
    names = sys.argv[1:]
    pad, lbl = 10, 26
    W = (BOX + pad) * len(names) + pad
    canvas = Image.new("RGB", (W, BOX + lbl + pad * 2), (250, 250, 250))
    d = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 16)
    except OSError:
        font = ImageFont.load_default()

    for i, n in enumerate(names):
        p = os.path.join(ITEMS, n + "_thumb.png")
        x = pad + i * (BOX + pad)
        # 체크무늬 바닥
        chk = Image.new("RGB", (BOX, BOX), (235, 235, 235))
        cd = ImageDraw.Draw(chk)
        for yy in range(0, BOX, 16):
            for xx in range(0, BOX, 16):
                if ((xx // 16) + (yy // 16)) % 2:
                    cd.rectangle([xx, yy, xx + 15, yy + 15], fill=(205, 205, 205))
        if os.path.exists(p):
            im = Image.open(p).convert("RGBA")
            chk.paste(im, ((BOX - im.width) // 2, (BOX - im.height) // 2), im)
            a = np.asarray(im).astype(int)
            op = (a[:, :, 3] >= 128).mean() * 100
            d.text((x, 4), f"{n}  불투명 {op:.0f}%", fill=(20, 20, 20), font=font)
        else:
            d.text((x, 4), f"{n}  없음", fill=(200, 0, 0), font=font)
        canvas.paste(chk, (x, lbl + pad))

    out = os.path.join(HERE, "_diag", "thumbs.png")
    canvas.save(out)
    print(f"-> {out}")


if __name__ == "__main__":
    main()
