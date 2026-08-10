# -*- coding: utf-8 -*-
"""히든 캐릭터 누끼본(1408x3008, 3열x4행, 투명) → 게임 시트 char/hidden_*.png.

build_walk.py와 같은 규격(셀 높이 224 = TARGET_H 214 + 상6 하4)으로 맞춰 사람/헬토리와 스케일 일치.
소스가 정확한 3등분이 아니어도(1408÷3 비정수) 셀별로 캐릭터 bbox를 찾아 균일 셀에 재정렬한다.
프레임 재생성 시 소스만 갈고 재실행 → index.html ?v= 만 올리면 반영.
"""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET_H = 214
PADX, PAD_TOP, PAD_BOTTOM = 6, 6, 4
SRCDIR = r"C:\Users\allys\Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차\머피_로고삭제툴_에셋보관"
_DESKTOP = r"C:\Users\allys\Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차"
# (파일명, largest_only). largest_only=True면 셀에서 가장 큰 연결덩어리(캐릭터)만 추출 →
#   외딴 제미나이 ✦ 등 작은 잡티가 자동 제거된다(누끼 전 워터마크 제거를 못 한 헬토리용).
_LIMITED = os.path.join(_DESKTOP, '한정판캐릭터')
SOURCES = {
    'hidden_cult':   (os.path.join(SRCDIR, '화요일교 교주 시안_clean-nukki.png'), False),
    'hidden_somm':   (os.path.join(SRCDIR, '소믈리에_clean-nukki.png'), False),
    'hidden_zombie': (os.path.join(SRCDIR, '좀비_clean-nukki.png'), False),
    'heltori':       (os.path.join(_DESKTOP, '헬토리_초안-Photoroom.png'), True),
    # 돼쫀토(코드 해금 한정판, 2026-08-10). 원본 → remove_gemini_watermark.py -f → nukki.py 순서.
    'ddungddung':    (os.path.join(_LIMITED, '돼쫀토_clean-nukki.png'), False),
}


def _largest_bbox(cell):
    """셀에서 가장 큰 불투명 연결덩어리의 bbox. 외딴 잡티(워터마크)는 무시."""
    import numpy as np
    from scipy import ndimage
    a = np.asarray(cell)[..., 3] >= 40
    lab, n = ndimage.label(a)
    if n == 0:
        return None
    sizes = ndimage.sum(a, lab, range(1, n + 1))
    big = int(np.argmax(sizes)) + 1
    ys, xs = np.where(lab == big)
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def build(name, path, largest_only=False):
    im = Image.open(path).convert('RGBA')
    W, H = im.size
    subs = []
    maxw = 0
    for r in range(4):
        for c in range(3):
            x0, x1 = round(W * c / 3), round(W * (c + 1) / 3)
            y0, y1 = round(H * r / 4), round(H * (r + 1) / 4)
            cell = im.crop((x0, y0, x1, y1))
            bb = _largest_bbox(cell) if largest_only else cell.getbbox()
            if not bb:
                subs.append(None)
                continue
            s = cell.crop(bb)
            sc = TARGET_H / s.height
            s = s.resize((max(1, round(s.width * sc)), TARGET_H), Image.LANCZOS)
            subs.append(s)
            maxw = max(maxw, s.width)
    cw = maxw + PADX * 2
    chh = TARGET_H + PAD_TOP + PAD_BOTTOM
    sheet = Image.new('RGBA', (cw * 3, chh * 4), (0, 0, 0, 0))
    for i, s in enumerate(subs):
        if s is None:
            continue
        r, c = i // 3, i % 3
        ox = c * cw + (cw - s.width) // 2
        oy = r * chh + (chh - PAD_BOTTOM - s.height)
        sheet.alpha_composite(s, (ox, oy))
    out = os.path.join(HERE, name + '.png')
    sheet.save(out)
    print(name, '->', sheet.size, 'cell', cw, 'x', chh)


if __name__ == '__main__':
    # 인자를 주면 그 이름만 다시 만든다(예: python char/extract_hidden.py ddungddung).
    # 인자가 없으면 전부 — 단 소스가 없는 것은 건너뛴다(옛 소스가 지워진 PC에서 터지지 않게).
    import sys
    only = set(sys.argv[1:])
    for name, (path, largest) in SOURCES.items():
        if only and name not in only:
            continue
        if not os.path.exists(path):
            print(name, '건너뜀 — 소스 없음:', path)
            continue
        build(name, path, largest)
