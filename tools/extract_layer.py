# -*- coding: utf-8 -*-
"""정합된 worn 시트(몸+옷)에서 **옷 레이어만** 뽑는다.  worn - base = item.

리터치 스튜디오는 아이템 레이어를 편집한다(몸이 아니라). 그래서 fit_sheet 로 정합한
worn 을 그대로 열 수 없고, 여기서 한 번 걸러야 한다.

규칙(customizer_cli 의 교훈 그대로):
 - base 와 색이 다르고, **살색이 아닌** 픽셀만 아이템으로 본다.
 - 작은 파편은 버린다(추출 잔여물이 '왼쪽 검은 줄'로 남은 사고가 있었다).
 - 안쪽 구멍은 **채우지 않는다.** 2D 로 둘러싸였다고 옷 안쪽이 아니다 —
   겨드랑이 틈·목덜미가 그렇게 몸에 옷 색으로 칠해졌다(asset-studio/README 실측).
 - 알파 128 이진화 (에셋 하드룰)
"""
import argparse, os
import numpy as np
from PIL import Image

CW, CH, COLS, ROWS = 141, 224, 3, 4


def is_skin(rgb):
    r, g, b = rgb[..., 0].astype(int), rgb[..., 1].astype(int), rgb[..., 2].astype(int)
    mx = rgb[..., :3].max(2).astype(int); mn = rgb[..., :3].min(2).astype(int)
    L = (mx + mn) / 2.0 / 255.0
    return (r > g + 12) & (g >= b) & (L > 0.28) & (r > 95)


def drop_small(alpha, min_px):
    """프레임마다 연결성분을 세어 작은 조각을 버린다."""
    from collections import deque
    a = alpha.copy()
    for r in range(ROWS):
        for c in range(COLS):
            ys, xs = slice(r * CH, (r + 1) * CH), slice(c * CW, (c + 1) * CW)
            sub = a[ys, xs] > 0
            seen = np.zeros_like(sub)
            for y in range(CH):
                for x in range(CW):
                    if not sub[y, x] or seen[y, x]:
                        continue
                    q = deque([(y, x)]); seen[y, x] = True; comp = []
                    while q:
                        cy, cx = q.popleft(); comp.append((cy, cx))
                        for dy, dx in ((-1,0),(1,0),(0,-1),(0,1)):
                            ny, nx = cy+dy, cx+dx
                            if 0 <= ny < CH and 0 <= nx < CW and sub[ny, nx] and not seen[ny, nx]:
                                seen[ny, nx] = True; q.append((ny, nx))
                    if len(comp) < min_px:
                        for cy, cx in comp:
                            a[r*CH+cy, c*CW+cx] = 0
    return a


def extract(worn_path, base_path, out_path, thr=40, min_px=12, log=print):
    w = np.array(Image.open(worn_path).convert("RGBA")).astype(int)
    b = np.array(Image.open(base_path).convert("RGBA")).astype(int)
    if w.shape != b.shape:
        raise SystemExit("worn/base 규격이 다르다: %s vs %s" % (w.shape, b.shape))
    d = np.abs(w[..., :3] - b[..., :3]).sum(2) + np.abs(w[..., 3] - b[..., 3])
    item = (d > thr) & (w[..., 3] > 128) & ~is_skin(w)
    alpha = np.where(item, 255, 0).astype(np.uint8)
    before = int((alpha > 0).sum())
    alpha = drop_small(alpha, min_px)
    out = np.zeros_like(w, dtype=np.uint8)
    out[..., :3] = w[..., :3].astype(np.uint8)
    out[..., 3] = alpha
    out[..., :3] = np.where(alpha[..., None] > 0, out[..., :3], 0)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    Image.fromarray(out, "RGBA").save(out_path)
    log("%-24s 아이템 %d px (파편 %d 제거) -> %s"
        % (os.path.basename(worn_path), int((alpha > 0).sum()), before - int((alpha > 0).sum()), out_path))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--worn", required=True); ap.add_argument("--base", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--thr", type=int, default=40)
    a = ap.parse_args()
    extract(a.worn, a.base, a.out, a.thr)
