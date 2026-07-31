# -*- coding: utf-8 -*-
"""원본 시트에는 있는데 우리 추출이 놓친 머리카락을 되찾는다.

■ 왜 이 방향인가 (7-31 실측)
대표가 손으로 채운 자리를 원본과 대조했더니 **94~100%가 원본에 이미 머리카락으로
그려져 있던 자리**였다. 즉 대표는 구멍을 추측해 메운 게 아니라 내 추출의 누락을
원본대로 복원한 것이다. 정답이 원본에 있으므로 자동화할 수 있다.

■ 왜 놓쳤나
diff 추출은 헤어가 base 의 검은 외곽선 위에 얹힌 자리에서 차이가 0이 된다.
**검은 머리(여캐)는 특히 심하다** — 머리색과 외곽선이 둘 다 검정이라 통째로 빠진다.

■ 얼굴을 지키는 장치 (이게 없으면 눈이 깨진다 — 7-30에 실제로 그랬다)
1. base 영역지도의 KEEP(얼굴 앞면·귀)은 절대 건드리지 않는다.
2. 기존 헤어에 붙어 있는 것만 되살린다(고립 조각 금지).
3. 원본의 살색은 제외한다.
AI 는 얼굴 위치·크기를 다르게 그리므로 **원본 시트를 얼굴 판정에 쓰면 안 된다.**
얼굴 판정은 고정 파일인 base 에서만 한다.

    python char/restore_from_source.py hair_f_long.png human_f            # 미리보기
    python char/restore_from_source.py hair_f_long.png human_f --apply
    python char/restore_from_source.py hair_f_long.png human_f --check before_hair_f_long.png
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_regions import regions as base_regions   # noqa: E402
from build_hair_layer import (BALD_M, BALD_F, MHAIR, NUKKI, FBASIC, CW, CH,   # noqa: E402
                              ALPHA_BIN, SKIN_R, Norm, load, pad_img, binarize)

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = ["정면", "후면", "좌", "우"]
BASEW = {"human": "walk.png", "human_f": "walk_female.png"}
BALD = {"human": BALD_M, "human_f": BALD_F}
GROW = 2          # 기존 헤어에서 이만큼 안에 붙어 있는 것만 되살린다
CLOSE = 3         # 실루엣 안쪽으로 파인 자리만 (0이면 끔). --close 로 바꾼다

SOURCE = {
    "hair_f_long.png": os.path.join(NUKKI, "여자 검정생머리_clean-Photoroom.png"),
    "hair_f_bob_bang.png": os.path.join(NUKKI, "여자 검정단발머리_clean-Photoroom.png"),
    "hair_f_basic.png": os.path.join(FBASIC, "여자기본머리_clean-Photoroom.png"),
    "hair_m_basic.png": os.path.join(MHAIR, "남자기본헤어_clean-Photoroom.png"),
    "hair_m_semileaf.png": os.path.join(MHAIR, "세미리프컷_clean-Photoroom.png"),
}
# 세미리프컷은 4방향 전부 원본 col0 을 쓴다(대표 지정)
FORCE_COL0 = {"hair_m_semileaf.png"}


def is_skin(a):
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    return (R >= SKIN_R) & (R > G + 20) & (G > B)


def run(name, body, apply=False, check=None):
    walk = np.asarray(Image.open(os.path.join(HERE, BASEW[body])).convert("RGBA")).astype(int)
    norm = Norm(load(BALD[body]))
    src_pad = pad_img(load(SOURCE[name]))

    p = os.path.join(HERE, "items", name)
    start = p if check is None else os.path.join(HERE, "_diag", check)
    a = np.asarray(Image.open(start).convert("RGBA")).astype(int)
    out = a.copy()

    print(f"■ {name}  (시작 {os.path.basename(start)})")
    total = 0
    for r in range(4):
        sc = 0 if name in FORCE_COL0 else 0        # 원본은 방향당 1프레임만 쓴다
        worn = binarize(norm.cell(src_pad, r, sc))
        wm = (worn[:, :, 3] >= ALPHA_BIN) & ~is_skin(worn)
        got = 0
        for c in range(3):
            bc = walk[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
            hc = out[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
            h = hc[:, :, 3] >= ALPHA_BIN
            _must, keep = base_regions(bc, r, BASEW[body], c)

            near = ndimage.binary_dilation(h, np.ones((3, 3), bool), iterations=GROW)
            add = wm & ~h & ~keep & near           # 원본에 있고·우리엔 없고·얼굴귀 아니고·헤어에 붙음
            # ★'붙어 있음'만으론 머리 둘레가 통째로 부푼다(실측 과잉 3451~4670px).
            #   원본 머리는 base 두상보다 크게 그려져 있기 때문이다.
            #   닫힘(closing)으로 **실루엣 안쪽으로 파인 자리(노치·틈)** 만 남긴다.
            #   바깥으로 퍼지는 살은 닫힘 결과에 안 들어와 걸러진다.
            if CLOSE:
                k = np.ones((CLOSE * 2 + 1, CLOSE * 2 + 1), bool)
                add &= ndimage.binary_closing(h, k)
            if add.any():
                hc[add] = worn[add]
                hc[add, 3] = 255
                got += int(add.sum())
        total += got
        print(f"   {ROWS[r]:2s}  {got}px 되찾음")
    print(f"   합계 {total}px")

    if check:
        truth = np.asarray(Image.open(p).convert("RGBA")).astype(int)
        before = a[:, :, 3] >= ALPHA_BIN
        auto = (out[:, :, 3] >= ALPHA_BIN) & ~before
        human = (truth[:, :, 3] >= ALPHA_BIN) & ~before
        inter, union = int((auto & human).sum()), int((auto | human).sum())
        print(f"\n   [대표 수작업과 비교]")
        print(f"     대표 {int(human.sum())}px / 자동 {int(auto.sum())}px · 둘 다 {inter}px")
        print(f"     자동만(과잉) {int((auto & ~human).sum())}px · 대표만(놓침) {int((human & ~auto).sum())}px")
        print(f"     겹침률(IoU) {100.0 * inter / union if union else 0:.1f}%"
              f" · 대표가 채운 것 중 자동이 잡은 비율 {100.0 * inter / max(1, human.sum()):.0f}%")
        if inter:
            d = np.abs(out[auto & human][:, :3] - truth[auto & human][:, :3]).sum(axis=1)
            print(f"     색 차이 평균 {d.mean():.1f} · 24이하 {100.0 * (d <= 24).mean():.0f}%")

    if apply:
        Image.fromarray(out.astype(np.uint8), "RGBA").save(p)
        print(f"   -> 적용됨 {p}")
    elif not check:
        q = os.path.join(HERE, "_diag", f"restored_src_{name}")
        Image.fromarray(out.astype(np.uint8), "RGBA").save(q)
        print(f"   -> 미리보기 {q}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    check = sys.argv[sys.argv.index("--check") + 1] if "--check" in sys.argv else None
    if "--close" in sys.argv:
        global CLOSE
        CLOSE = int(sys.argv[sys.argv.index("--close") + 1])
    run(sys.argv[1], sys.argv[2], "--apply" in sys.argv, check)


if __name__ == "__main__":
    main()
