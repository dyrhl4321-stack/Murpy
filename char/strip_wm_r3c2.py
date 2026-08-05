# -*- coding: utf-8 -*-
"""제미나이 워터마크(✦) 제거 — 어떤 시트에도 쓰는 범용판.

■ 알아낸 패턴 (2026-08-05)
✦ 는 **항상 우하단 프레임 = 4행 3열(우측 걸음2)** 에 찍힌다.
반투명 흰색이라 밑에 뭐가 있든 그 자리를 밝게 만든다.
  - 어두운 옷(반바지) 위 → 어두운 것만 고르는 필터에 안 걸려 문제가 안 났다
  - 흰 옷·살색 위 → 밝은 것을 고르는 필터를 그대로 통과해 옷으로 딸려 들어온다

■ 방식
없는 픽셀을 지어내지 않는다. **같은 행 c0 에서 그 자리를 그대로 옮겨 심는다.**
✦ 판정 = "도너보다 눈에 띄게 밝아진 자리". 색으로 찾으면 못 잡는다
(살색 위에서는 '밝은 살색'이라 무채색 조건에 안 걸린다 — 실제로 그렇게 놓쳤다).

    python char/strip_wm_r3c2.py <시트.png>            # 찾기만
    python char/strip_wm_r3c2.py <시트.png> --apply    # 제자리 수정(백업 남김)
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BRIGHT = 18      # 도너보다 이만큼 밝아지면 ✦ 로 본다
GROW = 2         # 옅은 가장자리까지 걷어내려고 넓히는 횟수
# ★몸통 구간으로 좁힌다. 안 좁히면 **다리가 가장 큰 덩어리로 잡힌다** —
#   걸음 프레임마다 다리 위치가 달라 통째로 '밝아진 곳'이 되기 때문이다.
#   실제로 후드집업에서 다리(7438px)를 워터마크(3512px)로 오인해 이식했다가 다리를 깨뜨렸다.
ROI_Y0, ROI_Y1 = 0.53, 0.80
ROI_X0, ROI_X1 = 0.28, 0.74


def find_and_fix(a: np.ndarray, apply: bool):
    h, w = a.shape[0] // 4, a.shape[1] // 3
    oy, ox = 3 * h, 2 * w
    A = a.astype(int)
    tgt = A[oy:oy + h, ox:ox + w]
    don = A[oy:oy + h, 0:w]                      # 같은 행 c0

    op = tgt[:, :, 3] >= 128
    od = don[:, :, 3] >= 128
    both = op & od
    if both.sum() < 1000:
        return None, "겹치는 영역이 너무 적다"

    roi = np.zeros((h, w), bool)
    roi[int(h * ROI_Y0):int(h * ROI_Y1), int(w * ROI_X0):int(w * ROI_X1)] = True
    bright = both & roi & ((tgt[:, :, :3].mean(axis=2) - don[:, :, :3].mean(axis=2)) > BRIGHT)
    lab, n = ndimage.label(ndimage.binary_closing(bright, np.ones((3, 3), bool)), np.ones((3, 3), bool))
    if not n:
        return None, "밝아진 덩어리 없음 (✦ 가 없을 수 있다)"
    sizes = ndimage.sum(bright, lab, range(1, n + 1))
    wm = lab == int(np.argmax(sizes)) + 1
    ys, xs = np.nonzero(wm)
    info = (int(sizes.max()), int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max()))

    if apply:
        m = ndimage.binary_dilation(wm, np.ones((3, 3), bool), iterations=GROW) & both
        patch = a[oy:oy + h, 0:w]
        dst = a[oy:oy + h, ox:ox + w]
        dst[m] = patch[m]
        info = info + (int(m.sum()),)
    return info, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    p = Path(args.src)
    if not p.exists():
        print("!! 없음", p)
        return 1
    a = np.asarray(Image.open(p).convert("RGBA")).astype(np.uint8).copy()
    h, w = a.shape[0] // 4, a.shape[1] // 3
    print(f"{p.name}  {a.shape[1]}×{a.shape[0]}  셀 {w}×{h}")

    info, err = find_and_fix(a, args.apply)
    if err:
        print("  " + err)
        return 0
    print(f"  ✦ 후보 {info[0]}px  셀내 x{info[1]}~{info[2]} y{info[3]}~{info[4]}")
    if not args.apply:
        print("  --apply 를 붙이면 도너 이식")
        return 0

    bak = p.with_name(p.stem + "_워터마크백업" + p.suffix)
    if not bak.exists():
        shutil.copy2(p, bak)
    Image.fromarray(a, "RGBA").save(p)
    print(f"  이식 {info[5]}px  -> 제자리 수정 (백업 {bak.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
