# -*- coding: utf-8 -*-
"""대표가 준 아이템 썸네일 원본에서 배경을 빼고 카드용으로 다듬는다.

★썸네일은 **대표가 준 파일만** 쓴다(캐릭터 시트에서 자동으로 잘라 만들지 않는다).
  여기서 하는 일은 배경 제거 · 파편 제거 · 트림 · 축소뿐이다.

★파편을 먼저 지우고 트림한다. 떨어진 점 하나가 남으면 바운딩 박스가 그만큼 커지고,
  카드에서 높이 52px 로 맞출 때 **물건이 그만큼 작아 보인다**(대표 8-27: "썸네일도
  딱 깔끔하게 크기 맞춰서"). 실제로 브라탑·망고나시에 흰 점이 하나씩 남아 있었다.
"""
import argparse, os
import numpy as np
from PIL import Image


def clean(src, out, flip=False, maxside=256, min_frag=40, log=print):
    im = Image.open(src).convert("RGBA")
    a = np.array(im).astype(int)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    # 형광 마젠타/그린 · 흰 배경 · 이미 투명한 곳을 배경으로 본다
    # ★g<70 을 빼면 안 된다 — 분홍·보라 **옷 색까지** 배경으로 걸려 드레스 안쪽이 비었다.
    #   형광 마젠타는 G 가 거의 0 이다. 남는 보라 점은 아래 '바깥 잔여'가 잡는다.
    bg = (((r > g + 40) & (b > g + 40) & (g < 70))
          | ((g > r + 40) & (g > b + 40))
          | (al < 128)
          | ((r > 240) & (g > 240) & (b > 240)))
    keep = ~bg
    # ★잔여물 제거 — **가장 큰 덩어리의 테두리 밖**에 있는 것만 버린다.
    #   "가장 큰 덩어리만 남기기"는 쓰면 안 된다: 옷은 윤곽선과 색면이 서로 다른 덩어리라
    #   드레스 치마 안쪽이 통째로 날아간다(실제로 131,771 px 이 사라졌다).
    #   물건은 가운데 모여 있고 배경 잔여는 바깥에 흩어져 있다 — 그 차이만 쓴다.
    try:
        from scipy import ndimage
        lab, n = ndimage.label(keep)
        if n > 1:
            sizes = ndimage.sum(keep, lab, range(1, n + 1))
            big = int(np.argmax(sizes)) + 1
            ys, xs = np.where(lab == big)
            y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
            drop = 0
            for i in range(1, n + 1):
                if i == big:
                    continue
                iy, ix = np.where(lab == i)
                inside = (iy.min() >= y0 and iy.max() <= y1 and ix.min() >= x0 and ix.max() <= x1)
                if not inside:                       # 테두리 밖으로 삐져나온 것 = 배경 잔여
                    keep[lab == i] = False; drop += int(sizes[i - 1])
            if drop: log("  바깥 잔여 %d px 제거" % drop)
    except ImportError:
        pass
    o = np.array(im); o[..., 3] = np.where(keep, 255, 0)
    im2 = Image.fromarray(o, "RGBA")
    bb = im2.split()[3].point(lambda v: 255 if v > 50 else 0).getbbox()
    if bb:
        im2 = im2.crop(bb)
    k = maxside / max(im2.size)
    if k < 1:
        im2 = im2.resize((max(1, round(im2.width * k)), max(1, round(im2.height * k))), Image.LANCZOS)
    if flip:
        im2 = im2.transpose(Image.FLIP_LEFT_RIGHT)
    im2.save(out)
    log("%-24s -> %s%s" % (os.path.basename(src), im2.size, "  (좌우반전)" if flip else ""))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--flip", action="store_true", help="파일명이 좌우반전을 지시할 때")
    a = ap.parse_args()
    clean(a.src, a.out, a.flip)
