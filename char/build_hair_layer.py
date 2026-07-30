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
# 머리 옆면 맹점(세로 이음매)의 최대 폭(앱 px). 실측 틈이 7px이라 8이면 덮이고,
# 앞머리 사이 이마(정면 실측 최대 76px)는 훨씬 넓어 걸리지 않는다.
SEAM_W = 8

MHAIR = os.path.join(DESK, "헤어", "남자")
FBASIC = os.path.join(DESK, "머피_로고삭제툴_에셋보관", "여자")
BALD_M = os.path.join(DESK, "빡빡이_눈썹포함시안2-Photoroom.png")
BALD_F = os.path.join(DESK, "빡빡이_여캐시안-Photoroom.png")

# ★ref = 차분 기준 시트. 대표 아이디어: 같은 배치에서 생성된 '기본헤어'를 기준으로 삼으면
#   몸 드리프트가 서로 상쇄된다(실측 몸 차분 71,366 -> 18,083, 75% 감소).
#   기본헤어 자신은 빡빡이(base)를 기준으로 뽑는다. ref=None 이면 base를 쓴다.
# ★force_col = 방향별로 쓸 프레임을 대표가 지정. 세미리프컷은 1열(col0)만 앞머리 가르마가
#   제대로 나왔다(대표 확인) → 4방향 전부 col0 강제.
CONFIG = [
    dict(out="hair_m_basic", label="남자 기본헤어", walk="walk.png",
         base=BALD_M, ref=None,
         hair=os.path.join(MHAIR, "남자기본헤어_clean-Photoroom.png")),
    dict(out="hair_m_semileaf", label="세미리프컷", walk="walk.png",
         base=BALD_M, ref=os.path.join(MHAIR, "남자기본헤어_clean-Photoroom.png"),
         hair=os.path.join(MHAIR, "세미리프컷_clean-Photoroom.png"),
         force_col=[0, 0, 0, 0]),
    dict(out="hair_m_part55", label="오대오 가르마펌", walk="walk.png",
         base=BALD_M, ref=os.path.join(MHAIR, "남자기본헤어_clean-Photoroom.png"),
         hair=os.path.join(MHAIR, "오대오가르마펌_clean-Photoroom.png")),
    dict(out="hair_f_basic", label="여자 기본헤어", walk="walk_female.png",
         base=BALD_F, ref=None,
         hair=os.path.join(FBASIC, "여자기본머리_clean-Photoroom.png")),
    dict(out="hair_f_bob_bang", label="앞머리 단발", walk="walk_female.png",
         base=BALD_F, ref=os.path.join(FBASIC, "여자기본머리_clean-Photoroom.png"),
         hair=os.path.join(NUKKI, "여자 검정단발머리_clean-Photoroom.png")),
    dict(out="hair_f_long", label="긴 생머리", walk="walk_female.png",
         base=BALD_F, ref=os.path.join(FBASIC, "여자기본머리_clean-Photoroom.png"),
         hair=os.path.join(NUKKI, "여자 검정생머리_clean-Photoroom.png"),
         # 긴 머리는 몸을 넓게 덮어 유령이 묻힌다. 유령 배제를 켜면 목 부근에서 머리가 끊긴다.
         ghost=False),
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
def quantize(arr, levels=5):
    """팔레트 양자화 — 색 커스터마이징(머리색 바꾸기)의 전제.

    소스는 그라데이션이라 90%를 덮는 색이 950~2200개다(실측). 그 상태로 머리색을 바꾸면
    수천 색을 각각 매핑해야 해서 지저분해진다. 명암 단계를 몇 개로 정리하면
    그 단계만 목표 색으로 갈아끼우면 되고, 도트 룩도 좋아진다.
    밝기로 나누고 각 구간의 대표색(중앙값)으로 대체한다 — 색을 지어내지 않는다.
    """
    m = arr[:, :, 3] >= ALPHA_BIN
    if not m.any():
        return arr, []
    rgb = arr[:, :, :3]
    lum = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2])
    vals = lum[m]
    edges = np.quantile(vals, np.linspace(0, 1, levels + 1))
    edges[0] -= 1; edges[-1] += 1
    out = arr.copy()
    pal = []
    for i in range(levels):
        sel = m & (lum > edges[i]) & (lum <= edges[i + 1])
        if not sel.any():
            continue
        rep = np.median(rgb[sel], axis=0).round().astype(int)
        out[sel, 0], out[sel, 1], out[sel, 2] = rep
        pal.append((tuple(int(v) for v in rep), int(sel.sum())))
    return out, pal


