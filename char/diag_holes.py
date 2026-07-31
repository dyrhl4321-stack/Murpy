# -*- coding: utf-8 -*-
"""헤어 레이어의 '구멍'을 찾아 지도로 만든다 — 대표가 메울 자리를 찾기 쉽게.

두 종류를 다른 색으로 표시한다:
  마젠타 = 머리카락에 완전히 둘러싸인 **내부 구멍** (base 가 비쳐 보인다)
  시안   = base 영역지도상 머리카락이 덮어야 하는데(MUST) **비어 있는 자리** (두상 노출)

    python char/diag_holes.py hair_f_basic.png human_f
    python char/diag_holes.py                      # 여캐 3종 한꺼번에
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_regions import regions as base_regions   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CW, CH = 141, 224
ALPHA_BIN = 128
ROWS = ["정면", "후면", "좌", "우"]
BASE = {"human": "walk.png", "human_f": "walk_female.png"}
MIN_SHOW = 3          # 이보다 작은 조각은 노이즈라 표에서 뺀다(그림엔 그린다)
SCALE = 5

DEFAULT = [("hair_f_basic.png", "human_f"),
           ("hair_f_bob_bang.png", "human_f"),
           ("hair_f_long.png", "human_f")]


def over(dst, src):
    out = dst.copy()
    m = src[:, :, 3] >= ALPHA_BIN
    out[m] = src[m]
    out[m, 3] = 255
    return out


def analyze(name, body):
    base_name = BASE[body]
    base = np.asarray(Image.open(os.path.join(HERE, base_name)).convert("RGBA")).astype(int)
    hair = np.asarray(Image.open(os.path.join(HERE, "items", name)).convert("RGBA")).astype(int)

    print(f"\n■ {name}")
    tiles = []
    for r in range(4):
        bc = base[r * CH:(r + 1) * CH, 0:CW]
        hc = hair[r * CH:(r + 1) * CH, 0:CW]
        h = hc[:, :, 3] >= ALPHA_BIN

        allholes = ndimage.binary_fill_holes(h) & ~h         # 머리카락에 둘러싸인 빈 자리
        must, keep = base_regions(bc, r, base_name, 0)
        # ★프로필에서 머리카락이 귀를 둘러싸면 귀가 '내부 구멍'으로 잡힌다.
        #   귀는 보여야 정상이다 — 메우면 귀가 사라진다. 반드시 갈라서 보여준다.
        ear = allholes & keep
        holes = allholes & ~keep                             # 진짜 메울 구멍
        bare = must & ~h                                     # 덮어야 하는데 비었다

        comp = over(bc, hc)
        vis = comp.copy()
        vis[bare] = [0, 220, 255, 255]
        vis[holes] = [255, 0, 255, 255]
        vis[ear] = [255, 220, 0, 255]
        tiles.append((ROWS[r], vis))

        def report(mask, lbl):
            lab, n = ndimage.label(mask, np.ones((3, 3), bool))
            if not n:
                print(f"   {ROWS[r]:2s} {lbl}: 없음")
                return
            sizes = ndimage.sum(mask, lab, range(1, n + 1))
            big = [(int(s), i) for i, s in enumerate(sizes, 1) if s >= MIN_SHOW]
            big.sort(reverse=True)
            if not big:
                print(f"   {ROWS[r]:2s} {lbl}: 자잘한 것 {n}개뿐 ({int(mask.sum())}px)")
                return
            parts = []
            for s, i in big[:5]:
                ys, xs = np.where(lab == i)
                parts.append(f"{s}px@x{int(xs.mean())},y{int(ys.mean())}")
            print(f"   {ROWS[r]:2s} {lbl}: {len(big)}곳 {int(mask.sum())}px  " + " · ".join(parts))

        report(holes, "메울 구멍")
        report(ear, "귀 (메우지 말 것)")
        report(bare, "두상노출")

    pad, lbl = 8, 26
    canvas = Image.new("RGB", ((CW + pad) * 4 + pad, CH + lbl + pad * 2), (250, 250, 250))
    for i, (t, a) in enumerate(tiles):
        canvas.paste(Image.fromarray(a.astype(np.uint8), "RGBA").convert("RGB"),
                     (pad + i * (CW + pad), lbl + pad))
    big = canvas.resize((canvas.width * SCALE, canvas.height * SCALE), Image.NEAREST)
    d = ImageDraw.Draw(big)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 30)
    except OSError:
        font = ImageFont.load_default()
    for i, (t, _) in enumerate(tiles):
        d.text(((pad + i * (CW + pad)) * SCALE, 8), t, fill=(20, 20, 20), font=font)
    d.text((10, (lbl + pad + CH) * SCALE - 34),
           "마젠타=메울 구멍   노랑=귀(메우지 말 것)   시안=머리카락이 덮어야 하는데 빈 곳",
           fill=(90, 90, 90), font=font)
    p = os.path.join(HERE, "_diag", f"holes_{name}")
    big.save(p)
    print(f"   -> {p}")
    return p


def main():
    if len(sys.argv) > 2:
        analyze(sys.argv[1], sys.argv[2])
    else:
        for n, b in DEFAULT:
            analyze(n, b)


if __name__ == "__main__":
    main()
