# -*- coding: utf-8 -*-
"""냉장고 아래 문짝의 유령 자석 장식을 지운다.

    python char/remove_fridge_ghost.py

Pixel Interiors 시트의 냉장고에는 아래 문짝에 흰 유령 모양 자석 스티커가
원래 그려져 있다. 앱 축소(768→320 BILINEAR)에서는 정체불명 흰 얼룩으로만
보여서 제거(대표 지시 7-23). slice_pi_furniture.py로 재추출하면 다시 생기니
재추출 후엔 이 스크립트를 다시 돌릴 것.

지우는 법: 유령 bbox 안에서 같은 행의 문짝 색(bbox 왼쪽 바깥 샘플)과 크게
다른 픽셀만 그 문짝 색으로 치환 — 문짝의 세로 음영은 행별 샘플이라 보존되고,
문 경계·손잡이 하이라이트는 bbox 밖이라 안 건드린다.
"""
from PIL import Image

FILES = ['char/rooms/pi_fridge.png', 'char/rooms/pi_fridge_white.png']
DIFF = 9           # 문짝 색과 이만큼 다르면 유령 픽셀로 본다 (18은 회색 드롭섀도를 놓침 — 실측)
SAMPLE_DX = 10     # 문짝 색 샘플 위치: 확장 bbox 왼쪽으로 이 만큼 바깥
PAD_L, PAD_R, PAD_T, PAD_B = 8, 5, 4, 12   # 유령 드롭섀도가 bbox 밖(특히 좌·하)까지 뻗는다 — 실측


def find_ghost_bbox(im):
    """검은 냉장고 기준: 아래 문짝(세로 중앙 아래)에서 밝은(흰) 픽셀 덩어리 bbox."""
    W, H = im.size
    px = im.load()
    # ★왼쪽 절반만 탐색 — 오른쪽 손잡이 하이라이트(흰 세로줄)가 딸려오면 bbox가 문짝 전체로 번진다
    pts = [(x, y) for y in range(H // 2, H) for x in range(W // 2)
           if px[x, y][3] > 128 and px[x, y][0] > 180 and px[x, y][1] > 180 and px[x, y][2] > 180]
    if not pts:
        raise SystemExit('유령 픽셀을 못 찾았습니다')
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def clean(path, bbox):
    im = Image.open(path).convert('RGBA')
    px = im.load()
    x0, y0, x1, y1 = bbox
    n = 0
    for y in range(y0 - PAD_T, y1 + PAD_B + 1):
        base = px[max(0, x0 - PAD_L - SAMPLE_DX), y]          # 같은 행 문짝 색(확장 bbox 밖)
        for x in range(x0 - PAD_L, x1 + PAD_R + 1):
            p = px[x, y]
            if p[3] > 128 and (abs(p[0] - base[0]) > DIFF or abs(p[1] - base[1]) > DIFF
                               or abs(p[2] - base[2]) > DIFF):
                px[x, y] = base
                n += 1
    im.save(path)
    print(f'{path}: {n}픽셀 치환 (bbox {bbox})')


def main():
    # bbox는 검은 냉장고에서 찾는다(어두운 문짝이라 흰 유령이 확실히 구분됨).
    # 두 냉장고는 같은 시트 모듈이라 위치가 같다.
    dark = Image.open(FILES[0]).convert('RGBA')
    bbox = find_ghost_bbox(dark)
    print('유령 bbox:', bbox)
    for f in FILES:
        clean(f, bbox)


if __name__ == '__main__':
    main()