def hair_mask(hair, base, norm, ref=None, ghost=True):
    """헤어 마스크. base = 빡빡이(차분 기준), ref = 기본헤어(몸 유령 판정용, 없으면 base)."""
    if ref is None:
        ref = base
    hr, hg, hb = hair[:, :, 0], hair[:, :, 1], hair[:, :, 2]

    # ★헤어 색을 시트에서 학습한다. 고정 임계(max<=150)로는 갈색 머리가 걸러진다 —
    # 세미리프컷·오대오가르마펌은 갈색이라 하이라이트가 185까지 올라가고, 어두운 갈색
    # (87,55,49)은 살색 조건(r>g+18)에도 걸려 '살색'으로 오판된다(후면 삐짐 2327px).
    # 정수리(머리 최상단 12%)는 반드시 머리카락이므로 거기서 색 단계를 뽑아 기준으로 쓴다.
    crown = []
    for _r in range(4):
        _y0, _y1 = norm.rb[_r]
        _yc = _y0 + max(4, int((_y1 - _y0) * 0.12))
        for _c in range(3):
            _x0, _x1 = norm.cb[_c]
            sub = hair[_y0:_yc, _x0:_x1 + 1]
            sm = sub[:, :, 3] > 40
            if sm.any():
                crown.append(sub[:, :, :3][sm])
    cc = np.concatenate(crown) if crown else np.array([[40, 36, 42]])
    clum = 0.299 * cc[:, 0] + 0.587 * cc[:, 1] + 0.114 * cc[:, 2]
    pal = []
    for q in np.quantile(clum, [0.08, 0.28, 0.5, 0.72, 0.94]):
        sel = np.abs(clum - q) <= 14
        if sel.any():
            pal.append(np.median(cc[sel], axis=0))
    pal = np.array(pal) if pal else np.array([[40, 36, 42]])
    dist = np.min(np.abs(hair[:, :, None, :3] - pal[None, None, :, :]).max(axis=3), axis=2)
    dark = dist <= 62
    # 살색은 '밝고 붉은 기가 강한 것'만. 어두운 갈색 머리를 살리기 위해 조건을 좁혔다.
    skin = (hr >= 150) & (hr > hg + 45) & (hg > hb + 8)
    # ★알파 조건 필수. 투명 배경은 RGB가 (0,0,0)이라 'dark'로 판정되어,
    #   빼면 정수리 복구가 머리 위 빈 배경까지 헤어로 칠한다(실측: 셀 상단 전체 폭 검은 띠).
    hairish = dark & ~skin & (hair[:, :, 3] > 40)

    # ★차분은 반드시 **빡빡이 base** 대비다. 기본헤어를 차분 기준으로 쓰면 두 헤어가 겹치는
    # 머리카락(정수리 등)이 차분 0이 되어 빠지고, base가 빡빡이라 그 자리가 대머리로 비어버린다
    # (실측: 세미리프컷 좌 삐짐 2805px). 기본헤어는 아래 '몸 유령 판정'에만 쓴다.
    d = np.abs(hair[:, :, :3] - base[:, :, :3]).max(axis=2)
    newpx = (hair[:, :, 3] > 40) & (base[:, :, 3] <= 40)
    changed = (hair[:, :, 3] > 40) & (base[:, :, 3] > 40) & (d > DIFF_T)
    cand = (newpx | changed) & hairish

    # ★★몸 유령 배제 (대표 아이디어의 핵심).
    # 기준이 '같은 배치에서 생성된 기본헤어'일 때만 성립한다: 두 시트의 몸은 거의 같은
    # 위치로 삐뚤어져 있으므로, **머리 아래에서 기준 시트가 어두우면 그건 몸 윤곽선**이다.
    # (기본헤어는 짧아서 몸에 닿지 않는다 — 그래서 이 판정이 안전하다.)
    # 빡빡이를 기준으로 할 때는 몸 위치가 달라서 이 판정을 쓸 수 없었고, 그래서
    # 어깨·팔 윤곽선이 '헤어'로 잡혀 몸이 하나 더 보였다.
    # ★ref의 '어두운 픽셀 전부'를 대상으로 하면 기본헤어의 머리카락까지 걸려서, 긴 머리가
    # 목 부근에서 끊기고 아래쪽이 '머리에서 시작 안 한 조각'으로 버려진다(긴 생머리가 통째로
    # 사라졌다). 배제 대상은 **ref 실루엣의 경계선(=몸 윤곽선)**뿐이다 — 머리카락 내부는 경계가
    # 아니라서 자동으로 빠진다.
    ref_sil = ref[:, :, 3] > 40
    ref_dark = (ref_sil & ~ndimage.binary_erosion(ref_sil, np.ones((3, 3), bool))
                & (ref[:, :, :3].max(axis=2) <= 110))
    body = np.zeros(cand.shape, bool)
    for r in range(4):
        ry0, ry1 = norm.rb[r]
        body[ry0 + int((ry1 - ry0) * HEAD_FRAC):ry1 + 1] = True
    if ghost:
        cand &= ~(body & ndimage.binary_dilation(ref_dark, np.ones((3, 3), bool)))

    # ★★몸 드리프트 유령 제거 (AI는 "몸 그대로"라고 해도 매번 살짝 삐뚤게 그린다 — 대표 확인).
    # 핵심: **머리 아래에서 헤어 시트 자신의 실루엣 경계는 머리카락이 아니라 '몸 윤곽선'이다.**
    # 그 윤곽선이 base보다 1px 어긋나면 차분에 걸려 '헤어'로 잡히고, base 윤곽선 옆에
    # 한 겹 더 그려진다(대표: 팔-어깨 몸통 겹침, 목·귀 겹침).
    # base의 어두운 자리를 넓게(5px) 지우면 진짜 머리카락까지 파낸다(기각). 그래서
    # **헤어 시트 실루엣 경계 ∩ base 몸 경계 근처(2px) ∩ 머리 아래** 만 뺀다.
    # 몸에서 멀리 떨어진 머리카락(긴 머리)은 base 경계 근처가 아니라 그대로 남는다.
    hsil = hair[:, :, 3] > 40
    bsil = base[:, :, 3] > 40
    hedge = hsil & ~ndimage.binary_erosion(hsil, np.ones((3, 3), bool))
    bedge = bsil ^ ndimage.binary_erosion(bsil, np.ones((3, 3), bool))
    near_bedge = ndimage.binary_dilation(bedge, np.ones((5, 5), bool))
    body = np.zeros(cand.shape, bool)
    for r in range(4):
        ry0, ry1 = norm.rb[r]
        body[ry0 + int((ry1 - ry0) * HEAD_FRAC):ry1 + 1] = True
    cand &= ~(hedge & near_bedge & body)

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

    # ★★머리 아래(목·어깨·팔)에서는 base가 어두운 자리 근처를 헤어가 아예 갖지 않게 한다.
    # 헤어 시트의 몸이 AI 드리프트로 1px 어긋나게 그려져서, 그 어긋난 몸 윤곽선이 '헤어'로
    # 잡혀 base 윤곽선 옆에 한 겹 더 그려졌다(대표: 후면 걸음 팔-어깨 몸통 겹침, 목·귀 겹침).
    # 색이 어긋나 있어 same(색 일치) 규칙으로는 안 걸린다 → 위치로 잡는다.
    # 이러면 윤곽선은 항상 base 것 하나만 남는다.
    # ★기각한 접근: base가 어두운 자리 근처(5x5)를 머리 아래에서 전부 지우기.
    # 유령 윤곽선은 지워졌지만 **진짜 머리카락까지 파냈다** — 우측 목에 살색 쐐기가
    # 헤어를 뚫고 들어오고 후면 밑단이 갉였다. 헤어가 몸 윤곽선 위에 정당하게 걸치기 때문.
    # 몸 드리프트는 규칙으로 분리할 수 없다 → 재생성 시 몸을 base와 동일하게 받아야 한다.
    ghost = np.zeros_like(hm)

    # ★same(base와 같은 색)은 어디서든 지워도 안전하다 — base가 그 자리에 같은 색을 그리므로
    #   화면은 그대로고 '두 겹으로 그리는 것'만 없어진다. 어깨 외곽선이 겹쳐 '몸통이 하나 더'
    #   보이던 것도 이걸 안 지워서였다(대표: 후면 걸음에서 어깨에 몸통 하나 더).
    #   반면 shadow·skin을 머리 안쪽에서 지우면 구멍이 난다 → 경계만.
    inner = ndimage.binary_erosion(hm, np.ones((5, 5), bool))
    kill = same | ghost | ((shadow | skin) & ~inner)
    out = hc.copy()
    out[kill] = 0
    return out, int(same.sum()), int(ghost.sum()), int(skin.sum()), int(kill.sum())


