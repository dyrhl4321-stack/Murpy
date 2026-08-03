# -*- coding: utf-8 -*-
"""조합별 모자 시트를 만든다 — 모자도 헤어마다 달라야 한다(대표 요구 2026-08-03).

■ 왜
모자 시트가 하나뿐이라 **모든 조합이 같은 모자**를 쓴다. 그래서 긴 머리에 맞춰 모자를
올리면 짧은 머리에서도 떠버린다. "각 머리마다 모자가 얹히는 높이·모양이 달라야 한다".

■ 구조
헤어가 모자별 대체 시트를 갖는 것(hatVariants)과 **대칭**으로, 모자도 헤어별 대체 시트를
갖는다(hairVariants). 조합폭발은 없다 — 헤어 6 × 모자 2 = 12장이 전부다.

    헤어: hair_m_basic__hat_beanie.png   (모자 쓸 때의 헤어)
    모자: hat_beanie__hair_m_basic.png   (그 헤어에 얹을 때의 모자)  ← 이 스크립트

초기값은 **원본 모자를 그대로 복사**한다. 지금과 똑같이 보이는 상태에서 시작해,
대표가 조합마다 다듬으면 그 조합만 바뀐다.

    python char/build_hat_percombo.py           # 없는 것만 만든다
    python char/build_hat_percombo.py --force   # 원본 모자로 전부 되돌린다
"""
import argparse
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "items")

HAIRS = ["hair_m_basic", "hair_ivyleague", "hair_m_semileaf",
         "hair_f_basic", "hair_f_bob_bang", "hair_f_long"]
HATS = ["hat_beanie", "hat_ladodgers"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    made = kept = 0
    for hat in HATS:
        src = os.path.join(ITEMS, hat + ".png")
        if not os.path.exists(src):
            print(f"!! 모자 없음 {hat}")
            continue
        for h in HAIRS:
            dst = os.path.join(ITEMS, f"{hat}__{h}.png")
            if os.path.exists(dst) and not args.force:
                kept += 1
                continue
            shutil.copy2(src, dst)
            made += 1
            print(f"-> {os.path.basename(dst)}")
    print(f"\n새로 만듦 {made} · 이미 있어 건너뜀 {kept}")
    print("※ 초기값은 원본 모자 복사본이다. 조합마다 다듬으면 그 조합만 바뀐다.")


if __name__ == "__main__":
    main()
