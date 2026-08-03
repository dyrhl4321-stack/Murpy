# -*- coding: utf-8 -*-
"""헤어×모자 조합 시트의 썸네일을 만든다 (리터치 도구 목록용).

조합 시트는 `<헤어>__<모자>.png` 인데 썸네일이 없어서 도구 목록에서 깨져 보인다.
헤어와 같은 규칙(정면 전신 렌더)으로 만들되 **모자까지 얹어** 어떤 조합인지 알아보게 한다.
※ 다른 슬롯의 *_thumb.png 는 대표가 준 아이콘이다. 자동 생성은 헤어 계열만.

    python char/build_combo_thumbs.py
"""
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "items")
CW, CH = 141, 224
ALPHA_BIN = 128
BASEW = {"human": "walk.png", "human_f": "walk_female.png"}

HAIRS = {
    "human": ["hair_m_basic", "hair_ivyleague", "hair_m_semileaf"],
    "human_f": ["hair_f_basic", "hair_f_bob_bang", "hair_f_long"],
}
HATS = ["hat_beanie", "hat_ladodgers"]


def over(dst, src):
    m = src[:, :, 3] >= ALPHA_BIN
    dst[m] = src[m]
    dst[m, 3] = 255
    return dst


def main():
    n = 0
    for body, hairs in HAIRS.items():
        base = np.asarray(Image.open(os.path.join(HERE, BASEW[body]))
                          .convert("RGBA")).astype(int)
        for h in hairs:
            for hat in HATS:
                vid = f"{h}__{hat}"
                pv = os.path.join(ITEMS, vid + ".png")
                ph = os.path.join(ITEMS, hat + ".png")
                if not (os.path.exists(pv) and os.path.exists(ph)):
                    continue
                va = np.asarray(Image.open(pv).convert("RGBA")).astype(int)
                hta = np.asarray(Image.open(ph).convert("RGBA")).astype(int)
                comp = base[0:CH, 0:CW].copy()
                comp = over(comp, va[0:CH, 0:CW])
                comp = over(comp, hta[0:CH, 0:CW])
                a = comp[:, :, 3]
                ys, xs = np.where(a > 0)
                im = Image.fromarray(comp.astype(np.uint8), "RGBA").crop(
                    (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
                q = os.path.join(ITEMS, vid + "_thumb.png")
                im.save(q)
                print(f"-> {vid}_thumb.png  {im.width}x{im.height}")
                n += 1
    print(f"\n{n}개 생성")


if __name__ == "__main__":
    main()
