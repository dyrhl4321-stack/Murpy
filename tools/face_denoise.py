# -*- coding: utf-8 -*-
"""얼굴 시트의 **지정한 네모 구간을 base 로 되돌린다**.

대표 8-27: "조재진 캐릭터 정면에서 봤을 때 왼쪽 볼쪽에 검은색 가로선 노이즈 껴 있음".
실측: 볼 음영 띠(x37~41)의 아래끝이 턱선 윤곽과 붙어 y106~110 에서 굵은 가로 막대가 됐다.
base 는 그 자리가 밝기 87 의 피부다.

★자동 판정(“base 보다 어두우면 지운다”)은 **쓰지 않는다.** 얼굴 전반이 base 와 다르므로
  코 그림자·입·눈매까지 통째로 지워진다(실제로 5,849 px 이 걸려 되돌렸다).
  얼굴은 개성이라 기계가 판단할 수 없다 — **자리를 눈으로 찍어서** 그 구간만 되돌린다.

사용:
  python tools/face_denoise.py --face char/faces/jaejin_src.png --base char/walk.png \
      --rect 106 111 37 42 --rows 0
"""
import argparse, os
import numpy as np
from PIL import Image

CW, CH, COLS, ROWS = 141, 224, 3, 4


def run(face_path, base_path, rect, rows, out_path=None, log=print):
    y0, y1, x0, x1 = rect
    f = np.array(Image.open(face_path).convert("RGBA"))
    b = np.array(Image.open(base_path).convert("RGBA"))
    if f.shape != b.shape:
        raise SystemExit("규격이 다르다: %s vs %s" % (f.shape, b.shape))
    n = 0
    for r in rows:
        for c in range(COLS):
            ys = slice(r * CH + y0, r * CH + y1)
            xs = slice(c * CW + x0, c * CW + x1)
            f[ys, xs] = b[ys, xs]
            n += (y1 - y0) * (x1 - x0)
    log("%s  y%d~%d x%d~%d · 행 %s · %d px 를 base 로 되돌림"
        % (os.path.basename(face_path), y0, y1 - 1, x0, x1 - 1, rows, n))
    Image.fromarray(f, "RGBA").save(out_path or face_path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--face", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--rect", nargs=4, type=int, required=True, metavar=("Y0", "Y1", "X0", "X1"))
    ap.add_argument("--rows", default="0", help="적용할 방향 행(쉼표). 0아래 1위 2좌 3우")
    ap.add_argument("--out")
    a = ap.parse_args()
    run(a.face, a.base, a.rect, [int(x) for x in a.rows.split(",")], a.out)
