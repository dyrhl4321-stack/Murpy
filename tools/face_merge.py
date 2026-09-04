# -*- coding: utf-8 -*-
"""AI 시트의 얼굴+머리만 base 시트에 얹는다 — 몸·옷·걸음은 base 픽셀 그대로.

    python tools/face_merge.py --base char/walk.png --ai char/faces/hyunsu.png --out char/faces/hyunsu.png

★왜 필요한가 (9-04 대표 지적): baked(=AI가 몸까지 통째로 그림)는 옷 색·몸 비율이 base에서 드리프트한다
  (실측: 베이지 탱크톱 → 흰옷). 프롬프트로는 보장이 안 되고, base 픽셀을 실제로 남기는 합성만이 보장한다.

방식: 셀마다 base 목선을 찾아
  · 목선 위  = AI 픽셀(얼굴+머리)로 통째 교체
  · 목선 아래 = base 픽셀 유지 + AI 머리카락만 flood 로 따라 내려와 위에 얹음(긴머리 보존)
"""
import os, sys, argparse
import numpy as np
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')

CW, CH = 141, 224          # 셀 규격 (3열 4행 = 423x896)
COLS, ROWS = 3, 4


def neck_y(cell):
    """머리 아래 가장 좁은 행 = 목. 머리통이 큰 chibi 라 y 90~140 대역에서 찾는다."""
    op = cell[..., 3] > 128
    w = op.sum(1)
    band = w[90:140].astype(int)
    band[band == 0] = 9999
    return 90 + int(band.argmin())


DARK = 150          # RGB 합이 이보다 어두우면 외곽선 취급(머리·옷 공용이라 색으로는 구분 불가)


