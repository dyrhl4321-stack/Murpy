# -*- coding: utf-8 -*-
"""AI 가 그려준 '캐릭터가 옷을 입은 전신 시트'를 우리 격자에 정합시킨다.

AI 시트는 매번 크기가 다르다(1408x2986 등). 그대로 두면 base 와 겹치지 않아
diff 추출이 통째로 어긋난다. → 프레임마다 **머리**를 기준으로 base 에 맞춘다.

★기준이 왜 머리인가: 발바닥·전체 바운딩박스로 맞추면 **드레스처럼 밑단이 발보다 내려오는
  옷에서 통째로 어긋난다**(실측 확인). 머리는 어떤 옷에도 가려지지 않는 유일한 부위다.
  머리 최대폭으로 스케일, 머리 꼭대기 y 와 머리 가로중심으로 위치를 잡는다.

★확대·축소는 NEAREST 만 쓴다(에셋 하드룰). LANCZOS 로 줄이면 반투명 픽셀이
  1.1% -> 36.6% 로 폭증한다(asset-studio/README 실측).
★배경은 형광 마젠타/그린 단색이다 — AI 는 투명 배경을 못 그린다(대표 강명령).

사용:
  python tools/fit_sheet.py --src "<AI시트>" --base char/walk_female.png --out char/work/top_f_bratop_worn.png
"""
import argparse, os, sys
import numpy as np
from PIL import Image

CW, CH, COLS, ROWS = 141, 224, 3, 4


def dechroma(a):
    """형광 마젠타/그린 배경을 알파 0 으로. 가장자리 섞인 픽셀까지 잡는다."""
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    mag = (r > g + 40) & (b > g + 40)
    grn = (g > r + 40) & (g > b + 40)
    out = a.copy()
    out[..., 3] = np.where(mag | grn, 0, out[..., 3])
    return out


def heads(a, head_px):
    """셀마다 (머리꼭대기 y, 머리 가로중심, 머리 최대폭, 셀 원점). head_px = 머리로 볼 세로 범위."""
    H, W = a.shape[:2]
    cw, ch = W / COLS, H / ROWS
    op = a[..., 3] > 40
    out = []
    for r in range(ROWS):
        for c in range(COLS):
            y0, y1 = int(r * ch), int((r + 1) * ch)
            x0, x1 = int(c * cw), int((c + 1) * cw)
            sub = op[y0:y1, x0:x1]
            ys, xs = np.where(sub)
            if not len(ys):
                out.append(None); continue
            top = ys.min()
            band = sub[top:top + head_px]          # 머리 구간만
            w = band.sum(axis=1)
            k = int(np.argmax(w))                  # 가장 넓은 줄 = 머리 최대폭
            row = np.where(band[k])[0]
            out.append({"top": y0 + top, "cx": x0 + (row.min() + row.max()) / 2.0,
                        "w": int(w[k]), "ox": x0, "oy": y0})
    return out


def fit(src_path, base_path, out_path, log=print):
    src = np.array(Image.open(src_path).convert("RGBA"))
    src = dechroma(src)
    base = np.array(Image.open(base_path).convert("RGBA"))
    if base.shape[:2] != (CH * ROWS, CW * COLS):
        sys.exit("base 규격이 아니다: %s" % (base.shape,))
    # 머리 구간: base 는 106px(빡빡이 머리 높이 실측). 원본은 셀 높이 비율로 환산한다.
    k0 = (src.shape[0] / ROWS) / float(CH)
    sb, bb = heads(src, int(106 * k0)), heads(base, 106)
    out = Image.new("RGBA", (CW * COLS, CH * ROWS), (0, 0, 0, 0))
    simg = Image.fromarray(src, "RGBA")
    for i in range(COLS * ROWS):
        r, c = divmod(i, COLS)
        sh_, bh = sb[i], bb[i]
        if not sh_ or not bh:
            log("  r%dc%d 비었음 — 건너뜀" % (r, c)); continue
        k = bh["w"] / float(sh_["w"])              # 머리 최대폭 비율 = 배율
        cell = simg.crop((sh_["ox"], sh_["oy"],
                          sh_["ox"] + int(src.shape[1] / COLS), sh_["oy"] + int(src.shape[0] / ROWS)))
        nw, nh = max(1, round(cell.width * k)), max(1, round(cell.height * k))
        cell = cell.resize((nw, nh), Image.NEAREST)
        # 셀 안에서의 머리 꼭대기·중심이 base 와 같아지도록 놓는다
        dst_x = round(bh["cx"] - (sh_["cx"] - sh_["ox"]) * k)
        dst_y = round(bh["top"] - (sh_["top"] - sh_["oy"]) * k)
        out.alpha_composite(cell, (dst_x, dst_y))
        log("  r%dc%d 머리폭 %d->%d (x%.3f)  위치 %d,%d" % (r, c, sh_["w"], bh["w"], k, dst_x, dst_y))
    a = np.array(out)
    a[..., 3] = np.where(a[..., 3] >= 128, 255, 0)      # 알파 128 이진화 (하드룰)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    Image.fromarray(a, "RGBA").save(out_path)
    log("-> %s" % out_path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    fit(a.src, a.base, a.out)
