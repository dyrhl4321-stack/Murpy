# -*- coding: utf-8 -*-
"""아이템 색을 다른 아이템에 맞춘다 (세트로 보이게).

■ 왜 단순 '색 곱하기'가 아닌가
옷은 명암 단계가 여러 개다. 전체에 같은 계수를 곱하면 어두운 곳이 뭉개지거나
밝은 곳이 날아간다. 그래서 **밝기 분포(백분위)를 기준으로 대응**시킨다.
  대상의 40퍼센타일 밝기 -> 기준의 40퍼센타일 밝기
이러면 명암 단계 수와 순서가 그대로 유지된 채 톤만 옮겨간다.

■ 채도도 맞춘다
회색이라도 따뜻한 회색(R>G>B)과 차가운 회색은 나란히 두면 티가 난다.
기준 옷의 평균 (R-G), (G-B) 비율로 맞춘다.

■ 외곽선은 안 건드린다
가장 어두운 구간은 옷 색이 아니라 도트 외곽선이다. 여기를 옮기면 테두리가 흐려진다.

    python char/match_tone.py <바꿀아이템> <기준아이템> [--apply]
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUTLINE_LUM = 60      # 이보다 어두우면 외곽선으로 보고 건드리지 않는다


def load(p):
    return np.asarray(Image.open(p).convert("RGBA")).astype(int)


def stats(a):
    m = a[:, :, 3] >= 128
    px = a[m][:, :3]
    lum = px.mean(axis=1)
    body = lum >= OUTLINE_LUM
    return m, px, lum, body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("ref")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    tp, rp = Path(args.target), Path(args.ref)
    ta, ra = load(tp), load(rp)
    tm, tpx, tlum, tbody = stats(ta)
    rm, rpx, rlum, rbody = stats(ra)

    print(f"바꿀 것 {tp.name}   옷 픽셀 {int(tbody.sum())}  밝기 {tlum[tbody].min():.0f}~{tlum[tbody].max():.0f} 중앙 {np.median(tlum[tbody]):.0f}")
    print(f"기준   {rp.name}   옷 픽셀 {int(rbody.sum())}  밝기 {rlum[rbody].min():.0f}~{rlum[rbody].max():.0f} 중앙 {np.median(rlum[rbody]):.0f}")

    # 1) 밝기 백분위 대응표
    qs = np.linspace(0, 100, 256)
    src_q = np.percentile(tlum[tbody], qs)
    dst_q = np.percentile(rlum[rbody], qs)

    # 2) 기준 옷의 따뜻함(채도 방향)
    rg = float((rpx[rbody][:, 0] - rpx[rbody][:, 1]).mean())
    gb = float((rpx[rbody][:, 1] - rpx[rbody][:, 2]).mean())
    trg = float((tpx[tbody][:, 0] - tpx[tbody][:, 1]).mean())
    tgb = float((tpx[tbody][:, 1] - tpx[tbody][:, 2]).mean())
    print(f"채도 방향  바꿀것 R-G {trg:.1f} G-B {tgb:.1f}   기준 R-G {rg:.1f} G-B {gb:.1f}")

    out = ta.copy()
    ys, xs = np.nonzero(tm)
    lum_all = ta[tm][:, :3].mean(axis=1)
    keep = lum_all < OUTLINE_LUM                    # 외곽선은 그대로
    newl = np.interp(lum_all, src_q, dst_q)
    # 밝기를 새 값으로 옮기고, 채도는 기준 옷 비율로 다시 세운다
    g = newl - (rg + gb) / 3.0 + gb / 3.0 * 0        # G 를 기준으로 R,B 를 배치
    g = newl - (rg - gb) / 3.0
    r = g + rg
    b = g - gb
    rgb = np.stack([r, g, b], axis=1)
    rgb = np.clip(np.rint(rgb), 0, 255)
    orig = ta[tm][:, :3]
    rgb[keep] = orig[keep]
    out[ys, xs, :3] = rgb

    nb = out[tm][:, :3]
    nl = nb.mean(axis=1)
    body2 = nl >= OUTLINE_LUM
    print(f"결과   밝기 {nl[body2].min():.0f}~{nl[body2].max():.0f} 중앙 {np.median(nl[body2]):.0f}")

    if not args.apply:
        print("\n--apply 를 붙이면 저장한다")
        return 0
    bak = tp.with_name(tp.stem + "_톤변경전" + tp.suffix)
    if not bak.exists():
        shutil.copy2(tp, bak)
    Image.fromarray(out.astype(np.uint8), "RGBA").save(tp)
    print(f"-> {tp}  (백업 {bak.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
