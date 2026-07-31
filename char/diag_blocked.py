# -*- coding: utf-8 -*-
"""원본에 있는데 아직 못 되살린 머리카락이 **무엇에 막혀 있는지** 사유별로 가른다.

복원 조건은 4개다. 어느 조건이 얼마나 막고 있는지 알아야 뭘 풀지 정할 수 있다.
  ① KEEP(얼굴 앞면·귀 보호)   ② 기존 헤어에서 떨어져 있음   ③ 밝기 상한   ④ 이미 있음

    python char/diag_blocked.py hair_f_long.png human_f 0 1
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_regions import regions as base_regions   # noqa: E402
from build_hair_layer import (BALD_M, BALD_F, CW, CH, ALPHA_BIN,   # noqa: E402
                              Norm, load, pad_img, binarize)
from restore_from_source import SOURCE, is_skin, hair_lum_max, GROW   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = ["정면", "후면", "좌", "우"]
BASEW = {"human": "walk.png", "human_f": "walk_female.png"}
BALD = {"human": BALD_M, "human_f": BALD_F}
SCALE = 5


def main():
    name, body = sys.argv[1], sys.argv[2]
    rows = [int(x) for x in sys.argv[3:]] or [0, 1]
    walk = np.asarray(Image.open(os.path.join(HERE, BASEW[body])).convert("RGBA")).astype(int)
    cur = np.asarray(Image.open(os.path.join(HERE, "items", name)).convert("RGBA")).astype(int)
    norm = Norm(load(BALD[body]))
    src_pad = pad_img(load(SOURCE[name]))
    lum = hair_lum_max(cur)
    print(f"■ {name}  머리색 밝기상한 {lum:.0f}")

    tiles = []
    for r in rows:
        worn = binarize(norm.cell(src_pad, r, 0))
        wm = ((worn[:, :, 3] >= ALPHA_BIN) & ~is_skin(worn)
              & (worn[:, :, :3].mean(axis=2) < lum))
        bc = walk[r * CH:(r + 1) * CH, 0:CW]
        hc = cur[r * CH:(r + 1) * CH, 0:CW]
        h = hc[:, :, 3] >= ALPHA_BIN
        _must, keep = base_regions(bc, r, BASEW[body], 0)
        near = ndimage.binary_dilation(h, np.ones((3, 3), bool), iterations=GROW)

        missing = wm & ~h
        by_keep = missing & keep
        by_far = missing & ~keep & ~near
        ok = missing & ~keep & near
        print(f"\n  {ROWS[r]}  아직 없는 머리카락 {int(missing.sum())}px")
        print(f"    ① KEEP(얼굴·귀)에 막힘        {int(by_keep.sum()):5d}px")
        print(f"    ② 기존 헤어에서 떨어져 있음    {int(by_far.sum()):5d}px")
        print(f"    ③ 조건 통과인데 남음(재적용요)  {int(ok.sum()):5d}px")

        vis = bc.copy()
        vis[h] = hc[h]
        vis[by_far] = [255, 160, 0, 255]
        vis[by_keep] = [255, 0, 255, 255]
        vis[ok] = [0, 255, 90, 255]
        tiles.append((f"{ROWS[r]}", vis))

    pad, lbl = 8, 26
    canvas = Image.new("RGB", ((CW + pad) * len(tiles) + pad, CH + lbl + pad * 2), (248, 248, 248))
    for i, (_t, a) in enumerate(tiles):
        canvas.paste(Image.fromarray(a.astype(np.uint8), "RGBA").convert("RGB"),
                     (pad + i * (CW + pad), lbl + pad))
    big = canvas.resize((canvas.width * SCALE, canvas.height * SCALE), Image.NEAREST)
    d = ImageDraw.Draw(big)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 30)
    except OSError:
        font = ImageFont.load_default()
    for i, (t, _a) in enumerate(tiles):
        d.text(((pad + i * (CW + pad)) * SCALE, 6), t, fill=(20, 20, 20), font=font)
    d.text((10, big.height - 34), "마젠타=얼굴·귀 보호에 막힘  주황=헤어에서 떨어짐  초록=통과",
           fill=(90, 90, 90), font=font)
    p = os.path.join(HERE, "_diag", f"blocked_{name}")
    big.save(p)
    print(f"\n-> {p}")


if __name__ == "__main__":
    main()
