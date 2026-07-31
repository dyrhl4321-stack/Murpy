# -*- coding: utf-8 -*-
"""남캐용 아이템 시트를 여캐 몸에 맞춰 옮긴다 (신발·헤드셋처럼 여캐 원본이 없는 슬롯).

여캐 전용 원본이 없는 아이템은 재추출할 수가 없다. 대신 이미 만들어 둔 남캐 레이어를
**프레임마다 base 기준점 차이만큼 평행이동**해서 여캐 몸에 맞춘다.
남녀 base 는 키가 같으므로(둘 다 209) 크기 변환 없이 이동만으로 맞는다.

기준점은 슬롯에 따라 다르다:
  신발(shoes)  = 발 — base 실루엣 **최하단** y, 그 행의 좌우 중심 x
  그 외(acc 등) = 머리 — skull_ref(최상단 y, 상단 18px 밴드 중심 x)

    python char/adapt_item_to_body.py shoes_white shoes_f_white shoes
    python char/adapt_item_to_body.py acc_airpodsmax acc_f_airpodsmax acc --dry
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_hair_layer import skull_ref, shift   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "items")
CW, CH = 141, 224
ALPHA_BIN = 128
ROWS = ["정면", "후면", "좌", "우"]
MAXD = 3          # 이동 상한(px). 이보다 크면 기준점 계산이 튄 것으로 본다


def foot_ref(bm):
    """발 기준점 = 실루엣 최하단 y, 그 부근(아래 6행) 좌우 중심 x."""
    ys = np.where(bm.any(axis=1))[0]
    bot = int(ys.max())
    band = bm[max(0, bot - 5):bot + 1]
    xs = np.where(band.any(axis=0))[0]
    return bot, (int(xs.min()) + int(xs.max())) / 2.0


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return
    src_id, dst_id, slot = sys.argv[1], sys.argv[2], sys.argv[3]
    dry = "--dry" in sys.argv

    m = np.asarray(Image.open(os.path.join(HERE, "walk.png")).convert("RGBA")).astype(int)
    f = np.asarray(Image.open(os.path.join(HERE, "walk_female.png")).convert("RGBA")).astype(int)
    item = np.asarray(Image.open(os.path.join(ITEMS, src_id + ".png"))
                      .convert("RGBA")).astype(int)
    out = np.zeros_like(item)

    ref = foot_ref if slot == "shoes" else skull_ref
    print(f"■ {src_id} → {dst_id}  (기준 {'발' if slot == 'shoes' else '머리'})")
    for r in range(4):
        deltas = []
        for c in range(3):
            bm_m = m[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW, 3] >= ALPHA_BIN
            bm_f = f[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW, 3] >= ALPHA_BIN
            ym, xm = ref(bm_m)
            yf, xf = ref(bm_f)
            dx, dy = int(round(xf - xm)), int(round(yf - ym))
            # ★걸음 프레임에서 발이 앞뒤로 벌어지면 '최하단 부근 중심'이 크게 흔들린다
            #   (실측: 좌 col2 에서만 +20px). 남녀 base 는 실제로 ±2px 안에서 겹치므로
            #   그 범위를 넘는 값은 계산 실패로 보고 자른다.
            dx = max(-MAXD, min(MAXD, dx))
            dy = max(-MAXD, min(MAXD, dy))
            cell = item[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
            out[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW] = shift(cell, dx, dy)
            deltas.append(f"({dx:+d},{dy:+d})")
        print(f"   {ROWS[r]:2s}  이동 {' '.join(deltas)}")

    out[:, :, 3] = np.where(out[:, :, 3] >= ALPHA_BIN, 255, 0)
    out[out[:, :, 3] == 0] = 0
    if dry:
        print("   (--dry: 파일 안 씀)")
        return
    p = os.path.join(ITEMS, dst_id + ".png")
    Image.fromarray(out.astype(np.uint8), "RGBA").save(p)
    print(f"   -> {p}")


if __name__ == "__main__":
    main()
