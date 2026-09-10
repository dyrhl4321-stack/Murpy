# -*- coding: utf-8 -*-
"""내보내기 직전 마지막 정리 (2026-09-08 → 2026-09-10 확장).

9-08 판(박기웅 후광): 규격화 직후 clean_fringe 가 **밝은** 마젠타만 잡아서, 이식 뒤 시트에
  ① base 몸통의 원래 반투명 픽셀  ② 외곽선에 섞인 **어두운 보라끼**
가 남았다. 여기서 둘을 마지막으로 정리한다.

★2026-09-10 (대표: "얼굴에 잡다한 실선, 레제 머리 상단에 이물감"). 22명 전수 실측으로 원인 셋을 갈랐다:
  ① **머리카락 안쪽 마젠타 잔재** — 9-08 판은 가장자리 2px 띠만 청소해서 **안쪽은 손도 안 댔다**.
     레제 1,926px(시트)+1,420px(헤어), 한영 46px 이 그대로 남아 어두운 머리에 보라 점으로 박혀 있었다.
     ★정당한 분홍(공주 리본 RGB 240,128,160)과 갈라내는 기준 = **R≈B**.
       마젠타 배경(#FF00FF)이 무엇과 섞이든 R 과 B 는 같이 움직여 |R-B| 가 작다(레제 112,80,128).
       분홍·살구·빨강은 R 이 B 보다 훨씬 크다(공주 |R-B|=80). 실측: 이 규칙이 공주 리본 9,088px 을
       하나도 안 건드리고 레제·한영 잔재만 3,392px 잡았다. 손제작 자산 오작동은 2~18px(0.01%).
  ② **떠 있는 조각** — 머리 위에 붙어 있지도 않은 1~2px 조각이 가로선처럼 보였다(레제 상단).
  ③ 회색 잔선 — 실측 결과 대부분(1.5~2.9%)은 손제작 헤어 아이템(2.0~2.4%)과 같은 수준이라 **건드리지 않는다**.
     기준을 크게 넘는 것만(공주 21.5%·보우야 9.2%·면수 7.0%) despeckle 로 눌러 준다.

★얼굴 시트 전용이다. 옷 시트에 쓰면 안 된다 — 보라 후드집업(top_f_hoodzip)은 이 규칙에 3.2%가 걸린다.
"""
import numpy as np
from PIL import Image

try:                                  # despeckle 은 scipy 가 있을 때만(서버엔 있다). 없으면 조용히 건너뛴다.
    from scipy import ndimage
except Exception:
    ndimage = None


def _edge_band(op, width=2):
    band = np.zeros_like(op); cur = op.copy()
    for _ in range(width):
        sh = np.zeros_like(cur)
        sh[1:, :] |= ~cur[:-1, :]; sh[:-1, :] |= ~cur[1:, :]
        sh[:, 1:] |= ~cur[:, :-1]; sh[:, :-1] |= ~cur[:, 1:]
        e = cur & sh; band |= e; cur = cur & ~e
    return band


