# -*- coding: utf-8 -*-
"""모자를 썼을 때 쓸 헤어 대체 시트를 만든다 (hatVariants).

■ 지금 문제
앱 z 순서가 hair -> hat 이라 모자가 헤어 위에 그려진다. 그런데 **모자 시트가 두상 전체를
덮도록** 만들어져 있어서, 모자를 쓰면 머리카락이 하나도 안 보인다(12조합 전부).
대표 요구: "정면·측면에 앞머리 살짝 + 옆머리 + 뒷머리 살짝 보여야 진짜 모자 쓴 느낌."

■ 규칙 2단계
1) **자르기** — 보이는 머리카락 = 헤어 ∧ ¬모자실루엣.
   모자가 가리는 부분만 지우고 모자 밖으로 나온 머리카락은 남긴다.
   프레임마다 그 프레임의 모자를 쓰므로 어긋나지 않는다.
2) **삐져나오게 하기(peek)** — 1)만 하면 모자가 이마까지 푹 덮어서 **앞머리가 하나도
   안 남는다**(비니가 눈썹까지 내려온다). 대표 요구는 "머리에 실제로 씌운 것처럼
   앞머리·옆머리·뒷머리가 살짝 보이는" 연출이다.
   → 모자 경계 바깥 PEEK px 띠 중 **base 두상 안쪽**을 머리카락으로 채운다.
   색은 지어내지 않고 가장 가까운 원래 머리카락 색을 복사한다.
   방향마다 나오는 양이 다르다 — 정면은 앞머리만 살짝, 후면은 뒷머리가 넉넉히.

■ 남은 조각 정리
모자 경계에 1~2px 짜리 파편이 남으면 지저분하다. 작은 고립 조각은 버린다.
남는 픽셀이 아주 적으면(짧은 머리) **빈 시트 대신 null 로 등록**하는 게 낫다 — 그때는
파일을 만들지 않고 알려준다.

    python char/build_hat_variants.py                 # 전체 조합
    python char/build_hat_variants.py --hair hair_m_basic --hat hat_beanie
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_regions import regions as regions_of   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "items")
CW, CH = 141, 224
ALPHA_BIN = 128
ROWS = ["정면", "후면", "좌", "우"]
MIN_PIECE = 12      # 이보다 작은 고립 조각은 버린다
MIN_KEEP = 120      # 전체가 이보다 적으면 사실상 안 보인다 -> null 권장
# 방향별로 모자 밖으로 삐져나올 폭(px). 정면은 앞머리만 살짝, 후면은 뒷머리가 넉넉히.
PEEK = {0: 0, 1: 0, 2: 0, 3: 0}    # 자동 생성은 안 한다(어색하다) — 대표가 직접 그린다
HEM = True         # False 면 모자 위·옆으로 넘치는 머리를 남긴다(대표가 지울 때)
FRONT_TOP_KEEP = 6  # 정면에서 모자 최상단 아래 이만큼은 머리를 안 만든다(모자 위로 솟지 않게)
BASEW = {"human": "walk.png", "human_f": "walk_female.png"}
BODY_OF = {"hair_m_basic": "human", "hair_ivyleague": "human", "hair_m_semileaf": "human",
           "hair_f_basic": "human_f", "hair_f_bob_bang": "human_f", "hair_f_long": "human_f"}


def top_of(m):
    ys = np.where(m.any(axis=1))[0]
    return int(ys.min()) if len(ys) else 0


def hem_line(tm):
    """모자 밑단의 대표 높이 — 모자가 있는 x 들의 최하단 y 중앙값.

    모자 폭 **밖**(귀 옆 등)에는 기준이 될 모자가 없다. 그 자리 머리카락(옆머리)은
    남겨야 하지만 정수리 높이까지 남기면 '모자 위로 솟은' 모습이 된다 → 이 선 아래만 남긴다.
    """
    cols = [np.where(tm[:, x])[0] for x in range(tm.shape[1])]
    bots = [c.max() for c in cols if len(c)]
    return int(np.median(bots)) if bots else 0

HAIRS = ["hair_m_basic", "hair_ivyleague", "hair_m_semileaf",
         "hair_f_basic", "hair_f_bob_bang", "hair_f_long"]
HATS = ["hat_beanie", "hat_ladodgers"]


def load(name):
    p = os.path.join(ITEMS, name + ".png")
    return np.asarray(Image.open(p).convert("RGBA")).astype(int) if os.path.exists(p) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hair")
    ap.add_argument("--hat")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--no-hem", action="store_true",
                    help="모자 위·옆으로 넘치는 머리를 남긴다(대표가 직접 지울 때)")
    args = ap.parse_args()
    global HEM
    if args.no_hem:
        HEM = False

    hairs = [args.hair] if args.hair else HAIRS
    hats = [args.hat] if args.hat else HATS

    for h in hairs:
        ha = load(h)
        if ha is None:
            print(f"!! 헤어 없음 {h}")
            continue
        for hat in hats:
            hta = load(hat)
            if hta is None:
                print(f"!! 모자 없음 {hat}")
                continue
            base_name = BASEW[BODY_OF.get(h, "human")]
            base = np.asarray(Image.open(os.path.join(HERE, base_name))
                              .convert("RGBA")).astype(int)
            out = np.zeros_like(ha)
            per = []
            for r in range(4):
                kept_row = 0
                for c in range(3):
                    hc = ha[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
                    tc = hta[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
                    base_cell = base[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
                    hm = hc[:, :, 3] >= ALPHA_BIN
                    tm = tc[:, :, 3] >= ALPHA_BIN
                    # ★★모자를 쓰면 머리는 눌린다 — **위·옆으로는 안 나오고 밑단 아래로만**
                    #   나와야 한다. `hair ∧ ¬hat` 만 쓰면 모자 옆·위로 삐져나온 머리가
                    #   그대로 남아 "모자 밖으로 머리가 튀어나온" 상태가 된다(대표 지적).
                    #   그래서 x열마다 그 열의 모자 **최하단(hem)** 을 구하고 그 아래만 남긴다.
                    #   짧은 머리는 남는 게 거의 없어 자동으로 null 후보가 된다.
                    keep = hm & ~tm
                    # ★HEM 을 끄면 모자 위·옆으로 넘치는 머리를 **남긴다**.
                    #   대표가 스튜디오에서 직접 지우겠다고 할 때는 꺼야 한다 —
                    #   자동으로 잘라버리면 되살릴 수가 없다.
                    if HEM:
                        below = np.zeros_like(keep)
                        for x in range(CW):
                            col_hat = np.where(tm[:, x])[0]
                            if len(col_hat):
                                below[col_hat.max() + 1:, x] = True
                            elif tm.any():
                                # 모자가 없는 x(모자 폭 밖) — 밑단 평균선 아래만 인정
                                below[hem_line(tm) + 1:, x] = True
                        keep &= below

                    # ★★1단계만으로는 화면이 안 바뀐다 — 어차피 모자가 헤어 위에 그려지므로
                    #   미리 자르나 마나 결과가 같다. 실제로 "쓴 것처럼" 보이려면
                    #   모자 **바깥**에 머리카락을 만들어야 한다.
                    #   모자 경계 바깥 PEEK 띠 중 얼굴(눈·코·입)이 아닌 곳을 채운다.
                    peek_px = PEEK[r]
                    if peek_px:
                        band = ndimage.binary_dilation(
                            tm, np.ones((3, 3), bool), iterations=peek_px) & ~tm
                        band &= ~keep
                        if r == 0:
                            band[:top_of(tm) + FRONT_TOP_KEEP] = False   # 정면은 모자 위로 안 나오게
                        _must, kp = regions_of(base_cell, r, base_name, c)
                        band &= ~kp                                       # 얼굴·귀는 건드리지 않는다
                        if band.any() and hm.any():
                            _d, idx = ndimage.distance_transform_edt(~hm, return_indices=True)
                            ys2, xs2 = np.where(band)
                            cell0 = out[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
                            cell0[ys2, xs2] = hc[idx[0][ys2, xs2], idx[1][ys2, xs2]]
                            cell0[ys2, xs2, 3] = 255

                    lab, n = ndimage.label(keep, np.ones((3, 3), bool))
                    if n:
                        sizes = ndimage.sum(keep, lab, range(1, n + 1))
                        for i, s in enumerate(sizes, start=1):
                            if s < MIN_PIECE:
                                keep[lab == i] = False

                    cell = out[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
                    cell[keep] = hc[keep]
                    cell[keep, 3] = 255
                    kept_row += int(keep.sum())
                per.append(kept_row)

            total = sum(per)
            name = f"{h}__{hat}"
            mark = "  → null 권장(거의 안 보임)" if total < MIN_KEEP else ""
            print(f"{h:18s} + {hat:14s} 남는 머리카락 "
                  f"정면{per[0]:5d} 후면{per[1]:5d} 좌{per[2]:5d} 우{per[3]:5d}"
                  f"  합{total:5d}{mark}")
            if args.dry or total < MIN_KEEP:
                continue
            out[:, :, 3] = np.where(out[:, :, 3] >= ALPHA_BIN, 255, 0)
            out[out[:, :, 3] == 0] = 0
            Image.fromarray(out.astype(np.uint8), "RGBA").save(
                os.path.join(ITEMS, name + ".png"))


if __name__ == "__main__":
    main()