GAP_MAX = 20        # 이보다 큰 틈은 메우지 않는다
GAP_HAIR_FRAC = 0.7  # 틈 경계의 이 비율 이상이 헤어여야 메운다


def gap_need(hc, bc):
    """합성 후 갇힌 투명 구멍(등-머리 사이 ㅣ). 메워야 할 자리를 마스크로 돌려준다.

    ★크기·경계 조건이 없으면 헤어 밑단과 어깨 사이의 넓은 틈까지 메워서
      **base의 어깨·팔 윤곽선을 헤어색으로 따라 그린다** → 몸통이 하나 더 보인다
      (대표: 후면 걸음에서 팔-어깨 겹침). 작고 헤어로 둘러싸인 틈만 메운다.
    """
    hm = hc[:, :, 3] >= ALPHA_BIN
    vis = hm | (bc[:, :, 3] >= ALPHA_BIN)
    holes = ndimage.binary_fill_holes(vis) & ~vis
    out = np.zeros(vis.shape, bool)
    if not holes.any():
        return out
    bm = bc[:, :, 3] >= ALPHA_BIN
    lab, n = ndimage.label(holes)
    for i in range(1, n + 1):
        comp = lab == i
        if comp.sum() > GAP_MAX:
            continue
        ring = ndimage.binary_dilation(comp, np.ones((3, 3), bool)) & ~comp
        h, b = int((ring & hm).sum()), int((ring & bm).sum())
        if h / max(1, h + b) >= GAP_HAIR_FRAC:
            out |= comp
    return out


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