def _fill_from_neighbors(a, bad, good, rounds=6):
    """bad 픽셀을 이웃 good 픽셀의 중앙값으로 바꾼다(픽셀아트라 블렌드 금지). 안쪽부터 못 채우면 다음 회차."""
    H, W = bad.shape; fixed = 0
    for _ in range(rounds):
        ys, xs = np.where(bad)
        if not len(ys): break
        moved = False
        for y, x in zip(ys, xs):
            y0, y1, x0, x1 = max(0, y - 1), min(H, y + 2), max(0, x - 1), min(W, x + 2)
            gm = good[y0:y1, x0:x1]
            if gm.any():
                a[y, x, :3] = np.median(a[y0:y1, x0:x1][gm][:, :3], axis=0).astype(int)
                bad[y, x] = False; good[y, x] = True; fixed += 1; moved = True
        if not moved: break
    if bad.any():                     # 이웃이 전부 잔재 — 마지막엔 무채색으로 눌러 둔다(보라로 남기지 않는다)
        lum = ((a[..., 0] * 299 + a[..., 1] * 587 + a[..., 2] * 114) // 1000)
        for ch in range(3):
            a[..., ch][bad] = lum[bad]
        fixed += int(bad.sum())
    return fixed


def _chroma_remnant(a):
    """마젠타 배경이 섞여 들어간 픽셀. |R-B| 가 작고 둘 다 G 보다 높다 = 배경이 남긴 보라끼.
    정당한 분홍/빨강(R≫B)·하늘색(B≫R)은 걸리지 않는다."""
    op = a[..., 3] == 255
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    return op & (np.abs(R - B) <= 24) & (R - G >= 24) & (B - G >= 24)


def _floaters(op, max_area=6):
    """본체에서 떨어져 나온 작은 조각(레제 머리 위 가로선). 가장 큰 덩어리 외에 area 이하인 것만."""
    if ndimage is None or not op.any(): return np.zeros_like(op)
    lab, n = ndimage.label(op)
    if n <= 1: return np.zeros_like(op)
    sz = ndimage.sum(op, lab, range(1, n + 1))
    keep = int(np.argmax(sz)) + 1
    out = np.zeros_like(op)
    for i in range(1, n + 1):
        if i != keep and sz[i - 1] <= max_area: out |= (lab == i)
    return out


def _trim_ledge(a, cell_h=224, cell_w=141, rows_from_top=8, margin=6):
    """★9-10 '머리 위에 얹힌 평평한 가로 막대'(대표: 레제 머리 상단 이물감) 제거.
    실루엣 꼭대기 근처에서 **윗행이 아랫행보다 넓으면** 처마다 — 머리는 위로 갈수록 좁아지는 게 정상이라
    이 모양은 규격화 축소가 만든 것이다. 실측: 손제작 자산 0칸 / 생성 22명 중 5명 26칸(레제·ZY(2)·한영·보우야·오채니손민수).
    윗행에서 아랫행 x 범위(±1) 밖으로 튀어나온 픽셀만 지운다 — 머리 모양 자체는 안 건드린다."""
    H, W = a.shape[:2]; removed = 0
    for r in range(H // cell_h):
        for c in range(W // cell_w):
            ys, xs = slice(r * cell_h, (r + 1) * cell_h), slice(c * cell_w, (c + 1) * cell_w)
            cell = a[ys, xs]
            for _ in range(3):
                op = cell[..., 3] == 255
                w = op.sum(1); nz = np.where(w > 0)[0]
                if not len(nz): break
                top = nz[0]; hit = False
                for y in range(top, min(top + rows_from_top, cell_h - 2)):
                    if w[y] < 10 or w[y] <= w[y + 1] + margin: continue
                    below = np.where(op[y + 1])[0]
                    if not len(below): continue
                    lo, hi = below.min() - 1, below.max() + 1
                    over = op[y].copy(); over[max(0, lo):hi + 1] = False
                    if over.any():
                        cell[y][over] = 0; removed += int(over.sum()); hit = True
                if not hit: break
            a[ys, xs] = cell
    return removed


def despeckle(a, limit, region=None):
    """국소 중앙값에서 크게 튀는 **작은** 조각만 눌러 준다.
    ★limit 은 반드시 손제작 자산 실측치를 넘겨야 한다(9-10 22명 전수):
      · 시트의 **목선 위 머리 영역** — 손제작 base 5.0~5.3%, 생성분 22명 중 17명이 3.4~5.3% 로 정상.
        6% 를 넘는 5명(ZY(2) 10.5·보우야 9.7·면수 7.7·공주 7.0·한영 6.7)만 눌러 준다.
      · 헤어 레이어 — 손제작 헤어 아이템 2.0~2.4%, 3.5% 초과만.
    기준 이하인데도 돌리면 정상 질감을 뭉개서 오히려 납작해진다. 그래서 게이트가 핵심이다."""
    if ndimage is None: return 0
    op = a[..., 3] == 255
    if region is not None: op = op & region
    if not op.any(): return 0
    lum = ((a[..., 0] * 299 + a[..., 1] * 587 + a[..., 2] * 114) // 1000)
    med = ndimage.median_filter(lum, size=5)
    odd = op & (np.abs(lum - med) > 26)
    if 100.0 * odd.sum() / op.sum() <= limit: return 0
    lab, n = ndimage.label(odd)
    if n == 0: return 0
    sz = ndimage.sum(odd, lab, range(1, n + 1))
    small = np.isin(lab, np.where(sz <= 4)[0] + 1) & odd      # 4px 이하 조각만(굵은 하이라이트는 보존)
    H, W = op.shape
    ys, xs = np.where(small)
    for y, x in zip(ys, xs):
        y0, y1, x0, x1 = max(0, y - 2), min(H, y + 3), max(0, x - 2), min(W, x + 3)
        m = (a[y0:y1, x0:x1, 3] == 255) & ~small[y0:y1, x0:x1]
        if m.any(): a[y, x, :3] = np.median(a[y0:y1, x0:x1][m][:, :3], axis=0).astype(int)
    return int(small.sum())


def _head_region(shape, cell_h=224, neck=110):
    """칸마다 목선 위 = AI 가 그린 머리 영역. 그 아래는 base 몸통이라 손대지 않는다."""
    m = np.zeros(shape[:2], bool)
    for r in range(shape[0] // cell_h):
        m[r * cell_h: r * cell_h + neck] = True
    return m


def demagenta(path, out=None, deep=True, is_hair=False):
    a = np.array(Image.open(path).convert('RGBA')).astype(int)
    al = a[..., 3]
    n_semi = int(((al > 0) & (al < 255)).sum())
    a[al < 128] = 0; a[al >= 128, 3] = 255                                    # ① 알파 128 이진화
    r, g, b = a[..., 0], a[..., 1], a[..., 2]; op = a[..., 3] == 255
    # ② 어두운 보라끼 → 무채색(외곽선은 원래 남보라 #2b2430 계열이라 밝기만 남기면 자연스럽다)
    dark_purple = op & (r > g + 10) & (b > g + 10) & ((r + g + b) < 330)
    lum = ((r * 299 + g * 587 + b * 114) // 1000)
    a[dark_purple, 0] = lum[dark_purple]; a[dark_purple, 1] = lum[dark_purple]; a[dark_purple, 2] = np.minimum(255, lum[dark_purple] + 2)
    n_dark = int(dark_purple.sum())
    # ③ 가장자리 띠(2px)의 밝은 마젠타 → 이웃 3x3 중 정상 픽셀의 중앙값(픽셀아트라 블렌드 금지)
    H, W = op.shape; n_edge = 0
    for _ in range(4):
        r, g, b = a[..., 0], a[..., 1], a[..., 2]; op = a[..., 3] == 255
        mag = op & (r > g + 22) & (b > g + 22) & (r > 55) & (b > 45)
        bad = mag & _edge_band(op, 2)
        if not bad.any(): break
        good = op & ~mag
        ys, xs = np.where(bad)
        for y, x in zip(ys, xs):
            y0, y1, x0, x1 = max(0, y - 1), min(H, y + 2), max(0, x - 1), min(W, x + 2)
            gm = good[y0:y1, x0:x1]
            if gm.any():
                a[y, x, :3] = np.median(a[y0:y1, x0:x1][gm][:, :3], axis=0).astype(int); n_edge += 1
            else:
                a[y, x] = 0
    n_inner = n_float = n_spec = n_ledge = 0
    if deep:
        # ④ ★9-10 안쪽 마젠타 잔재 — 가장자리가 아니어도 지운다(레제 머리 속 보라 점). 정당한 분홍은 R≫B 라 안 걸린다.
        rem = _chroma_remnant(a)
        if rem.any():
            n_inner = _fill_from_neighbors(a, rem.copy(), (a[..., 3] == 255) & ~rem)
        # ⑤ 떠 있는 조각(머리 위 가로선) 제거
        op = a[..., 3] == 255
        fl = _floaters(op, 6)
        if fl.any(): a[fl] = 0; n_float = int(fl.sum())
        # ⑥ 머리 위 평평한 처마 제거
        n_ledge = _trim_ledge(a)
        # ⑥ 잔선이 손제작 기준을 크게 넘을 때만 눌러 준다(시트=머리 영역만 6%, 헤어 레이어=3.5%)
        if is_hair: n_spec = despeckle(a, 3.5)
        else:       n_spec = despeckle(a, 6.0, _head_region(a.shape))
    Image.fromarray(a.astype(np.uint8)).save(out or path)
    return {'semi': n_semi, 'darkPurple': n_dark, 'edgeMagenta': n_edge,
            'innerMagenta': n_inner, 'floaters': n_float, 'speckle': n_spec, 'ledge': n_ledge}
