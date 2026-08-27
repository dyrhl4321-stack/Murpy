# -*- coding: utf-8 -*-
"""추출한 옷 레이어에 **그 옷이 아닌 것**이 섞였는지 검사한다.

대표 2026-08-27: "앞으로 옷 추출할 때 그 레이어 제외하고는
                  얼굴이나 하의나 캐릭터 다른 곳 절대 추출하지 마라 제발"

내가 브라탑을 뽑을 때 상의 슬롯 영역이 y67~188 이라 **하의 허리까지 딸려 나왔고**,
대표가 12프레임을 손으로 다 지우느라 하루를 썼다. 다시는 그러면 안 된다.

검사 세 가지 — 하나라도 걸리면 **추출을 다시 하라는 뜻**이다.
 1. 살색 픽셀   : base 가 살이던 자리를 그대로 베껴 왔는가 (얼굴·팔·다리)
 2. 하의 침범   : 상의인데 base 속옷(하의) 자리에 픽셀이 있는가
 3. 프레임 흔들림: 같은 방향 세 프레임의 옷 위쪽 경계가 크게 다른가
                  (브라탑이 y100/77/114 로 튀어 "가슴골이 오르내린다"고 지적받았다)

사용:
  python tools/item-purity-check.py char/items/top_f_bratop.png --base char/walk_female.png --slot top
"""
import argparse, os, sys
import numpy as np
from PIL import Image

CW, CH, COLS, ROWS = 141, 224, 3, 4
# base 여캐/남캐가 입고 있는 속옷의 세로 구간(실측). 상의는 여기를 건드리면 안 된다.
UNDERWEAR_Y = (158, 196)


# 대표가 눈으로 보고 **이대로 간다**고 승인한 것. 흔들림 경고를 띄우지 않는다.
#   (경고가 계속 뜨면 다음 사람이 "고쳐야 하나" 하고 또 붙잡는다)
APPROVED_WOBBLE = {
    "top_f_dress.png": "2026-08-27 대표 승인 — 치마가 넓게 퍼지는 옷이라 프레임마다 경계가 다르다",
}


def is_skin(rgb):
    r, g, b = rgb[..., 0].astype(int), rgb[..., 1].astype(int), rgb[..., 2].astype(int)
    mx = rgb[..., :3].max(2).astype(int); mn = rgb[..., :3].min(2).astype(int)
    L = (mx + mn) / 2.0 / 255.0
    return (r > g + 12) & (g >= b) & (L > 0.28) & (r > 95)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("item")
    ap.add_argument("--base", required=True)
    ap.add_argument("--slot", default="top", choices=["top", "bottom", "shoes", "hair", "hat", "acc"])
    ap.add_argument("--wobble", type=int, default=18, help="프레임 간 허용 흔들림(px)")
    a = ap.parse_args()

    it = np.array(Image.open(a.item).convert("RGBA")).astype(int)
    ba = np.array(Image.open(a.base).convert("RGBA")).astype(int)
    if it.shape != ba.shape:
        sys.exit("규격이 다르다: %s vs %s" % (it.shape, ba.shape))
    on = it[..., 3] > 128
    bad = []

    # 1) 살색을 베껴 왔는가 — 옷 픽셀이 base 와 색까지 거의 같으면 그건 몸이다
    same = np.abs(it[..., :3] - ba[..., :3]).sum(2) < 24
    skinned = on & same & is_skin(ba) & (ba[..., 3] > 128)
    if skinned.sum() > 40:
        bad.append("살색을 그대로 베껴 온 픽셀 %d개 (얼굴·팔·다리가 딸려왔다)" % skinned.sum())

    # 2) 상의인데 base 속옷을 **베껴 왔는가**
    #    ★"하의 구간에 픽셀이 있다"로 잡으면 안 된다 — 드레스처럼 발끝까지 오는 상의는
    #      거기 있는 게 정상이다(실제로 37,242개가 잡혀 오탐이었다).
    #      진짜 문제는 **base 속옷을 색까지 그대로 복사해 온 것**이다.
    if a.slot == "top":
        y0, y1 = UNDERWEAR_Y
        m = np.zeros(on.shape, bool)
        for r in range(ROWS):
            m[r * CH + y0: r * CH + y1, :] = True
        copied = on & m & same & (ba[..., 3] > 128)
        if copied.sum() > 200:
            bad.append("base 하의를 그대로 베껴 온 픽셀 %d개 (상의에 하의가 섞였다)" % copied.sum())

    # ※"살을 어둡게 덮었는가"로 검사해 봤다가 **뺐다**(2026-08-27).
    #   옷은 아웃라인이 있고 그 테두리가 살 위에 오는 것은 당연하다 —
    #   대표가 손본 브라탑(5,278px)·반스(5,115px)까지 전부 FAIL 이 났다.
    #   진짜 문제(드레스가 팔을 통째로 검게 덮은 것)와 정상 테두리를 픽셀 수로는 못 가른다.
    #   오탐을 내는 검사는 아무도 안 믿게 되므로 없느니만 못하다.

    # 3) 같은 방향 세 프레임의 옷 위쪽 경계가 튀는가 — **경고만** 한다.
    #    걸음 프레임은 자세가 달라 옷도 조금 움직인다(무릎을 들면 바지가 올라간다).
    #    실패로 처리하면 정상인 것까지 걸려 검사를 아무도 안 믿게 된다.
    warn = []
    for r in range(ROWS):
        tops = []
        for c in range(COLS):
            m = on[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
            ys = np.where(m.any(1))[0]
            if len(ys): tops.append(int(ys.min()))
        if len(tops) == COLS and (max(tops) - min(tops)) > a.wobble:
            warn.append("행%d 옷 위쪽 경계 %s (%dpx 차)" % (r, tops, max(tops) - min(tops)))

    name = os.path.basename(a.item)
    if bad:
        print("FAIL %s" % name)
        for b in bad: print("  x " + b)
        for w in warn: print("  ~ " + w)
        sys.exit(1)
    print("OK %s — 다른 부위를 베껴 온 것 없음" % name)
    if name in APPROVED_WOBBLE:
        if warn: print("  · 흔들림 경고 있음 — " + APPROVED_WOBBLE[name])
        return
    for w in warn:
        print("  ~ 살펴볼 것: " + w + "  ※걸음 자세 때문일 수 있다")


if __name__ == "__main__":
    main()
