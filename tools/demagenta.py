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

def magenta_mask(a, kind="magenta"):
    r, g, b, al = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int), a[..., 3]
    if kind == "green":
        # 형광 그린 = G 가 R·B 보다 뚜렷하게 높다. 살색·분홍·회색 어디에도 없는 조합이다.
        return (al > 0) & (g > r + 22) & (g > b + 22) & (g > 60)
    if kind == "green-bleed":
        # ★배경이 **밝은 색 위로 번진 것**. 흰 레이스 가장자리가 민트(#BAF9CE)가 된다.
        #   형광 그린 자체는 아니라 위 판정에 안 걸리는데, 눈에는 확실히 초록으로 보인다.
        #   자연 색에는 'G 만 18 이상 높고 전체가 밝은' 조합이 거의 없다.
        return (al > 0) & (g > r + 18) & (g > b + 18) & (g > 150)
    # 마젠타 = R·B 가 G 보다 뚜렷하게 높다. 붉은 살색(R만 높음)·보라 옷(R≈B 지만 G도 따라옴)과 구분된다.
    return (al > 0) & (r > g + 22) & (b > g + 22) & (r > 55) & (b > 45)

def edge_band(alpha, width=2):
    """불투명 영역의 **가장자리 띠**. 누끼 잔여물은 여기에만 생긴다."""
    op = alpha > 0
    band = np.zeros_like(op)
    cur = op.copy()
    for _ in range(width):
        sh = np.zeros_like(cur)
        sh[1:, :] |= ~cur[:-1, :]; sh[:-1, :] |= ~cur[1:, :]
        sh[:, 1:] |= ~cur[:, :-1]; sh[:, :-1] |= ~cur[:, 1:]
        e = cur & sh
        band |= e
        cur = cur & ~e
    return band


def clean(path, out=None, rounds=6, kind="magenta", width=2, anywhere=False):
    """누끼 배경의 **잔여 픽셀**을 이웃 정상 색으로 치환한다.

    ★처리 대상은 **알파 경계 띠 안**으로 한정한다. 색만 보고 지우면 같은 색 옷을 뜯는다 —
      핑크 드레스에 마젠타 판정을 걸어 58,888 픽셀을 뭉개 옷을 망가뜨린 적이 있다
      (2026-08-26). 옷 안쪽은 경계가 아니므로 이 방식에선 절대 건드려지지 않는다.
    ★픽셀아트라 블렌드는 금지 — 3x3 이웃 정상 픽셀의 중앙값을 쓰고 바깥부터 반복한다.
    """
    im = Image.open(path).convert("RGBA")
    a = np.array(im)
    # anywhere = 경계 띠 제한을 푼다. **그 색이 옷에 없다고 확신할 때만** 쓴다
    #   (민트 번짐처럼 자연 색과 겹치지 않는 경우).
    band = np.ones(a.shape[:2], bool) if anywhere else edge_band(a[..., 3], width)
    total = int((magenta_mask(a, kind) & band).sum())
    inner = int((magenta_mask(a, kind) & ~band & (a[..., 3] > 0)).sum())
    for _ in range(rounds):
        bad = magenta_mask(a, kind) & band
        if not bad.any():
            break
        good = (a[..., 3] > 0) & ~magenta_mask(a, kind)
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
            fixed[y, x, :3] = np.median(a[y0:y1, x0:x1, :3][nb], axis=0).astype(np.uint8)
        a = fixed
    left = int((magenta_mask(a, kind) & band).sum())
    a[..., 3] = np.where(a[..., 3] >= 128, 255, 0)     # 알파 128 이진화 (에셋 하드룰)
    Image.fromarray(a, "RGBA").save(out or path)
    print("%-26s %s 가장자리 %d -> %d   (안쪽 %d개는 옷으로 보고 그대로 둠)"
          % (os.path.basename(path), kind, total, left, inner))


if __name__ == "__main__":
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    kind = ("green-bleed" if "--green-bleed" in sys.argv
            else ("green" if "--green" in sys.argv else "magenta"))
    aw = "--anywhere" in sys.argv
    for p in args:
        clean(p, kind=kind, anywhere=aw)
