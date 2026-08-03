# -*- coding: utf-8 -*-
r"""조합 시트의 '몸'이 base 와 얼마나 어긋나는지 잰다.

★왜 필요한가 (2026-08-03)
조합 시트에서 머리·모자만 오려내려다 머리카락을 파먹어 대표가 실앱에서
"다 투명하고 머리가 비어 보인다"고 판정했다(cd62fc7 로 롤백).
→ 다음 방식은 **오려내지 않고 조합 시트를 body 레이어로 통째 교체**하는 것이다.
  그러면 추출 손실이 원천적으로 0이다.

대신 조건이 하나 붙는다: 옷(상의·하의·신발)은 그 위에 그대로 얹히므로
**조합 시트의 몸이 base 와 같은 자리에 있어야 한다.** 그걸 여기서 실측한다.

    python char/diag_combo_body.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
COMBO = HERE / "_combo"
CW, CH = 141, 224
ALPHA_BIN = 128
BASEW = {"f": "walk_female.png", "m": "walk.png"}
ROW_KO = ["정면", "후면", "좌", "우"]


def marks(cell: np.ndarray) -> tuple[int, int, int]:
    """(바닥 y, 다리 중심 x, 다리 폭).

    ★반드시 **다리·발**로 재야 한다. 몸통 밴드로 재면 긴 생머리가 어깨 옆으로 내려와
      '몸이 20px 어긋났다'는 거짓 수치가 나온다(실측: 어깨폭 +36px). 다리엔 머리가 안 닿는다.
    """
    a = cell[:, :, 3] >= ALPHA_BIN
    if not a.any():
        return -1, -1, -1
    ys = np.nonzero(a.any(axis=1))[0]
    foot = int(ys.max())
    band = a[max(0, foot - 34):foot + 1]              # 발바닥 위 35px = 다리
    xs = np.nonzero(band.any(axis=0))[0]
    if not len(xs):
        return -1, -1, -1
    mid = (int(xs.min()) + int(xs.max())) // 2
    return foot, mid, int(xs.max() - xs.min() + 1)


def main() -> int:
    files = sorted(COMBO.glob("*_full.png"))
    if not files:
        raise SystemExit("char/_combo 에 *_full.png 가 없다 — import_hat_combo.py 를 돌려라")

    bases = {k: np.asarray(Image.open(HERE / v).convert("RGBA")).astype(np.uint8)
             for k, v in BASEW.items()}

    print("■ 조합 시트의 몸 vs base   (발바닥 dy / 몸중심 dx / 어깨폭 차)")
    worst_all = 0
    for p in files:
        sheet = np.asarray(Image.open(p).convert("RGBA")).astype(np.uint8)
        base = bases["f"] if "__hat_f_" in p.stem else bases["m"]
        d = []
        for r in range(4):
            for c in range(3):
                ys, xs = slice(r * CH, (r + 1) * CH), slice(c * CW, (c + 1) * CW)
                sf, sm, sw = marks(sheet[ys, xs])
                bf, bm, bw = marks(base[ys, xs])
                if sf < 0 or bf < 0:
                    continue
                d.append((sf - bf, sm - bm, sw - bw))
        if not d:
            continue
        d = np.array(d)
        worst = max(int(np.abs(d[:, 0]).max()), int(np.abs(d[:, 1]).max()))
        worst_all = max(worst_all, worst)
        flag = "  ★어긋남 큼" if worst > 3 else "  ✔"
        print(f"  {p.stem.replace('_full',''):34s} 발 {d[:,0].min():+3d}~{d[:,0].max():+3d}"
              f"  중심 {d[:,1].min():+3d}~{d[:,1].max():+3d}"
              f"  다리폭 {d[:,2].min():+3d}~{d[:,2].max():+3d}{flag}")
    print(f"\n최대 어긋남 {worst_all}px — 3px 이내면 옷이 그대로 맞는다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
