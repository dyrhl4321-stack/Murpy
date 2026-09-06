# -*- coding: utf-8 -*-
"""헤어 레이어 자동 추출 — 머리색을 미리 모르고도 뽑는다 (서버용, 2026-09-06).

tools/face_hair_layer.py 는 PRESET('blonde') 색 규칙을 사람이 골라야 했다. 서버는 아무 머리색이나 와야 하므로
**정수리 띠(정면 칸 y 6~34, x 40~100)에서 색을 샘플링**해 그 색과 가까운 픽셀을 머리로 본다.
정수리가 거의 어두우면(흑발) 어두운 픽셀의 **덩어리**만 잡는다(외곽선은 가늘어 열림 연산에서 사라진다).
★어느 쪽이든 **정수리와 이어진 덩어리만** 남긴다 — 눈썹·눈·팔 외곽선 같은 딴 조각이 딸려오던 것(재진 실측)을 막는다.
긴 머리는 정수리에서 등까지 이어져 있으니 같이 남는다.
"""
import numpy as np
from PIL import Image
from scipy.ndimage import label, binary_dilation, binary_erosion

CW, CH = 141, 224

def _skin(r, g, b):
    return (r > 150) & (r > g + 20) & (g > b) & (g - b < 45)

def extract_auto(sheet_path, out_path, min_px=30):
    """sheet_path 의 머리 픽셀만 out_path 로. 돌려주는 값 = (kind, 픽셀수). 머리를 못 찾으면 (None, 0) 이고 파일도 안 쓴다."""
    S = Image.open(sheet_path).convert('RGBA'); a = np.array(S).astype(int)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]; mx = np.maximum(np.maximum(r, g), b)
    skin = _skin(r, g, b); dark = (al > 128) & (mx < 90)
    crown_win = np.zeros(al.shape, bool); crown_win[6:34, 40:101] = True      # 정면 정지 칸 정수리
    crown = a[6:34, 40:101]; ca = crown[..., 3] > 128
    cs = _skin(crown[..., 0], crown[..., 1], crown[..., 2]); cd = np.maximum(np.maximum(crown[..., 0], crown[..., 1]), crown[..., 2]) < 90
    pal = crown[ca & ~cs & ~cd][:, :3]
    if len(pal) >= 20 and len(pal) > int((ca & cd).sum()):
        q = (pal // 24) * 24 + 12
        vals, cnt = np.unique(q, axis=0, return_counts=True); top = vals[np.argsort(-cnt)[:3]]
        m = np.zeros(al.shape, bool)
        for c in top:
            d = np.sqrt(((a[..., :3] - c) ** 2).sum(-1)); m |= (al > 128) & (d < 55)
        m &= ~skin; kind = 'color'
    else:
        m = binary_dilation(binary_erosion(dark, iterations=2), iterations=2); kind = 'dark'
    lab, n = label(m, structure=np.ones((3, 3)))
    keep = np.zeros(al.shape, bool)
    if n:
        sz = np.bincount(lab.ravel())
        if kind == 'dark':
            # ★흑발은 어두운 픽셀 = 눈썹·눈·외곽선과 색으로 못 가르니 **정수리와 이어진 덩어리만** (칸마다)
            for rr in range(4):
                for cc in range(3):
                    win = np.zeros(al.shape, bool); win[rr * CH + 6: rr * CH + 34, cc * CW + 40: cc * CW + 101] = True
                    ids = np.unique(lab[win & m]); ids = ids[ids > 0]
                    for i in ids:
                        if sz[i] >= min_px: keep |= (lab == i)
        else:
            # 색으로 가른 머리는 몸 외곽선이 안 섞인다 — 크기만 거른다. 정수리 연결을 요구하면 얼굴 외곽선에
            # 막힌 **옆머리(어깨로 내려오는 갈래)** 가 빠진다(9-06 로컬 하네스 실측) — 그게 상의 위에 그려야 할 핵심이다.
            big = sz >= min_px; big[0] = False; keep = big[lab]
    keep |= dark & binary_dilation(keep, iterations=1)          # 머리 테두리 1px 동반
    n_px = int(keep.sum())
    if n_px < 500: return None, 0
    out = np.zeros_like(a); out[keep] = a[keep]
    Image.fromarray(out.astype('uint8'), 'RGBA').save(out_path)
    return kind, n_px
