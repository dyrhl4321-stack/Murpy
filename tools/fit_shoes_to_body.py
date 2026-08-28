# -*- coding: utf-8 -*-
"""남캐 신발 시트를 여캐 몸에 맞춘다 — 평행이동으로 안 될 때 쓴다.

대표 2026-08-27: "남캐 기반으로 여캐를 만든 거니까 발 사이즈랑 크기라던지 다 다를 거 아님.
                  남캐 반스는 맞는데 여캐 반스는 좀 이상하다."

맞다. 특히 **우향 걸음A** 에서 여캐 발이 남캐보다 11px 짧다
(남 x31~130 / 여 x30~119). 그래서 남캐 기준 신발이 오른쪽·아래로 삐져나온다.
char/adapt_item_to_body.py 는 평행이동만 해서(0~3px) 이 차이를 못 메운다.

방법: 프레임마다 **여캐 base 실루엣을 grow px 만큼 부풀린 범위 밖**을 잘라낸다.
신발은 발보다 조금 커야 자연스러우므로 grow 로 여유를 준다.
잘라내기만 하므로 없던 픽셀을 만들지 않는다 — 모양이 뒤틀릴 일이 없다.
"""
import argparse, os
import numpy as np
from PIL import Image

CW, CH, COLS, ROWS = 141, 224, 3, 4


def grow_mask(m, n):
    out = m.copy()
    for _ in range(n):
        g = out.copy()
        g[1:, :] |= out[:-1, :]; g[:-1, :] |= out[1:, :]
        g[:, 1:] |= out[:, :-1]; g[:, :-1] |= out[:, 1:]
        out = g
    return out


def foot_box(mask, band=34):
    """발 영역(실루엣 아래 band px)의 bbox — 좌우 끝과 바닥."""
    ys = np.where(mask.any(1))[0]
    if not len(ys): return None
    bot = int(ys.max())
    strip = mask[max(0, bot - band + 1):bot + 1]
    xs = np.where(strip.any(0))[0]
    if not len(xs): return None
    return int(xs.min()), int(xs.max()), bot


def run(item, base, out_path, grow=3, src_base=None, log=print):
    it = np.array(Image.open(item).convert("RGBA"))
    ba = np.array(Image.open(base).convert("RGBA"))
    bm = ba[..., 3] > 128
    sm = (np.array(Image.open(src_base).convert("RGBA"))[..., 3] > 128) if src_base else None
    cut = 0
    for r in range(ROWS):
        for c in range(COLS):
            ys, xs = slice(r * CH, (r + 1) * CH), slice(c * CW, (c + 1) * CW)
            cell = it[ys, xs]
            # ① 원래 base 와 목표 base 의 **발 bbox 중심** 차이만큼 옮긴다.
            #    ★기존 char/adapt_item_to_body.py 는 이동을 3px 로 묶어 둬서
            #      우향 걸음A(-6.5px 필요)를 못 메웠다 — 그게 "여캐 반스가 이상하다"의 원인이다.
            if sm is not None:
                a, b = foot_box(sm[ys, xs]), foot_box(bm[ys, xs])
                if a and b:
                    dx = int(round(((b[0] + b[1]) - (a[0] + a[1])) / 2.0))
                    dy = b[2] - a[2]
                    if dx or dy:
                        moved = np.zeros_like(cell)
                        h, w = cell.shape[:2]
                        y0s, y0d = (0, dy) if dy >= 0 else (-dy, 0)
                        x0s, x0d = (0, dx) if dx >= 0 else (-dx, 0)
                        hh = h - abs(dy); ww = w - abs(dx)
                        moved[y0d:y0d + hh, x0d:x0d + ww] = cell[y0s:y0s + hh, x0s:x0s + ww]
                        cell[:] = moved
                        log("  r%dc%d  이동 (%+d,%+d)" % (r, c, dx, dy))
            # ② 그래도 목표 base 밖으로 나간 것은 잘라낸다(폭 자체가 다른 프레임용)
            allow = grow_mask(bm[ys, xs], grow)
            bad = (cell[..., 3] > 128) & ~allow
            cell[..., 3][bad] = 0
            if bad.sum():
                log("  r%dc%d  %d px 잘라냄" % (r, c, bad.sum()))
            cut += int(bad.sum())
    it[..., 3] = np.where(it[..., 3] >= 128, 255, 0)      # 알파 128 이진화 (하드룰)
    Image.fromarray(it, "RGBA").save(out_path)
    log("총 %d px 잘라냄 -> %s" % (cut, out_path))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--item", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--grow", type=int, default=3, help="base 실루엣에서 허용할 여유(px)")
    ap.add_argument("--src-base", dest="src_base", help="아이템이 원래 맞춰져 있던 base(있으면 이동까지 한다)")
    a = ap.parse_args()
    run(a.item, a.base, a.out, a.grow, a.src_base)
