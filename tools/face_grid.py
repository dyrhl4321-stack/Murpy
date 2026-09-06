# -*- coding: utf-8 -*-
"""생성 원본(3x4)을 칸 단위로 규격화한다 — 12칸을 각각 base 캐릭터 위치에 맞춰 앉힌다.

    python tools/face_grid.py --raw <생성원본.png> --base char/walk.png --out char/faces/kim_ai.png

★왜 칸 단위인가 (9-04 실측): 시트 전체를 한 번에 423x896 으로 늘이면, AI 가 그린 칸 간격이
  base 와 달라(실측 154.5 vs 142) 열마다 -13 / -1 / +12 px 씩 어긋난다. 칸을 따로 앉히면
  이 어긋남이 통째로 사라진다. 배율은 몸 폭으로 재면 높이 구간과 무관하게 일정하다(실측 0.3235).
"""
import os, sys, argparse
import numpy as np
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')

CW, CH = 141, 224
COLS, ROWS = 3, 4
SW, SH = CW * COLS, CH * ROWS


def _blobs(v, thr=2, minw=20):
    on = v > thr
    out, s = [], None
    for i, x in enumerate(on):
        if x and s is None:
            s = i
        elif not x and s is not None:
            out.append((s, i - 1)); s = None
    if s is not None:
        out.append((s, len(on) - 1))
    return [b for b in out if b[1] - b[0] > minw]


def foreground(raw_path, tol=60):
    """단색 배경(마젠타) 위의 캐릭터 마스크와 RGBA 이미지."""
    img = Image.open(raw_path).convert('RGB')
    a = np.array(img).astype(int)
    bg = a[0, 0]
    fg = ((a - bg) ** 2).sum(-1) > tol * tol
    rgba = np.dstack([np.array(img), np.where(fg, 255, 0).astype(np.uint8)])
    return rgba, fg, bg


def anchors(mask):
    """캐릭터의 발 기준점 — 맨 아래 행(발바닥)과 하위 10% 구간의 좌우 중심.
    머리·머리카락에 안 휘둘리는 유일한 기준이라 정렬 앵커로 쓴다."""
    ys, xs = np.where(mask)
    if not len(ys):
        return None
    bot, top = ys.max(), ys.min()
    band = mask[max(top, bot - max(2, int((bot - top) * 0.10))):bot + 1]
    bxs = np.where(band.any(0))[0]
    return float(bot), (float(bxs.min()) + float(bxs.max())) / 2.0


def clean_fringe(arr, bgcol, passes=2):
    """★배경색 잔상 수술 (2026-09-06, 패수현 실측). LANCZOS 축소가 배경색을 테두리에 섞어
    ①반투명 가장자리 25,199px 평균색 (116,13,123)=마젠타 ②외곽선 안쪽 2번째 픽셀에 밝은 마젠타 640px
    가 남아 폰에서 '테두리에 마젠타가 낀다'로 보였다(대표 9-06). 규격화 결과에 항상 돌린다.
      1) 알파 128 이진화 (저장소 규칙)
      2) 배경 채널 배열을 따르는 밝은 픽셀(마젠타면 R·B≫G, 초록이면 G≫R·B) + 반투명이었던 픽셀 →
         인접 8칸 중 배경 기운 없는 가장 어두운 픽셀(=외곽선) 색으로. 2회 돌려 2px 깊이까지.
    정당한 내용이 배경색 계열인 시트에는 쓰면 안 된다 — 얼굴 시트는 머리·살·속옷·남보라 외곽선뿐이라 안전."""
    a = arr.astype(int)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    semi = (al > 0) & (al < 255)
    a[al < 128] = 0; a[al >= 128, 3] = 255
    bc = np.array(bgcol[:3], int); dom = bc > bc.mean() + 40      # 배경의 지배 채널(마젠타: R,B)
    chans = a[..., :3]
    mx = chans.max(-1)
    # ★배경이 무채색(검정·흰·회색)이면 채널 배열로 배경 기운을 가려낼 수 없다 — 그때 '밝은 픽셀 전부'를
    #   배경 기운으로 잡아 캐릭터를 통째로 검게 칠한 사고(9-06 백테스트 bt_1·bt_2). 그 경우 반투명만 다룬다.
    achromatic = (bc.max() - bc.min()) < 40 or dom.sum() == 0 or dom.sum() == 3
    tinted = np.zeros(al.shape, bool) if achromatic else ((a[..., 3] == 255) & (mx > 100))
    if not achromatic:
        for i in range(3):
            for j in range(3):
                if dom[i] and not dom[j]:
                    tinted &= chans[..., i] > chans[..., j] + 40
    suspect = (a[..., 3] == 255) & (tinted | semi)
    n_tint = int(tinted.sum())
    H, W = al.shape; fixed = 0
    for _ in range(passes):
        good = (a[..., 3] == 255) & ~tinted & ~suspect
        ys, xs = np.where(suspect)
        if not len(ys): break
        nxt = np.zeros_like(suspect)
        for y, x in zip(ys, xs):
            best = None
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and good[yy, xx]:
                        c = a[yy, xx, :3]; ssum = int(c.sum())
                        if best is None or ssum < best[0]: best = (ssum, c.copy())
            if best is not None:
                a[y, x, :3] = best[1]; fixed += 1
            else:
                nxt[y, x] = True                      # 이웃이 전부 의심 픽셀 — 다음 회차에
        suspect = nxt
        tinted = np.zeros_like(tinted)
    if suspect.any():                                  # 끝까지 남은 것 = 남보라 외곽선 기본색
        a[suspect, :3] = (34, 11, 38); fixed += int(suspect.sum())
    print('  배경 잔상 수술: 반투명 %d + 배경기운 %d → 재색칠 %d (배경 %s)' % (int(semi.sum()), n_tint, fixed, tuple(int(v) for v in bc)))
    return a.astype('uint8')