def _uniq(cols, k=48):
    if len(cols) == 0:
        return np.zeros((1, 3), int)
    u = np.unique(cols, axis=0)
    return u[:: max(1, len(u) // k)]


def _dilate(m, n=1):
    for _ in range(n):
        d = m.copy()
        d[1:, :] |= m[:-1, :]; d[:-1, :] |= m[1:, :]
        d[:, 1:] |= m[:, :-1]; d[:, :-1] |= m[:, 1:]
        m = d
    return m


def skin_mask(cell):
    """피부(얼굴·목)만 — 금발(r-g 가 작다)이 안 걸리도록 g < r*0.80 을 쓴다."""
    r, g, b, al = (cell[..., i].astype(int) for i in range(4))
    return (al > 128) & (r > 150) & (r > b + 50) & (g < r * 0.80) & (g > b)


def shoulder_y(cell, around, span=25):
    """★이음선 = 목-어깨 경계. 피부 폭이 가장 좁은 곳(목)에서 아래로 내려가다
    폭이 확 넓어지는 첫 행 = 어깨가 시작되는 곳.

    ★왜 여기서 자르나(9-04): 목 한가운데(실루엣 최소폭)에서 자르면 AI 턱 외곽선과
      base 목 그림자가 겹쳐 검은 띠 두 겹 = '목 잘림'이 된다. 목은 AI 가 통째로 주고
      어깨부터 base 가 받으면 이음선이 안 보인다.
    얼굴이 없는 칸(뒤통수)은 None — 호출부에서 다른 칸의 값을 쓴다."""
    w = skin_mask(cell).sum(1)
    lo, hi = max(1, around - span), min(cell.shape[0] - 1, around + span)
    seg = w[lo:hi].astype(int)
    if (seg > 0).sum() < 3:
        return None
    ymin = lo + int(np.where(seg > 0, seg, 9999).argmin())
    wmin = int(w[ymin])
    for y in range(ymin + 1, hi):
        if w[y] > max(wmin * 1.8, wmin + 10):
            return y
    return None


def fit_head(acell, ai_y, base_y):
    """AI 머리를 세로로 눌러/늘려 AI 의 목-어깨 경계가 base 의 그것에 오게 한다.
    ★안 하면 AI 얼굴이 base 보다 길어 이음선에서 턱이 잘린다(9-04 '목 잘림')."""
    if not ai_y or ai_y == base_y:
        return acell
    h = acell.shape[0]
    nh = max(2, int(round(h * base_y / float(ai_y))))
    im = Image.fromarray(acell, 'RGBA').resize((acell.shape[1], nh), Image.LANCZOS)
    out = np.zeros_like(acell)
    n = min(nh, h)
    out[:n] = np.array(im)[:n]
    return out


def _erode(m, n=1):
    for _ in range(n):
        e = m.copy()
        e[1:, :] &= m[:-1, :]; e[:-1, :] &= m[1:, :]
        e[:, 1:] &= m[:, :-1]; e[:, :-1] &= m[:, 1:]
        m = e
    return m


def _attached(mask, anchor_row, ay):
    """머리 뭉치(목선 바로 위 머리)와 실제로 이어진 덩어리만 남긴다 — 몸 위에 뜬 점·잔털 제거."""
    from scipy import ndimage
    m = mask.copy()
    m[ay] |= anchor_row                                  # 목선 위 머리를 앵커로 붙여 라벨링
    lab, _ = ndimage.label(m)
    keep = np.unique(lab[ay][anchor_row & (lab[ay] > 0)])
    return np.isin(lab, keep) & mask


def outside_hair(acell, bcell, ny):
    """★확실한 머리카락 = 목선 아래에서 base 실루엣 **바깥**으로 삐져나온 AI 픽셀.
    몸·옷은 base 실루엣 안에만 있으므로, 밖으로 나온 건 흘러내린 머리뿐이다.
    (색 팔레트를 정수리에서 뽑으면 금발↔흰옷처럼 안 갈리는 경우가 생겨 이 기하 신호를 쓴다.)"""
    ao = acell[..., 3] > 128
    bo = _dilate(bcell[..., 3] > 128, 2)     # base 외곽선·리샘플 오차 여유 2px
    out = ao & ~bo
    out[:ny] = False
    return out


def hair_mask_below(acell, bcell, ny, tol=60, min_seed=25):
    """목선 아래 머리카락 마스크 — 실루엣 밖 머리(확실)에서 색 팔레트를 얻어,
    그 색에 가까우면서 위에서 연결돼 내려오는 픽셀까지 머리로 인정한다.

    ★두 관문을 모두 통과해야 머리다(둘 중 하나만으론 샌다 — 9-04 실측):
      ① 머리색과 L1 %d 이내   — 흰옷(금발과 L1 121)이 여기서 걸린다
      ② base 몸색보다 머리색에 더 가까움 — AI 피부(금발과 L1 40)가 여기서 걸린다
    base 팔레트는 base 시트에서 뽑으므로 AI 드리프트에 오염되지 않는다.
    """ % tol
    op = acell[..., 3] > 128
    rgb = acell[..., :3].astype(int)
    bright = op & (rgb.sum(-1) >= DARK)

    seed = outside_hair(acell, bcell, ny)
    if (seed & bright).sum() < min_seed:                 # 짧은 머리 = 목 아래 머리 없음
        return np.zeros(op.shape, bool)
    pal = _uniq(rgb[seed & bright])

    bop = (bcell[..., 3] > 128).copy(); bop[:ny] = False
    bbright = bop & (bcell[..., :3].astype(int).sum(-1) >= DARK)
    bpal = _uniq(bcell[bbright][:, :3].astype(int))      # base 의 옷·팔다리 색(정본)

    dh = np.abs(rgb[:, :, None, :] - pal[None, None, :, :]).sum(-1).min(-1)
    db = np.abs(rgb[:, :, None, :] - bpal[None, None, :, :]).sum(-1).min(-1)
    # ★씨앗(실루엣 밖)도 색 관문을 통과해야 한다 — AI 팔·옷이 base 실루엣 밖으로 조금 삐져나오면
    #   그것까지 머리로 붙어 몸 위에 잔선으로 남는다(9-04 실측).
    like = bright & (dh <= tol) & (dh < db)

    mask = np.zeros(op.shape, bool)
    mask[ny - 1] = like[ny - 1]                          # 목선 바로 위의 머리색 픽셀이 씨앗
    for y in range(ny, acell.shape[0]):
        prev = mask[y - 1]
        cur = like[y] & (prev | np.roll(prev, 1) | np.roll(prev, -1))
        for _ in range(CW):                              # 같은 행 안에서 좌우로 번지기
            grown = cur | ((np.roll(cur, 1) | np.roll(cur, -1)) & like[y])
            if (grown == cur).all():
                break
            cur = grown
        mask[y] = cur

    # ★1px 폭 잔털 제거(opening) — 가는 머리끝을 그 외곽선까지 얹으면 base 몸 위에
    #   검은 잔선처럼 남는다(9-04 실측). 굵은 머리 뭉치만 남긴다.
    core = _dilate(_erode(mask), 1) & mask
    core |= seed & like                                  # 실루엣 밖 머리색 픽셀은 얇아도 지킨다
    core = _attached(core, mask[ny - 1], ny - 1)         # 머리 뭉치와 이어진 것만(뜬 점 제거)
    mask = core | (_dilate(core) & op & ~bright)         # 머리 테두리 외곽선 1px 동반
    mask[:ny] = False
    return mask


def merge_cell(b, a, ai_sh=None, base_sh=None):
    """머리 크기 맞춤은 목-어깨 경계 기준, 자르기는 base 목선 기준.
    ★자르기를 어깨선까지 내리면 AI 가 그린 제 옷깃까지 따라와 굵은 검은 띠가 된다.
      base 목선에서 자르면 목 아래 그림자는 base 것이 쓰여 원본과 똑같이 보인다(9-04 비교 확정)."""
    cut = neck_y(b)
    a = fit_head(a, ai_sh, base_sh)                      # AI 목-어깨 경계 → base 의 그것에 맞춤
    out = b.copy()
    out[:cut] = a[:cut]                                  # 이음선 위 = AI 얼굴+머리
    hm = hair_mask_below(a, b, cut)                      # 이음선 아래로 내려온 머리카락
    out[hm] = a[hm]
    return out, cut, int(hm.sum())


def merge(base_path, ai_path, out_path):
    base = np.array(Image.open(base_path).convert('RGBA'))
    ai = np.array(Image.open(ai_path).convert('RGBA'))
    if base.shape != ai.shape:
        raise SystemExit('시트 규격이 다르다: %s vs %s' % (base.shape, ai.shape))
    # 얼굴이 보이는 칸들에서 AI 목 위치를 모아 중앙값을 쓴다 — 뒤통수 칸은 목이 안 보여
    # 혼자 탐지가 안 되므로, 시트 전체가 같은 비율이라는 점을 이용해 같은 값을 적용한다.
    fa, fb = [], []
    for r in range(ROWS):
        for c in range(COLS):
            sy, sx = r * CH, c * CW
            bc, ac = base[sy:sy + CH, sx:sx + CW], ai[sy:sy + CH, sx:sx + CW]
            nb = neck_y(bc)
            ya, yb = shoulder_y(ac, nb), shoulder_y(bc, nb)
            if ya: fa.append(ya)
            if yb: fb.append(yb)
    ai_sh = int(np.median(fa)) if fa else None
    base_sh = int(np.median(fb)) if fb else None
    print('  목-어깨 경계  AI y=%s (%d칸) · base y=%s (%d칸)' % (ai_sh, len(fa), base_sh, len(fb)))

    out = base.copy()
    for r in range(ROWS):
        for c in range(COLS):
            sy, sx = r * CH, c * CW
            cell, cut, hn = merge_cell(base[sy:sy + CH, sx:sx + CW],
                                       ai[sy:sy + CH, sx:sx + CW], ai_sh, base_sh)
            out[sy:sy + CH, sx:sx + CW] = cell
            if c == 1:
                print('  행%d 이음선 y=%d · 아래 머리 %d px' % (r, cut, hn))
    Image.fromarray(out, 'RGBA').save(out_path)
    print('합성 →', out_path)
    return out_path


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True, help='base 시트 (char/walk.png)')
    ap.add_argument('--ai', required=True, help='AI 생성 규격 시트 (423x896)')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    merge(a.base, a.ai, a.out)