SKULL_H = 42     # 정수리 돔 높이(앱 px)
HEAD_H = 78      # 두상 높이(앱 px). 이보다 아래는 목·어깨·팔     # 정수리 돔 높이(앱 px). 이보다 아래는 얼굴·목이라 헤어 밖이 정상이다.

# ★★방향별 얼굴 경계 = base 시트 실측 상수 (머리 최상단 기준 상대 y).
#   base 시트는 고정 파일이라 이 값도 고정이다 → AI 드리프트와 무관해진다.
#   측정: 눈썹 덩어리 최상단 y - 두상 최상단 y (col0 기준, 3열 편차 1px 이내).
#     남 walk.png        정면 y65/top11 -> 54 · 좌 y59/top12 -> 47 · 우 y57/top11 -> 46
#     여 walk_female.png 정면 y64/top11 -> 53 · 좌 y58/top11 -> 47 · 우 y57/top12 -> 45
#   ★남녀를 같은 값으로 쓰면 안 된다 — 1px씩 달라서 여캐 눈썹 윗줄을 건드린다.
BROW_Y_BY_BASE = {                # 후면(1)은 얼굴이 없다
    "walk.png": [54, None, 47, 46],
    "walk_female.png": [53, None, 47, 45],
}
#   귀 최상단: 좌 y=73(top12) -> 61 / 우 y=71(top11) -> 60. 안전하게 작은 값을 쓴다.
#   프로필에서 뒤통수를 덮되 **귀보다 아래로는 내려가지 않는다** — 귀를 헤어색으로
#   칠하면 귀가 사라진다.
EAR_Y = 60
# 귀 높이 아래에서 '뒤통수'로 볼 깊이(머리 뒤 끝 기준 앱 px). 프로필 귀는 머리 가운데라
# (좌 x70~89 / 우 x46~68, 머리 x17~120) 뒤 끝에서 28px 안쪽이면 귀에 닿지 않는다.
BACK_DEPTH = 28


