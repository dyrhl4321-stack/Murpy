# -*- coding: utf-8 -*-
"""추출된 옷 시트에서 **본체와 떨어진 조각**을 버린다.

대표 2026-08-27: "왜 우리 워크플로우대로 상의 추출이면 상의 근처만 추출해야 하는데
                  계속 다른 애들도 추출해버리는 거임?"

영역(SLOT_REGIONS)은 지켰는데 상의 영역이 y67~188 로 넓어서, 그 안의
팔 그림자·목·머리카락 끝·하의 허리가 같이 잡힌다. 크기 임계(min_frag=40)로는
150·139·135px 같은 **큰 조각**을 못 거른다.

판정: 옷 한 벌은 프레임마다 **한 덩어리**다. 본체(가장 큰 덩어리)의 일정 비율보다
작으면서 **본체 테두리 밖**에 있는 조각은 잔여물이다.
 ★"가장 큰 것만 남기기"는 쓰지 않는다 — 윤곽선과 색면이 갈린 옷에서 안쪽이 통째로 날아간다
   (썸네일에서 드레스 치마 131,771px 을 날린 적이 있다).
"""
import argparse, os
import numpy as np
from PIL import Image
from scipy import ndimage

CW, CH, COLS, ROWS = 141, 224, 3, 4


def run(path, out_path=None, ratio=0.12, log=print):
    a = np.array(Image.open(path).convert("RGBA"))
    total = 0
    for r in range(ROWS):
        for c in range(COLS):
            ys, xs = slice(r * CH, (r + 1) * CH), slice(c * CW, (c + 1) * CW)
            cell = a[ys, xs]
            m = cell[..., 3] > 128
            lab, n = ndimage.label(m, structure=np.ones((3, 3)))
            if n <= 1:
                continue
            sizes = ndimage.sum(m, lab, range(1, n + 1))
            big = int(np.argmax(sizes)) + 1
            by, bx = np.where(lab == big)
            y0, y1, x0, x1 = by.min(), by.max(), bx.min(), bx.max()
            drop = 0
            for i in range(1, n + 1):
                if i == big:
                    continue
                if sizes[i - 1] >= sizes[big - 1] * ratio:
                    continue                        # 본체에 견줄 만큼 크면 옷의 일부로 본다
                iy, ix = np.where(lab == i)
                inside = (iy.min() >= y0 and iy.max() <= y1 and ix.min() >= x0 and ix.max() <= x1)
                if inside:
                    continue                        # 본체 테두리 안쪽이면 장식일 수 있다
                cell[..., 3][lab == i] = 0
                drop += int(sizes[i - 1])
            if drop:
                log("  r%dc%d  떨어진 조각 %d px 제거" % (r, c, drop))
            total += drop
    a[..., 3] = np.where(a[..., 3] >= 128, 255, 0)
    Image.fromarray(a, "RGBA").save(out_path or path)
    log("총 %d px 제거 -> %s" % (total, out_path or path))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("item")
    ap.add_argument("--out")
    ap.add_argument("--ratio", type=float, default=0.12,
                    help="본체 대비 이 비율보다 작은 조각만 버린다")
    a = ap.parse_args()
    run(a.item, a.out, a.ratio)
