# 누끼용 마젠타 배경(#FF00FF)의 **잔여 픽셀**을 지운다.
#
# AI 는 투명 배경을 못 그려서 형광 마젠타/그린을 깔고 누끼를 딴다(대표 강명령).
# 그때 머리카락처럼 가는 선의 가장자리에는 배경이 섞인 픽셀이 남는다 —
# 알파는 살아 있는데 색만 자주빛인 픽셀이라 누끼 도구가 못 잡는다.
#
# 고치는 법: 마젠타성 픽셀을 **이웃의 정상 색으로 치환**한다. 픽셀아트라 블렌드는 금지 —
# 3x3 이웃 중 정상 픽셀들의 중앙값을 쓰고, 가장자리부터 안쪽으로 여러 번 반복한다.
import sys, os
import numpy as np
from PIL import Image

def magenta_mask(a):
    r, g, b, al = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int), a[..., 3]
    # 마젠타 = R·B 가 G 보다 뚜렷하게 높다. 붉은 살색(R만 높음)·보라 옷(R≈B 지만 G도 따라옴)과 구분된다.
    return (al > 0) & (r > g + 22) & (b > g + 22) & (r > 55) & (b > 45)

def clean(path, out=None, rounds=6):
    im = Image.open(path).convert("RGBA")
    a = np.array(im)
    bad0 = magenta_mask(a)
    total = int(bad0.sum())
    for _ in range(rounds):
        bad = magenta_mask(a)
        if not bad.any(): break
        good = (a[..., 3] > 0) & ~bad
        ys, xs = np.where(bad)
        H, W = bad.shape
        fixed = a.copy()
        for y, x in zip(ys, xs):
            y0, y1 = max(0, y - 1), min(H, y + 2)
            x0, x1 = max(0, x - 1), min(W, x + 2)
            nb = good[y0:y1, x0:x1]
            if not nb.any():
                fixed[y, x, 3] = 0            # 주변이 전부 배경이면 그 픽셀도 배경이다
                continue
            px = a[y0:y1, x0:x1, :3][nb]
            fixed[y, x, :3] = np.median(px, axis=0).astype(np.uint8)
        a = fixed
    left = int(magenta_mask(a).sum())
    a[..., 3] = np.where(a[..., 3] >= 128, 255, 0)     # 알파 128 이진화 (에셋 하드룰)
    Image.fromarray(a, "RGBA").save(out or path)
    print("%s  마젠타 %d -> %d" % (os.path.basename(path), total, left))

if __name__ == "__main__":
    for p in sys.argv[1:]:
        clean(p)
