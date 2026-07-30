# -*- coding: utf-8 -*-
"""헤어 레이어 5종 결함 계량 — 후보정 전 기준값.

대표 지적을 측정 가능한 항목으로 바꾼 것:
  1) 두상 노출 : base 대머리가 헤어 밖으로 삐져나온 픽셀 수 (열별)
  2) base 복사 : 헤어 레이어가 base와 같은 색으로 갖고 있는 픽셀 = 이중 외곽선(검게 탐)
  3) 그림자    : base 색을 어둡게 깐 픽셀 = 턱·목 음영 (헤어가 아니라 base 조명)
  4) 살색      : 헤어 레이어에 든 살색
  5) 합성 틈   : base+헤어 합성 후 갇힌 투명 구멍 (생머리 등-머리 사이 ㅣ)
  6) 반투명    : 알파 이진화 위반
  7) 두상 이동 : base 두상이 걸음 프레임마다 얼마나 움직이나 (헤어 평행이동량)

    python char/audit_hair_layers.py
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "items")
CW, CH = 141, 224
ROWNAME = ["정면", "후면", "좌", "우"]
BAND = 18

HAIRS = [
    ("hair_shaggy", "더벅", "walk.png"),
    ("hair_semileaf", "세미리프", "walk.png"),
    ("hair_ivyleague", "아이비", "walk.png"),
    ("hair_fem_bob", "여-단발", "walk_female.png"),
    ("hair_fem_long", "여-생머리", "walk_female.png"),
]


def load(p):
    return np.asarray(Image.open(p).convert("RGBA")).astype(int)


def cell(a, r, c):
    return a[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]


def body_mask(bc):
    """base 셀의 몸 실루엣 — 최대 연결덩어리만(구석 잔여 픽셀 무시)."""
    m = bc[:, :, 3] >= 128
    lab, n = ndimage.label(m, np.ones((3, 3), bool))
    if n == 0:
        return m
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    return lab == (int(np.argmax(sizes)) + 1)


def skull(bc):
    """두상 기준점 = 실루엣 최상단 y, 상단 밴드의 중심 x."""
    m = body_mask(bc)
    ys = np.where(m.any(axis=1))[0]
    top = int(ys.min())
    xs = np.where(m[top:top + BAND].any(axis=0))[0]
    return top, (int(xs.min()) + int(xs.max())) / 2.0, int(xs.max() - xs.min() + 1)


def luma(x):
    return 0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2]


def classify(hc, bc):
    """헤어 픽셀을 base 대비로 분류한다."""
    hm = hc[:, :, 3] >= 128
    bm = bc[:, :, 3] >= 128
    over = hm & bm                       # base 위에 얹힌 헤어 픽셀
    d = np.abs(hc[:, :, :3] - bc[:, :, :3]).max(axis=2)

    same = over & (d <= 24)              # base를 그대로 복사 = 이중 그리기

    hl, bl = luma(hc), luma(bc)
    ratio = np.divide(hl, np.maximum(bl, 1e-6))
    # 색조가 base와 같은데 어둡기만 하다 = 그림자
    hue_close = (np.abs((hc[:, :, 0] - hc[:, :, 2]) - (bc[:, :, 0] - bc[:, :, 2])) <= 42)
    shadow = over & ~same & hue_close & (ratio >= 0.42) & (ratio <= 0.90)

    R, G, B = hc[:, :, 0], hc[:, :, 1], hc[:, :, 2]
    skin = hm & (R >= 120) & (R > G + 25) & (G > B + 5)
    return hm, bm, same, shadow, skin


def overhang(hm, bm, frac=0.45):
    """두상 구간에서 base 실루엣이 헤어보다 좌/우로 더 나간 픽셀 수.

    대표가 본 '빡빡이가 왼쪽으로 튀어나옴' / '양옆으로 튀어나옴' 이 이것이다.
    두상 구간 = base 최상단부터 머리 높이의 45%까지(그 아래는 얼굴·목이라 헤어 밖이 정상).
    """
    ys = np.where(bm.any(axis=1))[0]
    if not len(ys) or not hm.any():
        return 0
    top = int(ys.min())
    hy = np.where(hm.any(axis=1))[0]
    lim = top + max(6, int((int(hy.max()) - top) * frac))
    n = 0
    for y in range(top, min(lim + 1, bm.shape[0])):
        bx = np.where(bm[y])[0]
        hx = np.where(hm[y])[0]
        if not len(bx):
            continue
        if not len(hx):
            n += len(bx); continue
        n += int((bx < hx.min()).sum() + (bx > hx.max()).sum())
    return n


def holes(hc, bc):
    """합성 후 갇힌 투명 구멍 = 등-머리 사이 여백."""
    vis = (hc[:, :, 3] >= 128) | (bc[:, :, 3] >= 128)
    filled = ndimage.binary_fill_holes(vis)
    return filled & ~vis


print("=" * 96)
for name, ko, basef in HAIRS:
    hair = load(os.path.join(ITEMS, name + ".png"))
    base = load(os.path.join(HERE, basef))
    alpha = hair[:, :, 3]
    semi = int(((alpha > 0) & (alpha < 255)).sum())
    print("■ %s (%s)   반투명 %d px %s" % (
        ko, name, semi, "" if semi == 0 else "★알파 이진화 위반"))

    # 두상 이동량 (열별) — 헤어를 얼마나 평행이동해야 하는가
    for r in range(4):
        sk = [skull(cell(base, r, c)) for c in range(3)]
        tops = [s[0] for s in sk]
        cxs = [s[1] for s in sk]
        exposed, holecnt = [], []
        for c in range(3):
            hc, bc = cell(hair, r, c), cell(base, r, c)
            hm, bm, same, shadow, skin = classify(hc, bc)
            # 두상 삐짐 = 두상 구간에서 base 실루엣이 헤어 실루엣보다 좌/우로 더 나간 픽셀.
            # (얼굴 살색을 세면 안 된다 — 얼굴은 원래 헤어 밖이다)
            exposed.append(overhang(hm, bm))
            holecnt.append(int(holes(hc, bc).sum()))
        hc0, bc0 = cell(hair, r, 0), cell(base, r, 0)
        hm, bm, same, shadow, skin = classify(hc0, bc0)
        tot = max(1, int(hm.sum()))
        print("   [%s] 헤어%5d | base복사%5d(%4.1f%%) 그림자%4d 살색%5d | 두상노출%s 틈%s | 두상이동 dy%d dx%.1f" % (
            ROWNAME[r], tot, int(same.sum()), 100.0 * same.sum() / tot,
            int(shadow.sum()), int(skin.sum()),
            exposed, holecnt, max(tops) - min(tops), max(cxs) - min(cxs)))
    print()
