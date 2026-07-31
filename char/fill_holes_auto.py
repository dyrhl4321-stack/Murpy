# -*- coding: utf-8 -*-
"""헤어 레이어의 구멍을 주변 머리색으로 자동으로 메운다.

대표 제안(7-31): "형광 마젠타로 보니 뚫린 데가 바로 보인다. 그러면 그 주변 경계
머리색이나 검은 테두리 같은 색으로 AI가 알아서 칠해주면 되잖아."

맞다. 구멍 검출은 이미 정확하고(char/diag_holes.py), 채울 색도 규칙으로 정해진다.
**각 구멍 픽셀에서 가장 가까운 머리카락 픽셀의 색을 가져온다.** 구멍 둘레가 검은
테두리면 검은색이, 머리 안쪽이면 머리색이 자동으로 따라온다 — 색을 지어내지 않는다.

★귀는 절대 메우지 않는다. 프로필에서 머리카락이 귀를 둘러싸면 귀가 '내부 구멍'으로
  잡힌다(실측 240~290px). 메우면 귀가 사라진다. base 영역지도의 KEEP 으로 걸러낸다.

    python char/fill_holes_auto.py hair_f_long.png human_f            # 미리보기
    python char/fill_holes_auto.py hair_f_long.png human_f --apply
    python char/fill_holes_auto.py <파일> <몸통> --check <정답파일>   # 정확도 실측
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_regions import regions as base_regions   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CW, CH = 141, 224
ALPHA_BIN = 128
ROWS = ["정면", "후면", "좌", "우"]
BASE = {"human": "walk.png", "human_f": "walk_female.png"}
MAX_HOLE = 400      # 이보다 큰 건 구멍이 아니라 '원래 비어 있어야 할 자리'로 본다


def cell_of(a, r, c):
    return a[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]


def holes_of(hc, bc, r, base_name, c):
    """메울 구멍 마스크. 귀(KEEP)와 지나치게 큰 덩어리는 뺀다."""
    h = hc[:, :, 3] >= ALPHA_BIN
    allh = ndimage.binary_fill_holes(h) & ~h
    _must, keep = base_regions(bc, r, base_name, c)
    cand = allh & ~keep
    lab, n = ndimage.label(cand, np.ones((3, 3), bool))
    out = np.zeros_like(cand)
    for i in range(1, n + 1):
        m = lab == i
        if m.sum() <= MAX_HOLE:
            out |= m
    return out, h


def fill(hc, holes, h):
    """가장 가까운 머리카락 픽셀의 색을 복사한다 (색을 지어내지 않는다)."""
    if not holes.any():
        return hc, 0
    _d, idx = ndimage.distance_transform_edt(~h, return_indices=True)
    out = hc.copy()
    ys, xs = np.where(holes)
    out[ys, xs] = hc[idx[0][ys, xs], idx[1][ys, xs]]
    out[ys, xs, 3] = 255
    return out, int(holes.sum())


def run(name, body, apply=False, check=None):
    base_name = BASE[body]
    base = np.asarray(Image.open(os.path.join(HERE, base_name)).convert("RGBA")).astype(int)
    p = os.path.join(HERE, "items", name)
    src = p if check is None else os.path.join(HERE, "_diag", check)
    a = np.asarray(Image.open(src).convert("RGBA")).astype(int)
    out = a.copy()

    total = 0
    print(f"■ {name}  (원본 {os.path.basename(src)})")
    for r in range(4):
        for c in range(3):
            bc = cell_of(base, r, c)
            hc = cell_of(a, r, c)
            holes, h = holes_of(hc, bc, r, base_name, c)
            filled, n = fill(hc, holes, h)
            out[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW] = filled
            total += n
            if n and c == 0:
                print(f"   {ROWS[r]:2s} col0  {n}px 메움")
    print(f"   합계 {total}px")

    if check:
        truth = np.asarray(Image.open(p).convert("RGBA")).astype(int)
        before = a[:, :, 3] >= ALPHA_BIN
        auto = (out[:, :, 3] >= ALPHA_BIN) & ~before        # 자동이 채운 자리
        human = (truth[:, :, 3] >= ALPHA_BIN) & ~before     # 대표가 채운 자리
        inter = int((auto & human).sum())
        union = int((auto | human).sum())
        print(f"\n   [대표 수작업과 비교]")
        print(f"     대표가 채운 곳 {int(human.sum())}px / 자동이 채운 곳 {int(auto.sum())}px")
        print(f"     둘 다 채움 {inter}px · 자동만(과잉) {int((auto & ~human).sum())}px"
              f" · 대표만(놓침) {int((human & ~auto).sum())}px")
        print(f"     겹침률(IoU) {100.0 * inter / union if union else 0:.1f}%")
        if inter:
            d = np.abs(out[auto & human][:, :3] - truth[auto & human][:, :3]).sum(axis=1)
            print(f"     같이 채운 자리의 색 차이: 평균 {d.mean():.1f} / 24이하(사실상 같은 색)"
                  f" {100.0 * (d <= 24).mean():.0f}%")

        # 대표가 채웠는데 자동이 놓친 자리가 어떤 성격인지 — 다음 규칙의 근거
        missed = human & ~auto
        if missed.any():
            bm_all = base[:, :, 3] >= ALPHA_BIN
            hb = before
            nb = ndimage.binary_dilation(hb, np.ones((3, 3), bool)) & ~hb   # 머리 바로 바깥 한 겹
            print(f"     놓친 자리 성격: base 실루엣 안 {100.0*(missed&bm_all).sum()/missed.sum():.0f}%"
                  f" · 머리 가장자리에 붙음 {100.0*(missed&nb).sum()/missed.sum():.0f}%")
            per = []
            for r in range(4):
                m = missed[r*CH:(r+1)*CH]
                per.append(f"{ROWS[r]} {int(m.sum())}")
            print("     놓친 자리 방향별: " + " · ".join(per))

        # 시각화: 초록=자동만 · 빨강=대표만 · 노랑=둘다
        vis = np.zeros((CH, CW * 4, 4), int)
        for r in range(4):
            base_c = cell_of(base, r, 0).copy()
            hc = cell_of(a, r, 0)
            m = hc[:, :, 3] >= ALPHA_BIN
            base_c[m] = hc[m]
            au = auto[r*CH:(r+1)*CH, 0:CW]
            hu = human[r*CH:(r+1)*CH, 0:CW]
            base_c[au & ~hu] = [0, 255, 0, 255]
            base_c[hu & ~au] = [255, 40, 40, 255]
            base_c[au & hu] = [255, 230, 0, 255]
            vis[:, r*CW:(r+1)*CW] = base_c
        im = Image.fromarray(vis.astype(np.uint8), "RGBA").convert("RGB")
        q = os.path.join(HERE, "_diag", f"autofill_check_{name}")
        im.resize((im.width * 5, im.height * 5), Image.NEAREST).save(q)
        print(f"     -> {q}  (초록=자동만 · 빨강=대표만 · 노랑=둘다)")

    if apply:
        Image.fromarray(out.astype(np.uint8), "RGBA").save(p)
        print(f"   -> 적용됨 {p}")
    elif not check:
        q = os.path.join(HERE, "_diag", f"autofill_{name}")
        Image.fromarray(out.astype(np.uint8), "RGBA").save(q)
        print(f"   -> 미리보기 {q}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    check = None
    if "--check" in sys.argv:
        check = sys.argv[sys.argv.index("--check") + 1]
    run(sys.argv[1], sys.argv[2], "--apply" in sys.argv, check)


if __name__ == "__main__":
    main()
