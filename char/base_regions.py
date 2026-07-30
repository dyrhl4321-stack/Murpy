# -*- coding: utf-8 -*-
"""base(walk.png / walk_female.png)에서 '머리카락이 덮어야 할 영역' 지도를 만든다.

★왜 필요한가 (2026-07-31)
대표가 반복해서 지적한 결함이 전부 한 자리에 몰려 있었다 —
  귀 위 살색 도트 / 귀 뒤·귀 아래 살색 / 뒤통수-귀 연결부 / 목덜미 살색 / 귀 옆 검은 이중선.
원인은 내가 '귀를 보호한다'며 **귀 주변을 통째로 커버 대상에서 빼놨기** 때문이다.
빼야 할 것은 **귀 그 자체뿐**이고, 귀 위·뒤·아래와 목덜미는 머리카락 영역이다.

★왜 이 방식이 근본적인가
base 시트는 재수정 금지인 **고정 파일**이다. 그러니 영역 판정을 base에서 한 번 정확히
계산해 두면 AI 드리프트·시트 오염·색 임계와 완전히 무관해진다. 헤어를 새로 뽑든
다른 헤어를 추가하든 이 지도는 그대로 쓴다.

세 가지로 나눈다:
  MUST  머리카락이 반드시 덮어야 함 (두상 옆·뒤, 귀 위/뒤/아래, 목덜미)
  KEEP  절대 건드리면 안 됨 (눈·코·입이 있는 얼굴 앞면, 귀 그 자체)
  FREE  헤어스타일 마음대로 (이마 — 앞머리가 덮을 수도, 비칠 수도 있다)

    python char/base_regions.py          # 검증용 지도 PNG 저장
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
CW, CH = 141, 224
ALPHA_BIN = 128

# ── base 실측 상수 (머리 최상단 기준 상대 y / 셀 절대 x) ──────────────────────
# 눈썹 최상단: 남 정면65-top11=54 · 좌 59-12=47 · 우 57-11=46
#              여 정면64-11=53 · 좌 58-11=47 · 우 57-12=45
BROW = {"walk.png": [54, None, 47, 46], "walk_female.png": [53, None, 47, 45]}
# 정면/후면에서 귀가 옆으로 튀어나오기 시작하는 상대 y (실루엣 폭 급증 실측)
#   남 정면 rel64(y75) 후면 rel68(y79) / 여 정면 rel63 후면 rel67
EAR_TOP_FB = {"walk.png": [64, 68], "walk_female.png": [63, 67]}
# 프로필 귀 상자 (x는 머리 중심 기준 오프셋, y는 상대). 좌 실측 x70~89 / 우 x46~68,
# 머리중심 좌 mid68 / 우 mid70 → 오프셋 좌 +2~+22, 우 -25~-3. 여유 2px.
EAR_BOX_PROF = {2: (0, 24, 56, 84), 3: (-27, -1, 56, 84)}   # (dx0, dx1, y0, y1)
# 정면 얼굴 앞면의 가로 범위 (셀 절대 x, 실측). 이 밖은 관자놀이=두상이다.
FACE_X = {"walk.png": (37, 101), "walk_female.png": (29, 111)}


def largest(m):
    lab, n = ndimage.label(m, np.ones((3, 3), bool))
    if n <= 1:
        return m
    s = ndimage.sum(m, lab, range(1, n + 1))
    return lab == (int(np.argmax(s)) + 1)


def skinmask(a):
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    return (a[:, :, 3] >= ALPHA_BIN) & (R >= 140) & (R > G + 30) & (G > B + 5)


def neck_end(bm, top):
    """머리 아래 목이 가장 좁아지는 행 = 어깨 시작 직전. 목덜미까지 MUST에 넣기 위해 쓴다."""
    h = bm.shape[0]
    widths = []
    for y in range(top, min(top + 130, h)):
        xs = np.where(bm[y])[0]
        widths.append((y, len(xs)))
    # 머리(넓다) → 목(좁다) → 어깨(다시 넓다). 머리 아래 첫 최소점을 찾는다.
    start = top + 60
    seg = [(y, w) for y, w in widths if y >= start]
    if not seg:
        return min(top + 100, h - 1)
    ymin = min(seg, key=lambda t: t[1])[0]
    return ymin


def regions(bc, r, base_name):
    """(must, keep) 반환. must=헤어가 덮어야 함, keep=절대 건드리지 말 것."""
    bm = largest(bc[:, :, 3] >= ALPHA_BIN)
    if not bm.any():
        z = np.zeros(bm.shape, bool)
        return z, z
    ys = np.where(bm.any(axis=1))[0]
    top = int(ys.min())

    head = np.zeros_like(bm)
    if r == 0:
        # ★정면만 귀 높이에서 끊는다. 정면에서 귀 아래 옆면은 **볼(얼굴)**이지 두상이 아니다.
        #   목덜미까지 열었더니 볼이 머리카락에 먹혔다.
        head[top:top + EAR_TOP_FB[base_name][0] + 1] = True
    else:
        # 후면·프로필은 목덜미까지 머리카락 영역이다 (대표가 반복 지적한 자리).
        head[top:neck_end(bm, top) + 1] = True

    # ── 귀 ────────────────────────────────────────────────────────────────
    ear = np.zeros_like(bm)
    if r in (0, 1):
        # 정면·후면: 귀는 두상보다 **옆으로 튀어나온다**. 귀 위에서 잰 살색 폭 밖 = 귀.
        et = top + EAR_TOP_FB[base_name][r]
        sk = skinmask(bc)
        band = sk[max(0, et - 12):et]
        if band.any():
            xs = np.where(band.any(axis=0))[0]
            lo, hi = int(xs.min()), int(xs.max())
            ear[et:, :lo] = True
            ear[et:, hi + 1:] = True
    else:
        # 프로필: 귀는 머리 **가운데**에 있다 → 실측 상자(머리 중심 기준)로 지정.
        xs = np.where(bm[top:top + 78].any(axis=0))[0]
        mid = (int(xs.min()) + int(xs.max())) // 2
        dx0, dx1, y0, y1 = EAR_BOX_PROF[r]
        ear[top + y0:top + y1 + 1,
            max(0, mid + dx0):min(bm.shape[1], mid + dx1 + 1)] = True
    # ★귀는 넉넉히 남긴다. 좁게 잡았더니 정면·후면에서 귀가 헤어색에 먹혀 안 보였다
    #   (대표: "귀에 살색 하나도 안 보이고", "뒤에서 귀가 너무 안 보임").
    ear = ndimage.binary_dilation(ear, np.ones((5, 5), bool)) & bm

    # ── 얼굴 앞면 (눈·코·입) ──────────────────────────────────────────────
    keep_face = np.zeros_like(bm)
    b = BROW[base_name][r]
    if r == 0:
        # 정면: 눈썹 아래 + 얼굴 앞면의 좌우 폭 안쪽. 그 밖(관자놀이)은 두상이다.
        # ★자동 검출을 쓰면 머리 옆 외곽선을 눈으로 오인해 얼굴이 머리 전체 폭이 된다.
        #   base는 고정 파일이므로 실측값을 박는다 —
        #   남 눈·눈썹 x37~101 / 여 x29~111 (여캐가 눈 음영까지 넓다). 여유 없이 그대로.
        lo, hi = FACE_X[base_name]
        keep_face[top + b:, lo:hi + 1] = True
    elif r in (2, 3):
        # 프로필: 눈썹 아래 + 눈이 있는 쪽 절반
        xs = np.where(bm[top:top + 78].any(axis=0))[0]
        mid = (int(xs.min()) + int(xs.max())) // 2
        if r == 2:
            keep_face[top + b:, :mid + 1] = True
        else:
            keep_face[top + b:, mid:] = True
    # 후면(r==1)은 얼굴이 없다
    # ★keep도 반드시 머리 구간으로 자른다. 안 그러면 몸통 전체가 '건드리지 말 것'이 되어
    #   지도가 무의미해진다.
    keep_face &= bm & head

    keep = keep_face | (ear & head)
    must = bm & head & ~keep
    return must, keep


def eye_span(bc, bm, top):
    """정면에서 눈·눈썹 덩어리의 좌우 끝. 얼굴 앞면의 가로 범위로 쓴다."""
    r_, g_, b_ = bc[:, :, 0], bc[:, :, 1], bc[:, :, 2]
    dark = bm & (r_ < 70) & (g_ < 70) & (b_ < 70)
    # ★외곽선은 1px이 아니라 2~5px 두께다. 3x3 팽창으로 빼면 머리 옆 외곽선이 '눈'으로
    #   잡혀 눈 범위가 머리 전체 폭이 되고, 그러면 관자놀이까지 '얼굴'이 되어버린다.
    #   실루엣 경계에서 8px 이상 안쪽만 내부로 본다.
    inner = dark & (ndimage.distance_transform_edt(bm) > 8)
    inner[:top + 45] = False           # 정수리 장식 제외
    inner[top + 95:] = False           # 턱 아래 제외
    if not inner.any():
        return (0, bm.shape[1] - 1)
    xs = np.where(inner.any(axis=0))[0]
    return (max(0, int(xs.min()) - 4), min(bm.shape[1] - 1, int(xs.max()) + 4))


def main():
    out = {}
    for name in ["walk.png", "walk_female.png"]:
        p = os.path.join(HERE, name)
        if not os.path.exists(p):
            continue
        sheet = np.asarray(Image.open(p).convert("RGBA")).astype(int)
        vis = Image.new("RGB", (CW * 3, CH * 4), (255, 255, 255))
        for r in range(4):
            for c in range(3):
                bc = sheet[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
                must, keep = regions(bc, r, name)
                out[f"{name}|{r}|{c}"] = must
                v = bc.copy()
                v[must] = [255, 40, 40, 255]      # 빨강 = 덮어야 함
                v[keep] = [40, 220, 90, 255]      # 초록 = 건드리지 말 것
                vis.paste(Image.fromarray(v.astype(np.uint8), "RGBA").convert("RGB"),
                          (c * CW, r * CH))
                print(f"{name} r{r}c{c}  must={int(must.sum()):5d}  keep={int(keep.sum()):5d}")
        vis.resize((CW * 3 * 3, CH * 4 * 3), Image.NEAREST).save(
            os.path.join(HERE, f"_regions_{name}"))
        print(f"-> char/_regions_{name}")
    np.savez_compressed(os.path.join(HERE, "base_regions.npz"),
                        **{k: v for k, v in out.items()})
    print("-> char/base_regions.npz")


if __name__ == "__main__":
    main()