def bg_color(raw_path):
    """원본 네 모서리 평균 = 배경색 (regrid 와 같은 판정)."""
    im = Image.open(raw_path).convert('RGBA'); px = im.load(); W, H = im.size
    cs = [px[0, 0], px[W - 1, 0], px[0, H - 1], px[W - 1, H - 1]]
    return tuple(sum(c[i] for c in cs) // 4 for i in range(3))


def regrid_cells(raw_path, base_path, out_path):
    rgba, fg, bg = foreground(raw_path)
    cb, rb = _blobs(fg.sum(0)), _blobs(fg.sum(1))
    if len(cb) != COLS or len(rb) != ROWS:
        raise SystemExit('칸 탐지 실패: 열 %d개 행 %d개 (3x4 여야 한다)' % (len(cb), len(rb)))
    base = np.array(Image.open(base_path).convert('RGBA'))

    # 배율 = base 몸 폭 / AI 몸 폭. 캐릭터 높이의 여러 지점에서 재 중앙값을 쓴다
    # (전체 높이로 재면 머리카락 부피에 흔들린다).
    scales = []
    for r, (y0, y1) in enumerate(rb):
        for c, (x0, x1) in enumerate(cb):
            sub = fg[y0:y1 + 1, x0:x1 + 1]
            bo = base[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW, 3] > 128
            ays, _ = np.where(sub); bys, _ = np.where(bo)
            if not len(ays) or not len(bys):
                continue
            at, ah = ays.min(), ays.max() - ays.min() + 1
            bt, bh = bys.min(), bys.max() - bys.min() + 1
            for f in (0.65, 0.75, 0.85, 0.94):
                def w(m, y, d):
                    seg = m[y:y + max(1, d)]
                    xs = np.where(seg.any(0))[0]
                    return xs.max() - xs.min() + 1 if len(xs) else 0
                aw = w(sub, int(at + ah * f), int(ah * 0.04))
                bw = w(bo, int(bt + bh * f), max(1, int(bh * 0.04)))
                if aw > 4 and bw > 4:
                    scales.append(bw / float(aw))
    s = float(np.median(scales))
    print('  칸 %dx%d · 배율 %.4f (표본 %d)' % (len(cb), len(rb), s, len(scales)))

    out = np.zeros((SH, SW, 4), np.uint8)
    for r, (y0, y1) in enumerate(rb):
        for c, (x0, x1) in enumerate(cb):
            crop = rgba[y0:y1 + 1, x0:x1 + 1]
            m = fg[y0:y1 + 1, x0:x1 + 1]
            nw, nh = max(1, int(round(crop.shape[1] * s))), max(1, int(round(crop.shape[0] * s)))
            small = np.array(Image.fromarray(crop, 'RGBA').resize((nw, nh), Image.LANCZOS))
            sm = small[..., 3] > 128
            bo = base[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW, 3] > 128
            aa, ba = anchors(sm), anchors(bo)
            if aa is None or ba is None:
                continue
            dy, dx = int(round(ba[0] - aa[0])), int(round(ba[1] - aa[1]))
            for yy in range(nh):                       # base 셀 안으로 발 기준 정렬해 붙인다
                ty = yy + dy
                if 0 <= ty < CH:
                    xs0, xs1 = max(0, -dx), min(nw, CW - dx)
                    if xs1 > xs0:
                        dst = out[r * CH + ty, c * CW + xs0 + dx: c * CW + xs1 + dx]
                        src = small[yy, xs0:xs1]
                        keep = src[..., 3] > 0
                        dst[keep] = src[keep]
    out = clean_fringe(out, bg_color(raw_path))      # ★배경색 잔상 수술 — 항상
    Image.fromarray(out, 'RGBA').save(out_path)
    print('  칸단위 규격화 →', out_path)
    return out_path


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', required=True)
    ap.add_argument('--base', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    regrid_cells(a.raw, a.base, a.out)
