# -*- coding: utf-8 -*-
"""대표가 준 아이템 썸네일 원본에서 배경을 빼고 카드용으로 다듬는다.

★썸네일은 **대표가 준 파일만** 쓴다(캐릭터 시트에서 자동으로 잘라 만들지 않는다).
  여기서 하는 일은 배경 제거 · 파편 제거 · 트림 · 축소뿐이다.

★파편을 먼저 지우고 트림한다. 떨어진 점 하나가 남으면 바운딩 박스가 그만큼 커지고,
  카드에서 높이 52px 로 맞출 때 **물건이 그만큼 작아 보인다**(대표 8-27: "썸네일도
  딱 깔끔하게 크기 맞춰서"). 실제로 브라탑·망고나시에 흰 점이 하나씩 남아 있었다.
"""
import argparse, os
import numpy as np
from PIL import Image


def clean(src, out, flip=False, maxside=256, min_frag=40, neutralize_magenta=False, log=print):
    im = Image.open(src).convert("RGBA")
    a = np.array(im).astype(int)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    # 형광 마젠타/그린 · 흰 배경 · 이미 투명한 곳을 배경으로 본다
    # ★★배경을 **색으로 판정하지 않는다.** 아무리 조건을 좁혀도 옷 색과 겹친다 —
    #   진한 분홍(#E8306A)이 마젠타 조건에, 흰 레이스가 흰 배경 조건에 걸려
    #   **드레스 치마가 통째로 뚫렸다**(대표 8-27: "치마 중앙 부분 왜 다 날아가 있냐").
    #   → 배경은 **모서리에서 이어진 영역**이다. 네 모서리 색에서 번져 나간다.
    #     옷 안쪽의 같은 색은 배경과 이어져 있지 않으므로 살아남는다.
    #     (tools/fit_sheet.py 의 dechroma 와 같은 방법이다)
    rgb = a[..., :3]
    H, W = rgb.shape[:2]
    corners = [rgb[0, 0], rgb[0, W - 1], rgb[H - 1, 0], rgb[H - 1, W - 1]]
    near = np.zeros((H, W), bool)
    for cpx in corners:
        near |= np.abs(rgb - cpx).sum(2) <= 110
    bg = np.zeros((H, W), bool)
    try:
        from scipy import ndimage as _nd
        lab0, n0 = _nd.label(near)
        seeds = set(int(lab0[y, x]) for y, x in ((0, 0), (0, W - 1), (H - 1, 0), (H - 1, W - 1))
                    if lab0[y, x] > 0)
        if seeds:
            bg = np.isin(lab0, list(seeds))
    except ImportError:
        bg = near
    bg |= (al < 128)
    keep = ~bg
    # ★잔여물 제거 — **가장 큰 덩어리의 테두리 밖**에 있는 것만 버린다.
    #   "가장 큰 덩어리만 남기기"는 쓰면 안 된다: 옷은 윤곽선과 색면이 서로 다른 덩어리라
    #   드레스 치마 안쪽이 통째로 날아간다(실제로 131,771 px 이 사라졌다).
    #   물건은 가운데 모여 있고 배경 잔여는 바깥에 흩어져 있다 — 그 차이만 쓴다.
    try:
        from scipy import ndimage
        lab, n = ndimage.label(keep)
        if n > 1:
            sizes = ndimage.sum(keep, lab, range(1, n + 1))
            big = int(np.argmax(sizes)) + 1
            ys, xs = np.where(lab == big)
            y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
            drop = 0
            for i in range(1, n + 1):
                if i == big:
                    continue
                iy, ix = np.where(lab == i)
                inside = (iy.min() >= y0 and iy.max() <= y1 and ix.min() >= x0 and ix.max() <= x1)
                if not inside:                       # 테두리 밖으로 삐져나온 것 = 배경 잔여
                    keep[lab == i] = False; drop += int(sizes[i - 1])
            if drop: log("  바깥 잔여 %d px 제거" % drop)
    except ImportError:
        pass
    o = np.array(im); o[..., 3] = np.where(keep, 255, 0)
    # ★배경을 지워도 **경계에 섞인 크로마 픽셀**이 남는다 (대표 8-27: "브라탑 썸네일 누끼
    #   바깥쪽에 마젠타 배경 아직 잔류"). 어두운 자주(#3D0042)라 형광 판정에 안 걸린다.
    #   → 남은 가장자리에서 '크로마 쪽으로 치우친' 픽셀을 **이웃 정상 색으로** 바꾼다.
    #     픽셀아트가 아니라 일러스트라 median 으로 자연스럽게 메워진다.
    rr, gg, bb = o[..., 0].astype(int), o[..., 1].astype(int), o[..., 2].astype(int)
    for _ in range(3):
        opq = o[..., 3] > 0
        edge = np.zeros_like(opq)
        edge[1:, :] |= ~opq[:-1, :]; edge[:-1, :] |= ~opq[1:, :]
        edge[:, 1:] |= ~opq[:, :-1]; edge[:, :-1] |= ~opq[:, 1:]
        rr, gg, bb = o[..., 0].astype(int), o[..., 1].astype(int), o[..., 2].astype(int)
        # ★가장자리만 보면 안 된다 — 잔여가 윤곽선 **안쪽**까지 들어와 있다(브라탑 927px).
        #   대신 **어두운 것만** 잡는다: 배경이 섞인 테두리는 밝기 70 미만의 자주(#3D0042)인데,
        #   분홍 드레스의 옷 색은 밝기 70 이상이라 하나도 안 걸린다(실측: 드레스 0 / 브라탑 921).
        lm = (np.maximum(np.maximum(rr, gg), bb) + np.minimum(np.minimum(rr, gg), bb)) / 2.0
        chroma = opq & (lm < 70) & (((rr > gg + 25) & (bb > gg + 25)) | ((gg > rr + 25) & (gg > bb + 25)))
        if not chroma.any(): break
        good = opq & ~chroma
        ys2, xs2 = np.where(chroma)
        H2, W2 = chroma.shape
        for y, x in zip(ys2, xs2):
            ya, yb2 = max(0, y - 2), min(H2, y + 3)
            xa, xb2 = max(0, x - 2), min(W2, x + 3)
            nb = good[ya:yb2, xa:xb2]
            if not nb.any():
                o[y, x, 3] = 0; continue
            o[y, x, :3] = np.median(o[ya:yb2, xa:xb2, :3][nb], axis=0)
    # 회색 아이템은 마젠타가 디자인 색일 수 없다. 브라탑처럼 형광 배경이 윤곽선 안쪽까지
    # 번진 경우에는 밝기 제한(lm < 70)만으로 밝은 핑크 잔여가 남는다. 회색 전용 옵션에서는
    # 남은 마젠타 픽셀을 전부 가장 가까운 정상 불투명 픽셀 색으로 치환한다. 알파/윤곽은 유지해
    # 테두리를 뜯어내지 않고 색 오염만 없앤다.
    if neutralize_magenta:
        opq = o[..., 3] > 0
        rr, gg, bb = o[..., 0].astype(int), o[..., 1].astype(int), o[..., 2].astype(int)
        # 본체의 회보라 음영은 채널 차가 약 8~14다. 배경이 묻은 테두리는 16 이상으로
        # 실측 분리되므로 그 경계만 잡는다(전체 옷 색을 회색으로 평탄화하지 않는다).
        magenta = opq & (rr > gg + 15) & (bb > gg + 15)
        if magenta.any():
            good = opq & ~magenta
            try:
                from scipy import ndimage
                nearest = ndimage.distance_transform_edt(~good, return_distances=False, return_indices=True)
                o[magenta, :3] = o[nearest[0][magenta], nearest[1][magenta], :3]
            except ImportError:
                # scipy 없는 환경에서도 회색 아이템답게 중립화한다.
                gray = np.rint(0.299 * rr + 0.587 * gg + 0.114 * bb).astype(np.uint8)
                o[magenta, 0] = gray[magenta]
                o[magenta, 1] = gray[magenta]
                o[magenta, 2] = gray[magenta]
            log("  마젠타 잔여 %d px 중립화" % int(magenta.sum()))
    im2 = Image.fromarray(o, "RGBA")
    bb = im2.split()[3].point(lambda v: 255 if v > 50 else 0).getbbox()
    if bb:
        im2 = im2.crop(bb)
    k = maxside / max(im2.size)
    if k < 1:
        # ★★NEAREST 로 줄인다 (대표 8-27: "검정반스 썸네일 누끼 딴 게 퀄리티 저급화,
        #   특히 흰 선이 너무 깨져 있는 느낌"). 원본은 픽셀아트를 크게 그린 것이라
        #   LANCZOS 로 줄이면 **한 칸이 여러 색으로 뭉개져** 가는 흰 선이 뭉그러진다.
        #   에셋 하드룰(NEAREST 외 보간 금지)이 여기에도 그대로 적용된다.
        im2 = im2.resize((max(1, round(im2.width * k)), max(1, round(im2.height * k))), Image.NEAREST)
    if flip:
        im2 = im2.transpose(Image.FLIP_LEFT_RIGHT)
    im2.save(out)
    log("%-24s -> %s%s" % (os.path.basename(src), im2.size, "  (좌우반전)" if flip else ""))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--flip", action="store_true", help="파일명이 좌우반전을 지시할 때")
    ap.add_argument("--neutralize-magenta", action="store_true",
                    help="회색 아이템의 남은 마젠타 색 오염을 전부 주변색으로 치환")
    a = ap.parse_args()
    clean(a.src, a.out, a.flip, neutralize_magenta=a.neutralize_magenta)
