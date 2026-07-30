# -*- coding: utf-8 -*-
"""헤어 레이어 빌더 v2 — "base에 헤어만 쑉 얹힌" 결과를 만든다.

대표 지적(2026-07-30)에서 드러난 결함 6가지를 전부 구조로 막는다.

  결함                              대응
  --------------------------------- ------------------------------------------------
  빡빡이 두상이 헤어 밖으로 삐짐      ①키를 walk.png와 동일하게(209) ②정수리 외곽선 복구
                                     ③열마다 base 두상 위치로 평행이동
  목·턱·귀뒤가 검게 탐               base와 같은 색 픽셀(=이중 그리기)·그림자·살색 제거
  등과 머리 사이 ㅣ 여백             합성 후 갇힌 투명 구멍 메움
  반투명(체크무늬 비침)              알파 128 이진화, 유지 픽셀 alpha=255
  걸을 때 머리 출렁임                방향당 1프레임만 골라 3열에 복제(모양 고정)

★정수리가 빠지는 이유(여캐에서 실측): 정수리는 base의 검은 외곽선과 헤어의 검은 외곽선이
  같은 색이라 **차분이 0**이 된다. 그래서 차분 마스크만 쓰면 정수리 외곽선이 통째로 빠지고
  대머리가 위로 노출된다. → 머리 구간에서 '헤어색이면서 마스크에 인접한' 픽셀을 되살린다.

★walk.png 실측 규격: 키 209, 발끝 y=219 (TARGET_H=214 는 아이템 추출용 값이라 쓰면 안 된다.
  214로 만들면 여캐가 남캐보다 5px 커진다 — 실제로 그렇게 냈다가 고쳤다.)

    python char/build_hair_layer.py            # CONFIG 전체 빌드
    python char/build_hair_layer.py --dry      # 파일 안 쓰고 수치만
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "items")
DESK = r"C:\Users\allys\Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차"
NUKKI = os.path.join(DESK, "머피_로고삭제툴_에셋보관", "여캐")

# ===== 앱 격자 하드룰 (walk.png 실측) =====
CW, CH = 141, 224
TARGET_H, PAD_BOTTOM = 209, 4
ALPHA_BIN = 128
PADP = 240
ROWNAME = ["정면", "후면", "좌", "우"]

# ===== 추출 파라미터 (여캐 실측으로 고른 값) =====
DIFF_T = 40          # RGB 변화 판정
DARK_MAX = 150       # 헤어·외곽선은 어둡다
SKIN_R = 95          # 살색 하한. ★올리면 앞머리 끝이 깎인다(120·135 실측 악화)
MIN_COMP = 500       # 소스 해상도 최소 덩어리
HOLE_MAX = 2000      # 이보다 작은 내부 구멍만, 그리고 헤어색일 때만 메움
STRAY_MAX = 40       # 앱 셀 기준 고립조각 하한
SAME_T = 24          # base와 같은 색 판정 = 이중 그리기
HEAD_FRAC = 0.42     # 머리 구간(정수리 복구·삐짐 판정에 쓰는 세로 비율)
MARGIN = 34          # 헤어가 몸보다 옆으로 벌어지는 여유

CONFIG = [
    dict(out="hair_fem_bob", label="여-단발",
         base=os.path.join(DESK, "빡빡이_여캐시안-Photoroom.png"),
         hair=os.path.join(NUKKI, "여자 검정단발머리_clean-Photoroom.png"),
         walk="walk_female.png"),
    dict(out="hair_fem_long", label="여-생머리",
         base=os.path.join(DESK, "빡빡이_여캐시안-Photoroom.png"),
         hair=os.path.join(NUKKI, "여자 검정생머리_clean-Photoroom.png"),
         walk="walk_female.png"),
]


# ---------- 공통 ----------
def load(p):
    return np.asarray(Image.open(p).convert("RGBA")).astype(int)


def pad_img(arr):
    im = Image.fromarray(arr.astype(np.uint8), "RGBA")
    o = Image.new("RGBA", (im.width + PADP * 2, im.height + PADP * 2), (0, 0, 0, 0))
    o.paste(im, (PADP, PADP))
    return o


def detect_grid(al):
    def band(vals, t=3, minlen=30):
        segs, a = [], None
        for i, v in enumerate(vals):
            if v > t and a is None:
                a = i
            elif v <= t and a is not None:
                segs.append((a, i - 1)); a = None
        if a is not None:
            segs.append((a, len(vals) - 1))
        return [s for s in segs if s[1] - s[0] > minlen]
    H, W = al.shape
    return band([(al[y] > 30).sum() for y in range(H)]), band([(al[:, x] > 30).sum() for x in range(W)])


def largest(m):
    lab, n = ndimage.label(m, np.ones((3, 3), bool))
    if n <= 1:
        return m
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    return lab == (int(np.argmax(sizes)) + 1)


def binarize(cell_img):
    a = np.asarray(cell_img).astype(int).copy()
    keep = a[:, :, 3] >= ALPHA_BIN
    a[:, :, 3] = np.where(keep, 255, 0)
    a[~keep] = 0
    return a


def drop_strays(arr):
    m = arr[:, :, 3] > 0
    lab, n = ndimage.label(m, np.ones((3, 3), bool))
    if n <= 1:
        return arr, 0
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    dropped = 0
    for i, s in enumerate(sizes, start=1):
        if s < STRAY_MAX and s < sizes.max():
            arr[lab == i] = 0
            dropped += int(s)
    return arr, dropped


def raggedness(arr):
    m = arr[:, :, 3] > 0
    if not m.any():
        return 9e9
    return (m & ~ndimage.binary_erosion(m, np.ones((3, 3), bool))).sum() / m.sum()


# ---------- 정규화 ----------
class Norm:
    """base 시트에서 셀별 정규화 변환을 계산해 보관한다. 헤어도 이 변환을 쓴다."""

    def __init__(self, base_arr):
        self.arr = base_arr
        self.rb, self.cb = detect_grid(base_arr[:, :, 3])
        assert len(self.rb) == 4 and len(self.cb) == 3, "격자 검출 실패 %s %s" % (self.rb, self.cb)
        self.pad = pad_img(base_arr)
        self.tf = {}
        for r in range(4):
            for c in range(3):
                y0, y1 = self.rb[r]; x0, x1 = self.cb[c]
                sub = base_arr[y0:y1 + 1, x0:x1 + 1, 3] > 40
                ys, xs = np.where(sub)
                bx0, by0 = x0 + xs.min(), y0 + ys.min()
                bw, bh = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
                sc = min(TARGET_H / bh, (CW - 2) / bw)
                offx = (CW - round(bw * sc)) // 2
                offy = CH - PAD_BOTTOM - round(bh * sc)
                self.tf[(r, c)] = (bx0, by0, sc, offx, offy)

    def cell(self, padded, r, c):
        bx0, by0, sc, offx, offy = self.tf[(r, c)]
        l = bx0 + PADP - offx / sc
        t = by0 + PADP - offy / sc
        return padded.resize((CW, CH), Image.LANCZOS, box=(l, t, l + CW / sc, t + CH / sc))

    def sheet(self):
        out = Image.new("RGBA", (CW * 3, CH * 4), (0, 0, 0, 0))
        for r in range(4):
            for c in range(3):
                out.paste(Image.fromarray(binarize(self.cell(self.pad, r, c)).astype(np.uint8), "RGBA"),
                          (c * CW, r * CH))
        return out


def skull_ref(bm):
    """두상 기준점 = 실루엣 최상단 y, 상단 18px 밴드의 중심 x."""
    m = largest(bm)
    ys = np.where(m.any(axis=1))[0]
    top = int(ys.min())
    xs = np.where(m[top:top + 18].any(axis=0))[0]
    return top, (int(xs.min()) + int(xs.max())) / 2.0


# ---------- 헤어 마스크 (소스 해상도) ----------
def hair_mask(hair, base, norm):
    hr, hg, hb = hair[:, :, 0], hair[:, :, 1], hair[:, :, 2]
    dark = hair[:, :, :3].max(axis=2) <= DARK_MAX
    skin = (hr >= SKIN_R) & (hr > hg + 18) & (hg >= hb - 4)
    # ★알파 조건 필수. 투명 배경은 RGB가 (0,0,0)이라 'dark'로 판정되어,
    #   빼면 정수리 복구가 머리 위 빈 배경까지 헤어로 칠한다(실측: 셀 상단 전체 폭 검은 띠).
    hairish = dark & ~skin & (hair[:, :, 3] > 40)

    d = np.abs(hair[:, :, :3] - base[:, :, :3]).max(axis=2)
    newpx = (hair[:, :, 3] > 40) & (base[:, :, 3] <= 40)
    changed = (hair[:, :, 3] > 40) & (base[:, :, 3] > 40) & (d > DIFF_T)
    cand = (newpx | changed) & hairish

    H, W = d.shape
    mask = np.zeros((H, W), bool)
    for r in range(4):
        ry0, ry1 = norm.rb[r]
        head_hi = ry0 + int((ry1 - ry0) * 0.45)
        # 정수리 복구 구간 — 여기서만 '헤어색이고 마스크에 붙은' 픽셀을 되살린다.
        crown_hi = ry0 + int((ry1 - ry0) * HEAD_FRAC)
        for c in range(3):
            x0 = max(0, norm.cb[c][0] - MARGIN)
            x1 = min(W - 1, norm.cb[c][1] + MARGIN)
            y0, y1 = max(0, ry0 - 12), min(H - 1, ry1 + 12)
            sub = cand[y0:y1 + 1, x0:x1 + 1]
            lab, n = ndimage.label(sub, np.ones((3, 3), bool))
            keep = np.zeros_like(sub)
            for i in range(1, n + 1):
                comp = lab == i
                if comp.sum() < MIN_COMP:
                    continue
                ys = np.where(comp.any(axis=1))[0] + y0
                if ys.min() > head_hi:          # 머리에서 시작하지 않은 조각
                    continue
                keep |= comp

            # ★정수리 외곽선 복구: 차분이 0이라 빠진 어두운 외곽선을 되살린다.
            # 범위를 '지금 마스크 최상단 바로 위'로 못 박는다. 머리 구간 전체로 열면
            # 얼굴의 눈·눈썹(어둡고 살색 아님)까지 빨아들여 겹쳐 보이게 된다(실측: 픽셀 67% 폭증).
            if keep.any():
                mtop = int(np.where(keep.any(axis=1))[0].min())
                passable = hairish[y0:y1 + 1, x0:x1 + 1].copy()
                passable[min(passable.shape[0], mtop + 7):] = False
                passable[max(0, crown_hi - y0):] = False
                if passable.any():
                    keep = ndimage.binary_propagation(keep, mask=(keep | passable))

            # 구멍은 안이 헤어색일 때만 메운다 (귀를 삼키지 않게)
            filled = ndimage.binary_fill_holes(keep)
            holes = filled & ~keep
            hl, hn = ndimage.label(holes)
            for i in range(1, hn + 1):
                comp = hl == i
                if comp.sum() <= HOLE_MAX and hairish[y0:y1 + 1, x0:x1 + 1][comp].mean() >= 0.8:
                    keep |= comp
            mask[y0:y1 + 1, x0:x1 + 1] |= keep
    return mask


# ---------- 정리: base 복사·그림자 제거 ----------
def strip_base_echo(hc, bc):
    """base가 이미 그리는 것을 헤어가 또 그리면 외곽선이 두 겹이 되어 검게 탄다.
    ①base와 같은 색 ②base 색을 어둡게만 깐 그림자 — 둘 다 지운다."""
    hm = hc[:, :, 3] >= ALPHA_BIN
    bm = bc[:, :, 3] >= ALPHA_BIN
    over = hm & bm
    d = np.abs(hc[:, :, :3] - bc[:, :, :3]).max(axis=2)
    same = over & (d <= SAME_T)

    def luma(x):
        return 0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2]

    ratio = np.divide(luma(hc), np.maximum(luma(bc), 1e-6))
    hue_close = np.abs((hc[:, :, 0] - hc[:, :, 2]) - (bc[:, :, 0] - bc[:, :, 2])) <= 42
    shadow = over & ~same & hue_close & (ratio >= 0.42) & (ratio <= 0.90)

    R, G, B = hc[:, :, 0], hc[:, :, 1], hc[:, :, 2]
    skin = hm & (R >= 120) & (R > G + 25) & (G > B + 5)

    # ★same(base와 같은 색)은 어디서든 지워도 안전하다 — base가 그 자리에 같은 색을 그리므로
    #   화면은 그대로고 '두 겹으로 그리는 것'만 없어진다. 어깨 외곽선이 겹쳐 '몸통이 하나 더'
    #   보이던 것도 이걸 안 지워서였다(대표: 후면 걸음에서 어깨에 몸통 하나 더).
    #   반면 shadow·skin을 머리 안쪽에서 지우면 구멍이 난다 → 경계만.
    inner = ndimage.binary_erosion(hm, np.ones((5, 5), bool))
    kill = same | ((shadow | skin) & ~inner)
    out = hc.copy()
    out[kill] = 0
    return out, int(same.sum()), int(shadow.sum()), int(skin.sum()), int(kill.sum())


def gap_need(hc, bc):
    """합성 후 갇힌 투명 구멍(등-머리 사이 ㅣ). 메워야 할 자리를 마스크로 돌려준다."""
    vis = (hc[:, :, 3] >= ALPHA_BIN) | (bc[:, :, 3] >= ALPHA_BIN)
    holes = ndimage.binary_fill_holes(vis) & ~vis
    if not holes.any():
        return np.zeros(vis.shape, bool)
    hm = hc[:, :, 3] >= ALPHA_BIN
    return holes & ndimage.binary_dilation(hm, np.ones((3, 3), bool))


def paint(hc, need):
    """need 자리를 가장 가까운 헤어 픽셀 색으로 채운다 (색을 지어내지 않는다)."""
    if not need.any():
        return hc
    hm = hc[:, :, 3] >= ALPHA_BIN
    if not hm.any():
        return hc
    idx = ndimage.distance_transform_edt(~hm, return_distances=False, return_indices=True)
    out = hc.copy()
    ys, xs = np.where(need)
    out[ys, xs, :3] = hc[idx[0][ys, xs], idx[1][ys, xs], :3]
    out[ys, xs, 3] = 255
    return out


SKULL_H = 42     # 정수리 돔 높이(앱 px). 이보다 아래는 얼굴·목이라 헤어 밖이 정상이다.


def cover_need(hc, bc):
    """정수리에서 base 외곽선이 헤어보다 밖에 남으면 검은 테두리가 두 겹으로 보인다.
    (대표: '이마에 도트 검은거 한 줄 더 튀어나옴') → 덮어야 할 자리를 마스크로 돌려준다."""
    hm = hc[:, :, 3] >= ALPHA_BIN
    bm = largest(bc[:, :, 3] >= ALPHA_BIN)
    if not hm.any() or not bm.any():
        return np.zeros_like(hm)
    top = int(np.where(bm.any(axis=1))[0].min())
    band = np.zeros_like(bm)
    band[top:top + SKULL_H] = True
    # base의 검은 외곽선은 1px이 아니라 2~3px 두께다. 1px 링만 덮으면 나머지가 남아
    # 여전히 두 겹으로 보인다. 그래서 '어두운 픽셀'을 두께 상관없이 덮는다.
    # ★살색 조건이 핵심: 이게 없으면 측면에서 이마·얼굴까지 헤어색으로 칠해버린다.
    dark_base = bc[:, :, :3].max(axis=2) <= 110
    near = ndimage.binary_dilation(hm, np.ones((7, 7), bool))
    need = bm & dark_base & ~hm & near & band

    # ★관자놀이~이마에서 base 살색이 앞머리 경계 밖으로 새는 것도 덮는다
    #   (대표: '오른쪽 이동 중 귀 위·귀 아래·이마가 살색'). 실측 75~155px, 후면은 0~10px.
    #   범위를 머리 구간(70px) + 헤어에서 3px 안쪽으로 묶어 얼굴 옆선(코·턱)은 건드리지 않는다.
    # ★두상이 헤어보다 살짝 삐진 곳을 색으로 판정하면 안 된다. 귀 주변은 어두운 외곽선도
    #   밝은 살색도 아닌 중간톤이라 두 규칙 사이로 빠져나간다(대표: 후면 양쪽 귀쪽 이상).
    #   대신 '헤어를 몇 px 늘리면 두상을 덮는가'로 판정한다. 삐진 폭이 GROW 이내면 늘리고,
    #   그보다 크면 그건 얼굴 옆선(코·턱)이므로 건드리지 않는다 — 이게 얼굴을 지키는 장치다.
    GROW = 3
    top2 = int(np.where(bm.any(axis=1))[0].min())
    hband = np.zeros_like(bm); hband[top2:top2 + 70] = True

    # ★관자놀이 노출은 행 양끝이 아니라 '앞머리 사이에 끼인' 살색이다(위아래로 헤어가 있다).
    #   그래서 위 GROW 규칙으로는 닿지 않는다. 세로로 끼인 살색만 덮는다.
    #   실측: 우 75~96px / 좌 73~91px 이 걸리고, 정면은 6~14px뿐이라 얼굴은 안 건드린다
    #   (정면의 헤어밖 살색 212px = 얼굴. 끼임 조건이 그걸 걸러낸다).
    R, G, B = bc[:, :, 0], bc[:, :, 1], bc[:, :, 2]
    skin = bm & (R >= 150) & (R > G + 20) & (G > B + 5)
    above = np.cumsum(hm, axis=0) > 0
    below = np.cumsum(hm[::-1], axis=0)[::-1] > 0
    need |= skin & ~hm & above & below & hband & ndimage.binary_dilation(hm, np.ones((7, 7), bool))

    for y in range(top2, min(top2 + 70, bm.shape[0])):
        hx = np.where(hm[y])[0]
        bx = np.where(bm[y])[0]
        if not len(hx) or not len(bx):
            continue
        if 0 < hx.min() - bx.min() <= GROW:
            need[y, bx.min():hx.min()] = True
        if 0 < bx.max() - hx.max() <= GROW:
            need[y, hx.max() + 1:bx.max() + 1] = True
    return need


def overhang(hm, bm):
    ys = np.where(bm.any(axis=1))[0]
    if not len(ys) or not hm.any():
        return 0
    top = int(ys.min())
    lim = top + SKULL_H          # 얼굴 옆선을 세지 않도록 정수리 돔으로 한정
    n = 0
    for y in range(top, min(lim + 1, bm.shape[0])):
        bx = np.where(bm[y])[0]
        if not len(bx):
            continue
        hx = np.where(hm[y])[0]
        if not len(hx):
            n += len(bx); continue
        n += int((bx < hx.min()).sum() + (bx > hx.max()).sum())
    return n


def shift(arr, dx, dy):
    out = np.zeros_like(arr)
    h, w = arr.shape[:2]
    ys0, ys1 = max(0, dy), min(h, h + dy)
    xs0, xs1 = max(0, dx), min(w, w + dx)
    out[ys0:ys1, xs0:xs1] = arr[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="파일 안 쓰고 수치만")
    ap.add_argument("--only", nargs="*", help="특정 out 이름만")
    args = ap.parse_args()

    walks = {}
    for cfg in CONFIG:
        if args.only and cfg["out"] not in args.only:
            continue
        base = load(cfg["base"])
        norm = Norm(base)

        # base 시트 (키 209로 walk.png와 통일)
        if cfg["walk"] not in walks:
            ws = norm.sheet()
            walks[cfg["walk"]] = ws
            wa = np.asarray(ws).astype(int)
            m = largest(wa[0:CH, 0:CW, 3] >= ALPHA_BIN)
            ys = np.where(m.any(axis=1))[0]
            print("● %s  머리끝 y=%d 발끝 y=%d 키=%d  (walk.png와 같아야 함: 11/219/209)" % (
                cfg["walk"], ys.min(), ys.max(), ys.max() - ys.min() + 1))
            if not args.dry:
                ws.save(os.path.join(HERE, cfg["walk"]))

        wsheet = np.asarray(walks[cfg["walk"]]).astype(int)
        hair = load(cfg["hair"])
        mask = hair_mask(hair, base, norm)

        # 헤어 RGBA (투명 픽셀 RGB도 헤어색으로 채워 리샘플 헤일로 방지)
        med = np.median(hair[:, :, :3][mask], axis=0).astype(int) if mask.any() else np.array([60, 54, 66])
        hr = np.zeros(hair.shape, int)
        hr[:, :, 0], hr[:, :, 1], hr[:, :, 2] = med
        hr[mask, :3] = hair[mask, :3]
        hr[:, :, 3] = np.where(mask, 255, 0)
        hair_pad = pad_img(hr)

        print("■ %s (%s)  헤어색 %s" % (cfg["label"], cfg["out"], tuple(med)))
        sheet = Image.new("RGBA", (CW * 3, CH * 4), (0, 0, 0, 0))
        for r in range(4):
            # 방향당 1프레임 선택 (모양 고정 = 출렁임 없음)
            cells = [binarize(norm.cell(hair_pad, r, c)) for c in range(3)]
            scores = [raggedness(x) for x in cells]
            ref = int(np.argmin(scores))
            chosen = cells[ref]

            bref = wsheet[r * CH:(r + 1) * CH, ref * CW:(ref + 1) * CW]
            chosen, nsame, nshadow, nskin, nkill = strip_base_echo(chosen, bref)
            chosen, _ = drop_strays(chosen)
            top_ref, cx_ref = skull_ref(bref[:, :, 3] >= ALPHA_BIN)

            # ★후처리를 열마다 따로 하면 프레임마다 모양이 달라져 걸을 때 깜빡인다
            #   (실측 18~627px 차이. 대표: '왼쪽 갈 때 앞머리 구멍이 채워졌다 메꿔졌다 반복').
            #   그래서 3열에서 필요한 자리를 모두 모아 기준 좌표계로 되돌린 뒤,
            #   기준 프레임에 **한 번만** 칠한다. 결과적으로 3열은 평행이동만 다르다.
            shifts = []
            for c in range(3):
                bc = wsheet[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
                top_c, cx_c = skull_ref(bc[:, :, 3] >= ALPHA_BIN)
                shifts.append((int(round(cx_c - cx_ref)), int(top_c - top_ref)))

            need = np.zeros((CH, CW), bool)
            for c, (dx, dy) in enumerate(shifts):
                bc = wsheet[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
                moved = shift(chosen, dx, dy)
                n = cover_need(moved, bc) | gap_need(moved, bc)
                need |= shift(n, -dx, -dy)
            chosen = paint(chosen, need)
            chosen, _ = drop_strays(chosen)

            info = []
            for c, (dx, dy) in enumerate(shifts):
                bc = wsheet[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
                cell = shift(chosen, dx, dy)
                oh = overhang(cell[:, :, 3] >= ALPHA_BIN, largest(bc[:, :, 3] >= ALPHA_BIN))
                info.append((dx, dy, int(need.sum()), oh))
                sheet.paste(Image.fromarray(cell.astype(np.uint8), "RGBA"), (c * CW, r * CH))

            print("   [%s] col%d 채택 | 제거 base복사%4d 그림자%4d 살색%4d (총%4d) | "
                  "이동%s 틈메움%s | 삐짐%s" % (
                      ROWNAME[r], ref, nsame, nshadow, nskin, nkill,
                      [(i[0], i[1]) for i in info], [i[2] for i in info], [i[3] for i in info]))

        a = np.asarray(sheet).astype(int)
        semi = int(((a[:, :, 3] > 0) & (a[:, :, 3] < 255)).sum())
        print("   반투명 %d px %s" % (semi, "" if semi == 0 else "★위반"))
        if not args.dry:
            sheet.save(os.path.join(ITEMS, cfg["out"] + ".png"))
            # 썸네일 = 정면 전신 렌더 (헤어는 대표 아이콘이 없는 슬롯)
            t = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
            t.alpha_composite(Image.fromarray(wsheet[0:CH, 0:CW].astype(np.uint8), "RGBA"))
            t.alpha_composite(sheet.crop((0, 0, CW, CH)))
            ta = np.asarray(t)[:, :, 3]
            ys, xs = np.where(ta > 0)
            t.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)).save(
                os.path.join(ITEMS, cfg["out"] + "_thumb.png"))
            print("   -> items/%s.png + 썸네일" % cfg["out"])
        print()


if __name__ == "__main__":
    main()
