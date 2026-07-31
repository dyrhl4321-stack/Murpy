# -*- coding: utf-8 -*-
"""헤어 썸네일만 다시 만든다 (빌더를 다시 돌리지 않고).

썸네일 규칙은 build_hair_layer.py 와 같다 — **정면 전신 렌더**(base + 헤어, 알파 bbox 크롭).
헤어는 대표 아이콘이 없는 예외 슬롯이라 자동 렌더가 허용된다.
※ 다른 슬롯의 *_thumb.png 는 대표가 준 아이콘 파일이다. 자동 크롭 금지.

    python char/rebuild_hair_thumb.py hair_m_semileaf human
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "items")
CW, CH = 141, 224
BASE = {"human": "walk.png", "human_f": "walk_female.png"}


def main():
    item = sys.argv[1] if len(sys.argv) > 1 else "hair_m_semileaf"
    body = sys.argv[2] if len(sys.argv) > 2 else "human"

    base = Image.open(os.path.join(HERE, BASE[body])).convert("RGBA")
    hair = Image.open(os.path.join(ITEMS, item + ".png")).convert("RGBA")

    t = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    t.alpha_composite(base.crop((0, 0, CW, CH)))
    t.alpha_composite(hair.crop((0, 0, CW, CH)))
    ta = np.asarray(t)[:, :, 3]
    ys, xs = np.where(ta > 0)
    out = t.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    p = os.path.join(ITEMS, item + "_thumb.png")
    out.save(p)
    print(f"-> {p}  {out.width}x{out.height}")


if __name__ == "__main__":
    main()