def head_skin_need(hc, bc, r, brow=None):
    """★머리 영역에서 base 살색이 헤어 밖으로 보이는 것을 전부 덮는다.

    대표가 계속 지적한 결함: 옆에서 귀·뒤통수 살색, 앞머리·이마 살색, 정면 양쪽 빡빡이 삐짐.
    원인 = 헤어 시트를 뽑을 때 AI가 두상을 base보다 작게 그린다. 그래서 base 두상이
    헤어보다 크고, 차분 추출만으로는 그 차이를 메울 수 없다.

    ★이전엔 판정 기준을 헤어 시트 자신(truth)으로 삼았다가 롤백됐다(14ef1ed, sw v252) —
      헤어 시트의 캐릭터는 base와 얼굴 위치·크기가 달라서(AI가 두상을 작게 그림) 정규화해도
      얼굴이 어긋나고, 그 어긋난 마스크가 base의 눈을 덮어 눈알이 깨졌다.
      → **방향별 기하 규칙**으로 대체한다. 좌표는 walk.png에서 1회 실측해 고정값으로 박는다
      (walk.png는 재수정 금지 파일이라 좌표도 고정 → AI 드리프트·시트 오염과 무관해진다).

        정면 = 눈썹 위가 두상. 그 아래(눈·코·입)는 건드리지 않는다.
        후면 = 얼굴이 없다 → 두상 구간 전체.
        좌·우 = ①눈썹 위 전체(정수리는 앞뒤 구분 없이 머리카락이다)
               ②눈썹 아래는 **뒤통수 쪽 절반만**, 그것도 **귀 위까지만**.
               (귀보다 아래로 내려가면 귀를 헤어색으로 칠해 귀가 사라진다.)

    ★프로필에서 ②만 쓰면 정수리 앞쪽이 빠져서, 헤어가 거기까지 안 닿을 때 살색이 그대로
      남는다. ①이 그 구멍을 막는다.
    """
    hm = hc[:, :, 3] >= ALPHA_BIN
    bm = largest(bc[:, :, 3] >= ALPHA_BIN)
    if not hm.any() or not bm.any():
        return np.zeros_like(bm)
    ys = np.where(bm.any(axis=1))[0]
    top = int(ys.min())
    head = np.zeros_like(bm)
    head[top:top + HEAD_H] = True          # 두상 구간(목 위까지)

    def skinmask(a):
        R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
        return (a[:, :, 3] >= ALPHA_BIN) & (R >= 140) & (R > G + 30) & (G > B + 5)

    if brow is None:
        brow = BROW_Y_BY_BASE["walk.png"]
    bskin = skinmask(bc)
    skull = np.zeros_like(bm)
    if r == 1:      # 후면: 얼굴 없음 — 두상 구간 전체
        skull[:, :] = True
    else:
        skull[top:top + brow[r]] = True            # ① 눈썹 위 = 두상
        if r != 0:                                 # ② 프로필: 뒤통수 절반, 귀 위까지
            # ★절반 경계는 **두상 구간**에서 잰다. 몸 전체로 재면 팔·다리 폭이 섞여
            #   머리 중심과 어긋난다(우 col1 실측 2px 차이).
            xs = np.where(bm[top:top + HEAD_H].any(axis=0))[0]
            mid = (int(xs.min()) + int(xs.max())) // 2
            back = np.zeros_like(bm)
            if r == 2:      # 좌향 = 얼굴이 왼쪽 → 뒤통수는 오른쪽 절반
                back[:, mid:] = True
            else:           # 우향 = 얼굴이 오른쪽 → 뒤통수는 왼쪽 절반
                back[:, :mid + 1] = True
            back[top + EAR_Y:] = False
            # ★★뒤통수는 귀보다 훨씬 아래까지 이어진다. 위 back을 귀 높이에서 자르면
            #   대표가 본 '좌·우 뒤통수 살색'이 그대로 남는다(실측: 좌 x100~120, y75~95).
            #   프로필의 귀는 머리 **가운데**에 있으므로(좌 x70~89 / 우 x46~68),
            #   귀 높이 아래에서는 **머리 뒤 끝에서 BACK_DEPTH 이내**만 덮어 귀를 피한다.
            xs_h = np.where(bm[top:top + HEAD_H].any(axis=0))[0]
            hlo, hhi = int(xs_h.min()), int(xs_h.max())
            deep = np.zeros_like(bm)
            if r == 2:
                deep[:, max(0, hhi - BACK_DEPTH):] = True
            else:
                deep[:, :min(bm.shape[1], hlo + BACK_DEPTH + 1)] = True
            deep[:top + EAR_Y] = False       # 위쪽은 back이 이미 덮는다
            skull |= back | deep

    # ★★귀는 두상보다 옆으로 튀어나와 있다. 귀 높이 아래에서는 **귀 위에서 잰 두상 폭**
    #   안쪽만 덮는다 — 그 폭을 넘어 튀어나온 것이 귀다. 이 clamp가 없으면 후면에서
    #   귀까지 헤어색으로 칠해 귀가 사라진다.
    # ★폭은 반드시 **살색**으로 잰다. 실루엣으로 재면 검은 외곽선(두께 5px)이 폭에 섞여
    #   귀와 두상이 구분되지 않는다(실측: 실루엣 기준은 귀를 1px밖에 못 걸렀다).
    #   후면 실측 — 두상 살색 x21~117 / 귀 살색 x15~123 → 좌우 6px씩이 귀.
    ref_band = bskin[max(0, top + EAR_Y - 10):top + EAR_Y]
    if ref_band.any():
        rxs = np.where(ref_band.any(axis=0))[0]
        skull[top + EAR_Y:, :int(rxs.min())] = False
        skull[top + EAR_Y:, int(rxs.max()) + 1:] = False

    # ★두상 영역 안에서는 **색을 따지지 않는다.** 살색 조건으로 걸렀더니 관자놀이·귀 주변의
    #   중간톤(어두운 외곽선도 밝은 살색도 아닌 색)이 두 규칙 사이로 빠져나가, 대표가 본
    #   '정면 좌우 ㅣ 살색선'이 그대로 남았다(실측: 살색 기준으로는 정면 노출 0으로 잡혔다).
    #   기하 규칙이 이미 얼굴을 제외했으므로, 이 영역에 남은 base는 전부 '빡빡이 노출'이다.
    need = bm & head & skull & ~hm

    # ★★★두상 구간의 살색을 전부 칠하면 안 된다 — **앞머리 결이 뭉개진다**.
    #   그렇게 했더니 정면 이마가 통짜 덩어리가 되고 머리카락 사이로 비치던 이마가
    #   전부 메워졌다(대표 지적은 '좌우 ㅣ 살색선'이지 이마 전체가 아니다).
    #   결함은 **두상이 헤어 실루엣보다 옆으로 삐져나온 것**이다. 그래서 행마다
    #   헤어의 좌우 끝 밖에 있는 살색만 덮는다 — 헤어 폭 안쪽 살색은 '이마'라 그대로 둔다.
    # ★후면은 얼굴이 없어 이마 개념 자체가 없다. 거기서 이 제한을 걸면 뒤통수 구멍이
    #   안 메워지므로 후면만 전체 채우기를 유지한다.
    if r != 1:
        lateral = np.zeros_like(need)
        for y in range(top, min(top + HEAD_H, need.shape[0])):
            hx = np.where(hm[y])[0]
            if not len(hx):
                lateral[y] = True      # 헤어가 아예 없는 행 = 헤어선 위 정수리 → 전부 덮는다
                continue
            lateral[y, :int(hx.min())] = True
            lateral[y, int(hx.max()) + 1:] = True
        need &= lateral

    # ★★세로 이음매(대표: '정면 좌우 ㅣ 살색선') — 위 lateral 규칙으로는 절대 안 잡힌다.
    # 원인: base 검은 외곽선과 헤어가 같은 어두운 색이라 차분이 0이 되어 머리 **옆면**에
    # 세로로 긴 틈이 뚫린다(정수리 맹점과 같은 현상, 위치만 옆면). 실측 정면 x20~26 7px폭.
    # 그 틈은 **양옆이 헤어로 둘러싸여** 있어서 '헤어 바깥' 조건에 걸리지 않는다.
    # ★기각한 접근 2개 (추출 단계에서 고치려다 둘 다 얼굴을 망쳤다):
    #   ① base 실루엣 경계 근처를 열어 propagation → 프로필은 코·입이 경계에 있어 얼굴을 먹음
    #   ② 소스에서 가로 닫힘 → hairish가 눈썹까지 포함해 앞머리·눈썹을 이어붙여 머리가 무거워짐
    # → 얼굴이 이미 제외된 **여기(앱 셀)**에서, 좁은 틈만 메운다. 이마는 훨씬 넓어 안 걸린다.
    seam = np.zeros_like(need)
    for y in range(top, min(top + HEAD_H, need.shape[0])):
        hx = np.where(hm[y])[0]
        if len(hx) < 2:
            continue
        lo, hi = int(hx.min()), int(hx.max())
        x = lo
        while x <= hi:
            if bm[y, x] and not hm[y, x]:
                x2 = x
                while x2 <= hi and bm[y, x2] and not hm[y, x2]:
                    x2 += 1
                if x2 - x <= SEAM_W:
                    seam[y, x:x2] = True
                x = x2
            else:
                x += 1
    # ★skull(눈썹 위)로 제한하지 않는다 — 실측 이음매는 눈썹 아래 관자놀이까지 이어진다
    #   (정면 y53~79, 눈썹 y65). 얼굴은 넓게 열려 있어 '≤8px + 양옆 헤어' 조건에 안 걸린다.
    return need | (seam & head)


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

        # base 시트. ★walk.png(남캐)는 **절대 재생성하지 않는다** — 하드룰(base 시트 재수정 금지).
        # 이미 있는 파일을 읽어서 정합 기준으로만 쓴다. walk_female.png는 우리가 만든 것이라 생성한다.
        if cfg["walk"] not in walks:
            wpath = os.path.join(HERE, cfg["walk"])
            if cfg["walk"] == "walk.png":
                ws = Image.open(wpath).convert("RGBA")
                note = "기존 파일 사용(재생성 금지)"
            else:
                ws = norm.sheet()
                note = "정규화 생성"
                if not args.dry:
                    ws.save(wpath)
            walks[cfg["walk"]] = ws
            wa = np.asarray(ws).astype(int)
            m = largest(wa[0:CH, 0:CW, 3] >= ALPHA_BIN)
            ys = np.where(m.any(axis=1))[0]
            print("● %-16s 머리끝 y=%d 발끝 y=%d 키=%d  %s" % (
                cfg["walk"], ys.min(), ys.max(), ys.max() - ys.min() + 1, note))

        wsheet = np.asarray(walks[cfg["walk"]]).astype(int)
        brow = BROW_Y_BY_BASE[cfg["walk"]]      # 얼굴 경계는 base 시트마다 다르다(남녀 1px 차)
        hair = load(cfg["hair"])
        refsheet = load(cfg["ref"]) if cfg.get("ref") else None
        mask = hair_mask(hair, base, norm, refsheet, cfg.get("ghost", True))

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
            fc = cfg.get("force_col")
            ref = int(fc[r]) if fc else int(np.argmin(scores))   # 대표 지정이 있으면 그걸 쓴다
            chosen, _pal = quantize(cells[ref])

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
                n = (cover_need(moved, bc) | gap_need(moved, bc)
                     | head_skin_need(moved, bc, r, brow))
                need |= shift(n, -dx, -dy)
            chosen = paint(chosen, need)
            chosen, _ = drop_strays(chosen)

            info = []
            for c, (dx, dy) in enumerate(shifts):
                bc = wsheet[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
                cell = shift(chosen, dx, dy)
                oh = overhang(cell[:, :, 3] >= ALPHA_BIN, largest(bc[:, :, 3] >= ALPHA_BIN))
                leak = int(head_skin_need(cell, bc, r, brow).sum())   # 남은 두상 노출
                info.append((dx, dy, int(need.sum()), oh, leak))
                sheet.paste(Image.fromarray(cell.astype(np.uint8), "RGBA"), (c * CW, r * CH))

            print("   [%s] col%d 채택 | 제거 base복사%4d 유령%4d 살색%4d (총%4d) | "
                  "이동%s 틈메움%s | 삐짐%s 살색노출%s" % (
                      ROWNAME[r], ref, nsame, nshadow, nskin, nkill,
                      [(i[0], i[1]) for i in info], [i[2] for i in info], [i[3] for i in info],
                      [i[4] for i in info]))

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
