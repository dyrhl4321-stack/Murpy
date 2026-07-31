# -*- coding: utf-8 -*-
"""아이템 시트의 특정 방향(row)만 옛 커밋 버전으로 되돌린다.

방향별로 상태가 다르므로(한 방향은 좋아지고 다른 방향은 나빠짐) 통째 롤백은 쓰면 안 된다.
되돌릴 방향만 골라서 바꾼다.

    python char/revert_row.py hair_m_semileaf.png 671c2c5 0            # 미리보기
    python char/revert_row.py hair_m_semileaf.png 671c2c5 0 --apply
옛 버전 파일은 char/_diag/hist/<sha>.png 에 있어야 한다:
    cmd /c "git show <sha>:char/items/<name> > char\\_diag\\hist\\<sha>.png"
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
CW, CH = 141, 224
ALPHA_BIN = 128
ROWS = ["정면", "후면", "좌", "우"]


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return
    name, sha, row = sys.argv[1], sys.argv[2], int(sys.argv[3])
    apply = "--apply" in sys.argv

    p_cur = os.path.join(HERE, "items", name)
    cur = np.asarray(Image.open(p_cur).convert("RGBA")).astype(int)
    old = np.asarray(Image.open(os.path.join(HERE, "_diag", "hist", f"{sha}.png"))
                     .convert("RGBA")).astype(int)
    if cur.shape != old.shape:
        print(f"!! 규격 불일치 {cur.shape} vs {old.shape}")
        return

    out = cur.copy()
    y0, y1 = row * CH, (row + 1) * CH
    before = int((cur[y0:y1, :, 3] >= ALPHA_BIN).sum())
    out[y0:y1] = old[y0:y1]
    # 알파 128 이진화 하드룰 — 되돌린 구간도 반투명이 남으면 안 된다
    a = out[y0:y1, :, 3]
    out[y0:y1, :, 3] = np.where(a >= ALPHA_BIN, 255, 0)
    after = int((out[y0:y1, :, 3] >= ALPHA_BIN).sum())
    print(f"{name}  {ROWS[row]}(row{row}) → {sha}   헤어 픽셀 {before} → {after}")

    if apply:
        Image.fromarray(out.astype(np.uint8), "RGBA").save(p_cur)
        print(f"-> 적용됨 {p_cur}")
    else:
        p = os.path.join(HERE, "_diag", f"revert_{name}")
        Image.fromarray(out.astype(np.uint8), "RGBA").save(p)
        print(f"-> 미리보기 {p}  (적용하려면 --apply)")


if __name__ == "__main__":
    main()
