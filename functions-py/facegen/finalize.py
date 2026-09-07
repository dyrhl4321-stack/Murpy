# -*- coding: utf-8 -*-
"""내보내기 직전 마지막 정리 (2026-09-08, 박기웅 시트 머리 외곽 마젠타/보라 후광 — 반대 창 실측: 반투명 11,858px + 보라끼 어두운 픽셀 8,528px).

clean_fringe 는 규격화 직후 **밝은** 마젠타만 잡는다. 이식(graft) 뒤 시트에는
  ① base 몸통의 원래 반투명 픽셀(저장소 규칙은 알파 128 이진화)
  ② 외곽선에 섞인 **어두운 보라끼**(r>g+10, b>g+10, 합<330) — 밝기 기준(mx>100)에 안 걸린다
가 남는다. 여기서 둘을 마지막으로 정리한다. 헤어 레이어에도 같은 처리.
★얼굴 시트는 머리·살·베이지 속옷·남보라 외곽선뿐이라 보라끼 판정이 옷을 뜯을 일이 없다(옷 시트에는 쓰지 말 것).
"""
import numpy as np
from PIL import Image

def _edge_band(op, width=2):
    band = np.zeros_like(op); cur = op.copy()
    for _ in range(width):
        sh = np.zeros_like(cur)
        sh[1:, :] |= ~cur[:-1, :]; sh[:-1, :] |= ~cur[1:, :]
        sh[:, 1:] |= ~cur[:, :-1]; sh[:, :-1] |= ~cur[:, 1:]
        e = cur & sh; band |= e; cur = cur & ~e
    return band

def demagenta(path, out=None):
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
    Image.fromarray(a.astype(np.uint8)).save(out or path)
    return {'semi': n_semi, 'darkPurple': n_dark, 'edgeMagenta': n_edge}
