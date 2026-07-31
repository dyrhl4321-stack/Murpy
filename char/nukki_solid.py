# -*- coding: utf-8 -*-
"""단색 배경 누끼 — 형광초록이 아닌 검정·흰색·회색 배경용.

`char/nukki.py` 는 형광초록(#00FF00) 전용이다. 대표가 준 아이콘처럼 **검정/회색 단색**
배경은 초록기로 못 가른다. 그래서 다른 원리를 쓴다:

  ★가장자리에서 **연결된** 배경색만 지운다(flood fill).
    옷 안쪽에 같은 색(검은 지퍼선·회색 원단)이 있어도 배경과 안 이어져 있으면 살아남는다.
    색만 보고 지우면 옷 속 검은 선까지 뚫린다.

경계의 반투명 섞임은 **알파 128 이진화**로 정리한다(앱 하드룰).

    python char/nukki_solid.py <입력.png> -o <출력.png> [--tol 40]
    python char/nukki_solid.py --preset thumbs        # 여캐 썸네일 4종 일괄
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "items")
DESK = r"C:\Users\allys\Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차"
DIV = 8

PRESET_THUMBS = [
    ("top_f_hoodzip", r"상의\여캐\썸네일\회색후드집업.png"),
    ("top_f_zipup", r"상의\여캐\썸네일\보라색 후드집업.png"),
    ("bottom_f_leggings", r"바지\여캐\썸네일\챠콜레깅스.png"),
    ("bottom_f_sweatpants", r"바지\여캐\썸네일\회색 츄리닝바지.png"),
]


def cut_grad(arr, g_tol):
    """그라디언트 배경용 — 색이 아니라 **경계(윤곽선)** 로 자른다.

    배경이 단색이 아니라 은은한 그라디언트면 모서리 색 기준으로는 일부만 잡힌다.
    대신 '색 변화가 완만한 곳'을 후보로 두고, 가장자리에 연결된 덩어리만 배경으로 본다.
    옷 윤곽선에서 변화가 급해 자동으로 멈춘다. 옷 안쪽 평평한 면은 가장자리와
    안 이어져 있어 살아남는다.
    """
    g = arr[:, :, :3].mean(axis=2)
    gy = ndimage.sobel(g, axis=0)
    gx = ndimage.sobel(g, axis=1)
    mag = np.hypot(gx, gy)
    flat = mag < g_tol

    h, w = arr.shape[:2]
    lab, n = ndimage.label(flat, np.ones((3, 3), bool))
    edge_ids = set(lab[0, :]) | set(lab[h - 1, :]) | set(lab[:, 0]) | set(lab[:, w - 1])
    edge_ids.discard(0)
    bgmask = np.isin(lab, list(edge_ids)) if edge_ids else np.zeros_like(flat)
    # 윤곽선 두께만큼 남은 테두리를 조금 더 먹인다 (배경 쪽으로만)
    bgmask = ndimage.binary_dilation(bgmask, np.ones((3, 3), bool), iterations=2) & flat

    out = arr.copy()
    out[bgmask] = 0
    out[:, :, 3] = np.where(bgmask, 0, 255)
    return out, np.median(arr[bgmask][:, :3], axis=0) if bgmask.any() else np.zeros(3), \
        float(bgmask.mean() * 100)


def cut(arr, tol, ncolor=2):
    """배경색을 테두리에서 추정하고, 가장자리에 연결된 그 색만 지운다.

    ★배경이 한 색이라는 보장이 없다. 대표 아이콘은 '투명'을 나타내는 **체크무늬가
      이미지로 구워져** 있었다(흰색+회색 두 색이 격자로 반복). 모서리 한 색만 잡으면
      격자의 다른 색에서 flood 가 막혀 13% 밖에 안 지워진다.
      → 테두리 픽셀의 최빈색을 여러 개 뽑아 전부 배경 후보로 본다.
    """
    h, w = arr.shape[:2]
    border = np.concatenate([arr[0, :, :3], arr[h - 1, :, :3],
                             arr[:, 0, :3], arr[:, w - 1, :3]])
    uniq, cnt = np.unique(border // 8, axis=0, return_counts=True)   # 8단계로 뭉쳐 최빈색
    order = np.argsort(-cnt)[:ncolor]
    bgs = [uniq[i] * 8 + 4 for i in order]
    close = np.zeros((h, w), bool)
    for bg1 in bgs:
        close |= np.abs(arr[:, :, :3] - bg1).sum(axis=2) <= tol
    bg = bgs[0]

    # 가장자리에 닿은 덩어리만 배경으로 본다
    lab, n = ndimage.label(close, np.ones((3, 3), bool))
    edge_ids = set(lab[0, :]) | set(lab[h - 1, :]) | set(lab[:, 0]) | set(lab[:, w - 1])
    edge_ids.discard(0)
    bgmask = np.isin(lab, list(edge_ids)) if edge_ids else np.zeros_like(close)

    keep = ~bgmask
    # ✦ 워터마크 같은 작은 고립 조각 제거 (옷 본체는 한 덩어리다)
    lab2, n2 = ndimage.label(keep, np.ones((3, 3), bool))
    if n2 > 1:
        sizes = ndimage.sum(keep, lab2, range(1, n2 + 1))
        big = int(np.argmax(sizes)) + 1
        for i, s in enumerate(sizes, start=1):
            if i != big and s < sizes.max() * 0.02:      # 본체의 2% 미만이면 조각
                keep[lab2 == i] = False
        bgmask = ~keep

    out = arr.copy()
    out[bgmask] = 0
    out[:, :, 3] = np.where(bgmask, 0, 255)
    return out, bg, float(bgmask.mean() * 100)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?")
    ap.add_argument("-o", "--out")
    ap.add_argument("--tol", type=int, default=40)
    ap.add_argument("--grad", type=float, default=0,
                    help="그라디언트 배경 모드. 임계(예: 6). 0이면 색 거리 모드")
    ap.add_argument("--preset")
    args = ap.parse_args()

    jobs = []
    if args.preset == "thumbs":
        for item, rel in PRESET_THUMBS:
            jobs.append((os.path.join(DESK, rel),
                         os.path.join(ITEMS, item + "_thumb.png"), True))
    elif args.src:
        jobs.append((args.src, args.out or (os.path.splitext(args.src)[0] + "-nukki.png"), False))
    else:
        print(__doc__)
        return

    for src, dst, shrink in jobs:
        if not os.path.exists(src):
            print(f"!! 없음 {src}")
            continue
        arr = np.asarray(Image.open(src).convert("RGBA")).astype(int)
        out, bg, pct = (cut_grad(arr, args.grad) if args.grad else cut(arr, args.tol))
        im = Image.fromarray(out.astype(np.uint8), "RGBA")
        if shrink:
            # ★정수배 축소만. 크롭은 하지 않는다(대표 아이콘 원형 유지).
            im = im.resize((im.width // DIV, im.height // DIV), Image.NEAREST)
            a = np.asarray(im).astype(int).copy()
            a[:, :, 3] = np.where(a[:, :, 3] >= 128, 255, 0)
            a[a[:, :, 3] == 0] = 0
            im = Image.fromarray(a.astype(np.uint8), "RGBA")
        im.save(dst)
        print(f"배경 RGB{tuple(int(v) for v in bg)} 제거 {pct:4.1f}%  -> {os.path.basename(dst)}"
              f"  {im.width}x{im.height}")


if __name__ == "__main__":
    main()
