# -*- coding: utf-8 -*-
"""
머피월드 걷기 스프라이트 빌드 파이프라인 (캐릭터 여러 개 지원)
  <name>_source.png (단색 배경 마스터) --> <name>.png (게임이 읽는 시트)

사용법:  python build_walk.py
새 캐릭터 추가: _source.png 저장 후 아래 CONFIGS 에 항목 하나 추가(배경색·격자밴드).
새 아트로 교체: 해당 _source.png 만 갈아끼우고 재실행 → index.html 의 ?v= 만 올리면 배포 반영.

출력 규격: 3열[정지, 걸음A, 걸음B] × 3행[아래(정면), 위(뒤통수), 옆(왼쪽 향)]
  - 옆모습은 왼쪽 향 한 벌만(오른쪽은 코드에서 미러). 모든 프레임 같은 키로 정규화.
  - 배경 제거 = 테두리 flood-fill (내부 하이라이트/눈 흰자가 배경색과 비슷해도 보존).
"""
from PIL import Image
from collections import deque
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET_H = 214
PADX, PAD_TOP, PAD_BOTTOM = 6, 6, 4

# 캐릭터별 설정 (격자밴드는 각 소스에서 측정한 값)
CONFIGS = [
    dict(name="walk",    bg=(10, 182, 230),
         cols=[(223, 341), (493, 610), (742, 857)],
         rows=[(24, 240), (270, 487), (514, 710)]),      # 사람(디폴트)
    dict(name="heltori", alpha=True,     # Photoroom 누끼 완료본(투명 PNG) → 알파로 바로 사용
         cols=[(201, 329), (450, 579), (682, 810)],
         rows=[(27, 224), (254, 454), (476, 661)]),       # 헬토리(근방단 한정)
]

def build(cfg):
    src = os.path.join(HERE, cfg["name"] + "_source.png")
    out = os.path.join(HERE, cfg["name"] + ".png")
    im = Image.open(src).convert("RGBA"); W, H = im.size; px = im.load()

    if cfg.get("alpha"):
        # 이미 배경 제거된 투명 PNG(Photoroom 등): 알파로 마스크 (매트/침식 불필요)
        mask = [[1 if px[x, y][3] >= 40 else 0 for x in range(W)] for y in range(H)]
    else:
        BG = cfg["bg"]

        def is_bg(c, tol=78):
            return abs(c[0]-BG[0]) < tol and abs(c[1]-BG[1]) < tol and abs(c[2]-BG[2]) < tol

        bgmask = [[False]*W for _ in range(H)]
        dq = deque()
        for x in range(W):
            for y in (0, H-1):
                if is_bg(px[x, y][:3]) and not bgmask[y][x]: bgmask[y][x] = True; dq.append((x, y))
        for y in range(H):
            for x in (0, W-1):
                if is_bg(px[x, y][:3]) and not bgmask[y][x]: bgmask[y][x] = True; dq.append((x, y))
        while dq:
            x, y = dq.popleft()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nx, ny = x+dx, y+dy
                    if 0 <= nx < W and 0 <= ny < H and not bgmask[ny][nx] and is_bg(px[nx, ny][:3]):
                        bgmask[ny][nx] = True; dq.append((nx, ny))
        raw = [[0 if bgmask[y][x] else 1 for x in range(W)] for y in range(H)]
        mask = [[0]*W for _ in range(H)]
        for y in range(1, H-1):
            for x in range(1, W-1):
                if all(raw[y+dy][x+dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)):
                    mask[y][x] = 1

    def largest(x0, y0, x1, y1):
        seen = [[False]*(x1-x0) for _ in range(y1-y0)]; best = []
        for sy in range(y0, y1):
            for sx in range(x0, x1):
                if mask[sy][sx] and not seen[sy-y0][sx-x0]:
                    comp = []; q = deque([(sx, sy)]); seen[sy-y0][sx-x0] = True
                    while q:
                        cx, cy = q.popleft(); comp.append((cx, cy))
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                            nx, ny = cx+dx, cy+dy
                            if x0 <= nx < x1 and y0 <= ny < y1 and mask[ny][nx] and not seen[ny-y0][nx-x0]:
                                seen[ny-y0][nx-x0] = True; q.append((nx, ny))
                    if len(comp) > len(best): best = comp
        return best

    def cells(bands, tot, margin=30):
        return [(max(0, a-margin), min(tot, b+margin)) for (a, b) in bands]

    subs = []; maxw = 0
    for (ry0, ry1) in cells(cfg["rows"], H):
        for (cx0, cx1) in cells(cfg["cols"], W):
            comp = largest(cx0, ry0, cx1, ry1)
            xs = [p[0] for p in comp]; ys = [p[1] for p in comp]
            bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
            s = Image.new("RGBA", (bx1-bx0+1, by1-by0+1), (0, 0, 0, 0)); sp = s.load()
            for (x, y) in comp:
                sp[x-bx0, y-by0] = (px[x, y][0], px[x, y][1], px[x, y][2], 255)
            sc = TARGET_H / s.height
            s = s.resize((max(1, round(s.width*sc)), TARGET_H), Image.LANCZOS)
            subs.append(s); maxw = max(maxw, s.width)

    cw = maxw + PADX*2; ch = TARGET_H + PAD_TOP + PAD_BOTTOM
    sheet = Image.new("RGBA", (cw*3, ch*3), (0, 0, 0, 0))
    for i, s in enumerate(subs):
        r = i // 3; c = i % 3
        ox = c*cw + (cw - s.width)//2
        oy = r*ch + (ch - PAD_BOTTOM - s.height)
        sheet.alpha_composite(s, (ox, oy))
    if not cfg.get("alpha"):
        fill_notches(sheet)
    sheet.save(out)
    print("saved", out, sheet.size, "cell", cw, ch)


def fill_notches(img, passes=4, thr=16):
    """오목한 틈(배경이 파고든 곳)만 주변색으로 메움. 넓은 틈(다리·귀 사이)은 유지."""
    W, H = img.size
    for _ in range(passes):
        px = img.load(); todo = []
        for y in range(2, H-2):
            for x in range(2, W-2):
                if px[x, y][3] >= 40:
                    continue
                cnt = rs = gs = bs = 0
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        p = px[x+dx, y+dy]
                        if p[3] >= 40:
                            cnt += 1; rs += p[0]; gs += p[1]; bs += p[2]
                if cnt >= thr:
                    todo.append((x, y, rs//cnt, gs//cnt, bs//cnt))
        if not todo:
            break
        for (x, y, r, g, b) in todo:
            px[x, y] = (r, g, b, 255)

if __name__ == "__main__":
    for cfg in CONFIGS:
        build(cfg)
