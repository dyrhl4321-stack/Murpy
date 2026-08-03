# -*- coding: utf-8 -*-
"""AI 입력용 헤어착용시트 vs 현재 앱 자산 — 픽셀로 같은지 확인."""
import os, sys, io
import numpy as np
from PIL import Image
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

H = r"C:\Users\allys\Murpy\char"
OUT = r"C:\Users\allys\Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차\헤어\_모자생성용_헤어착용시트"
AB = 128
BG = np.array([255, 0, 255, 255])
PAIRS = [
    ("walk.png", "hair_m_basic", "남_기본헤어"),
    ("walk.png", "hair_ivyleague", "남_아이비리그컷"),
    ("walk.png", "hair_m_semileaf", "남_세미리프컷"),
    ("walk_female.png", "hair_f_basic", "여_기본헤어"),
    ("walk_female.png", "hair_f_bob_bang", "여_앞머리단발"),
    ("walk_female.png", "hair_f_long", "여_긴생머리"),
]
CW, CH = 141, 224
ROWS = ["정면", "후면", "좌", "우"]

for base_n, hid, label in PAIRS:
    b = np.asarray(Image.open(os.path.join(H, base_n)).convert("RGBA")).astype(int)
    h = np.asarray(Image.open(os.path.join(H, "items", hid + ".png")).convert("RGBA")).astype(int)
    now = b.copy()
    m = h[:, :, 3] >= AB
    now[m] = h[m]
    now[m, 3] = 255
    now[now[:, :, 3] < AB] = BG
    now[:, :, 3] = 255

    p = os.path.join(OUT, label + ".png")
    if not os.path.exists(p):
        print(f"{label:12s} !! 시트 없음"); continue
    old = np.asarray(Image.open(p).convert("RGBA")).astype(int)
    if old.shape != now.shape:
        print(f"{label:12s} !! 크기 다름 {old.shape} vs {now.shape}"); continue

    d = (np.abs(old - now).sum(2) > 0)
    if not d.any():
        print(f"{label:12s} 동일 ✔")
        continue
    per = []
    for r in range(4):
        for c in range(3):
            n = int(d[r*CH:(r+1)*CH, c*CW:(c+1)*CW].sum())
            if n:
                per.append(f"{ROWS[r]}col{c}={n}")
    print(f"{label:12s} ★다름 총 {int(d.sum())}px  " + " ".join(per))
