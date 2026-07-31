# -*- coding: utf-8 -*-
"""대표가 직접 그릴 수 있게 '정면 뒷머리' 작업 파일을 만들어 넘긴다.

대표: "정면 뒷머리만 worn 참고해서 넘겨봐. 내가 그릴게."

원본 시트(worn)에는 얼굴 양옆으로 내려오는 뒷머리가 그려져 있는데 우리 추출이 귀 높이에서
끊었다. 원본을 빌더와 **같은 정규화 변환**으로 우리 격자에 올린 뒤,
base 실루엣 **밖**에 있는 머리카락만 후보로 꺼낸다.
  ★실루엣 밖만 쓰는 이유 = 그 자리엔 얼굴이 없다. 안쪽을 건드리면 눈·볼을 먹는다
    (7-30에 시트를 정답으로 썼다가 눈알이 깨진 적이 있다).

산출물 2개:
  1) hair_m_semileaf_정면뒷머리밑그림.png  — 현재 레이어 + 후보를 채운 시트(대표가 다듬을 것)
  2) _참고_정면뒷머리.png                  — 원본 / 현재 / 밑그림 을 나란히 크게

    python char/handoff_front_backhair.py
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_hair_layer import (BALD_M, MHAIR, CW, CH, ALPHA_BIN, SKIN_R,   # noqa: E402
                              Norm, load, pad_img, binarize)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(r"C:\Users\allys\Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차",
                       "머피에셋스튜디오 수정본", "남자헤어_작업요청")
SRC = os.path.join(MHAIR, "세미리프컷_clean-Photoroom.png")
ITEM = "hair_m_semileaf"
ROW = 0                      # 정면
SCALE = 6


def is_skin(a):
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    return (R >= SKIN_R) & (R > G + 20) & (G > B)


def over(dst, src):
    out = dst.copy()
    m = src[:, :, 3] >= ALPHA_BIN
    out[m] = src[m]
    out[m, 3] = 255
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    walk = np.asarray(Image.open(os.path.join(HERE, "walk.png")).convert("RGBA")).astype(int)
    cur = np.asarray(Image.open(os.path.join(HERE, "items", ITEM + ".png"))
                     .convert("RGBA")).astype(int)

    # 빌더와 똑같은 정규화 — base(빡빡이)에서 변환을 계산해 원본 헤어 시트에 적용한다
    norm = Norm(load(BALD_M))
    src_pad = pad_img(load(SRC))

    # ★col0(정지 프레임)에만 채운다. 열마다 따로 계산하면 걸을 때 깜빡인다(7-30에 낸 버그).
    #   3열 복제는 대표가 그린 뒤 내가 처리한다.
    out = cur.copy()
    c = 0
    bc = walk[ROW * CH:(ROW + 1) * CH, c * CW:(c + 1) * CW]
    bm = bc[:, :, 3] >= ALPHA_BIN
    top = int(np.where(bm.any(axis=1))[0].min())

    worn = binarize(norm.cell(src_pad, ROW, 0))              # 세미리프컷은 4방향 전부 col0
    wm = worn[:, :, 3] >= ALPHA_BIN
    hair_px = wm & ~is_skin(worn)                            # 머리카락(살색 아님)

    hc = out[ROW * CH:(ROW + 1) * CH, c * CW:(c + 1) * CW]
    have = hc[:, :, 3] >= ALPHA_BIN

    band = np.zeros_like(bm)
    band[top + 40:top + 105] = True                          # 얼굴 옆 ~ 턱 아래
    cand = hair_px & ~bm & ~have & band                      # ★base 실루엣 밖만

    total = int(cand.sum())
    hc[cand] = worn[cand]
    hc[cand, 3] = 255
    ys = np.where(cand.any(axis=1))[0]
    print(f"원본에서 꺼낸 정면 뒷머리 후보 {total}px  (정지 프레임 col0 만)"
          f"  rel y{ys.min()-top}~{ys.max()-top}")

    p_item = os.path.join(OUT_DIR, f"{ITEM}_정면뒷머리밑그림.png")
    Image.fromarray(out.astype(np.uint8), "RGBA").save(p_item)
    print(f"-> {p_item}")

    # 참고 이미지 — 원본(정규화) / 현재 / 밑그림
    bc = walk[ROW * CH:(ROW + 1) * CH, 0:CW]
    worn = binarize(norm.cell(src_pad, ROW, 0))
    tiles = [("원본 시트(정규화)", worn),
             ("현재 앱", over(bc, cur[ROW * CH:(ROW + 1) * CH, 0:CW])),
             ("밑그림(원본에서 채움)", over(bc, out[ROW * CH:(ROW + 1) * CH, 0:CW]))]
    pad, lbl = 8, 30
    canvas = Image.new("RGB", ((CW + pad) * len(tiles) + pad, CH + lbl + pad * 2), (250, 250, 250))
    for i, (t, a) in enumerate(tiles):
        x = pad + i * (CW + pad)
        canvas.paste(Image.fromarray(a.astype(np.uint8), "RGBA").convert("RGB"), (x, lbl + pad))
    big = canvas.resize((canvas.width * SCALE, canvas.height * SCALE), Image.NEAREST)
    # ★라벨은 확대 후에 그린다 — 먼저 그리면 NEAREST 확대로 글자가 깨진다.
    #   PIL 기본 폰트엔 한글이 없어서 □ 로 나온다 → 맑은 고딕을 쓴다.
    d = ImageDraw.Draw(big)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 34)
    except OSError:
        font = ImageFont.load_default()
    for i, (t, _) in enumerate(tiles):
        d.text(((pad + i * (CW + pad)) * SCALE, 8), t, fill=(20, 20, 20), font=font)
    p_ref = os.path.join(OUT_DIR, "_참고_정면뒷머리.png")
    big.save(p_ref)
    print(f"-> {p_ref}")

    # 대표가 되돌릴 수 있게 현재 배포본 백업도 같이 넣는다
    Image.fromarray(cur.astype(np.uint8), "RGBA").save(
        os.path.join(OUT_DIR, f"{ITEM}_현재배포본_백업.png"))
    big.save(os.path.join(HERE, "_diag", "handoff_front_backhair.png"))


if __name__ == "__main__":
    main()
