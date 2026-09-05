# -*- coding: utf-8 -*-
"""얼굴 커마 합성 코어 — ★12칸을 한 번에 생성하지 않는다. 방향별 정본 1장을 합성한다.

배경(9-03 스파이크로 증명): 제미나이에 12칸 걷기 시트를 통째로 시키면 칸마다 얼굴·머리가
제각각이라 일관성이 깨진다. 그래서 **생성이 아니라 합성**으로 푼다.
  방향별(정면/뒤/좌) 얼굴+머리 정본을 단일 포즈로 1장씩 생성(모델이 이건 깨끗이 함)
  → base 걷기 시트의 그 방향 행에 정렬·합성. 우(3행)=좌 반전. 한 행 3칸은 같은 정본.

★비율 정합(중요·9-03 재작성):
  - 정본→cell 리사이즈는 **세로 기준(가로비 유지)**. 141x224 강제 리사이즈는 얼굴을 가로로
    늘려(눈 벌어짐·입 처짐) 괴물처럼 만든다.
  - 스케일은 **얼굴(피부) 크기 기준**으로 정면에서 한 번 구해 4방향 공통 적용 → 소두/대두 방지
    (목선 감지 기반 스케일은 정본마다 흔들려 소두가 났었다).
  - 정렬: 정면=얼굴 기준(얼굴이 base 얼굴 위치·크기에 맞음), 뒤/옆=머리 최상단 기준(top-align)
    → 뒤통수 긴 머리가 안 잘린다.

산출물:
    {id}.png        base 몸 + 정본 얼굴 + 머리(구운 통짜 시트) — 앱이 바로 쓰는 시트
    {id}_body.png   base 몸 + 얼굴만(머리 없음) — 착용형 헤어 구조용(선택)
    {id}_hair.png   머리 레이어만 — 착용형 헤어 구조용(선택)
"""
import os, sys, argparse
from collections import deque
import numpy as np
from PIL import Image

M = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CW, CH = 141, 224
ROWS = 4

# ── 픽셀 유틸 ─────────────────────────────────────────────────────────────

def rm_mag(arr):
    """마젠타/보라/핑크 크로마 제거 — 경계 반투명 보라까지.
    피부·머리는 초록이 중간이라 안 걸리고, 마젠타 계열은 초록이 최소 채널이라는 성질로 잡는다."""
    r, g, b = arr[..., 0].astype(int), arr[..., 1].astype(int), arr[..., 2].astype(int)
    arr = arr.copy()
    pure = (r > 150) & (b > 110) & (g < 100)
    fringe = (r > g + 10) & (b > g + 10)
    arr[pure | fringe, 3] = 0
    return arr

def head_top(alpha_cell):
    ys = np.where(alpha_cell > 128)[0]
    return int(ys.min()) if len(ys) else 0

def neck_y(alpha_cell):
    """목선 y = 머리와 어깨 사이 폭 최소 y (band 는 base 141x224 셀 기준)."""
    w = (alpha_cell > 128).sum(axis=1)
    ys = np.where(w > 0)[0]
    if not len(ys):
        return 118
    top = ys.min()
    seg = w[top + 95:top + 120]
    return int(np.argmin(np.where(seg > 0, seg, 9999))) + top + 95

def head_x(alpha_cell):
    ys = np.where(alpha_cell > 128)[0]
    if not len(ys):
        return CW // 2
    top = ys.min()
    hs = np.where(alpha_cell[top:top + 30] > 128)[1]
    return int(hs.mean()) if len(hs) else CW // 2

def skin_mask(rgba):
    """피부(밝은 주황) 픽셀 마스크."""
    a = rgba[..., 3] > 128
    R, G, B = rgba[..., 0].astype(int), rgba[..., 1].astype(int), rgba[..., 2].astype(int)
    return a & (R > 150) & (G > 90) & (R > B + 15)

def skin_bbox(rgba):
    """피부(밝은 주황) 영역 bbox = (x0,x1,y0,y1). 없으면 None (뒤통수 등)."""
    m = skin_mask(rgba)
    ys, xs = np.where(m)
    if len(ys) < 15:
        return None
    return int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())

def skin_median(rgba):
    m = skin_mask(rgba)
    px = rgba[..., :3][m]
    return np.median(px, axis=0) if len(px) else None

def _dilate1(mask):
    out = mask.copy()
    out[1:, :] |= mask[:-1, :]; out[:-1, :] |= mask[1:, :]
    out[:, 1:] |= mask[:, :-1]; out[:, :-1] |= mask[:, 1:]
    return out

def _fill_holes(mask):
    """실루엣 안쪽으로 완전히 둘러싸인 구멍을 메운다."""
    H, W = mask.shape
    free = ~mask
    seen = np.zeros_like(mask)
    q = deque()
    for x in range(W):
        for y in (0, H - 1):
            if free[y, x] and not seen[y, x]:
                seen[y, x] = True; q.append((y, x))
    for y in range(H):
        for x in (0, W - 1):
            if free[y, x] and not seen[y, x]:
                seen[y, x] = True; q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and free[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True; q.append((ny, nx))
    return mask | (free & ~seen)

# ── 정본 준비/스케일/배치 ─────────────────────────────────────────────────

def prep(path, mirror=False):
    """정본 로드 → 마젠타 제거 → bbox 크롭 → ★세로 224 기준 리사이즈(가로비 유지)."""
    a = rm_mag(np.array(Image.open(path).convert('RGBA')))
    im = Image.fromarray(a, 'RGBA')
    bb = im.getbbox()
    if bb:
        im = im.crop(bb)
    w = max(1, round(im.width * CH / im.height))
    im = im.resize((w, CH), Image.NEAREST)
    c = np.array(im)
    if mirror:
        c = c[:, ::-1].copy()
    return c

def scale_img(arr, s):
    H, W = arr.shape[:2]
    im = Image.fromarray(arr, 'RGBA').resize((max(1, round(W * s)), max(1, round(H * s))), Image.NEAREST)
    return np.array(im)

def place(canon, ax, ay, base_ax, base_ay):
    """canon 의 앵커(ax,ay)가 base 앵커(base_ax,base_ay)에 오도록 141x224 캔버스에 배치."""
    out = np.zeros((CH, CW, 4), np.uint8)
    dy, dx = base_ay - ay, base_ax - ax
    H, W = canon.shape[:2]
    for y in range(H):
        oy = y + dy
        if 0 <= oy < CH:
            row = canon[y]
            for x in range(W):
                ox = x + dx
                if 0 <= ox < CW and row[x, 3] > 0:
                    out[oy, ox] = row[x]
    return out

# ── 헤어 마스크 ───────────────────────────────────────────────────────────

def hair_mask(canon, neck):
    """머리색만(피부X·검정 외곽선X·흰색X) 최상단에서 flood → 외곽선 leak 차단. 구멍 메움 + 1px 팽창."""
    op = canon[..., 3] > 128
    if not op.any():
        return np.zeros((CH, CW), bool)
    rgb = canon[..., :3].astype(int)
    R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    s = rgb.sum(2)
    skin = (R > 150) & (G > 95) & (R > B + 15)
    outline = s < 95
    cand = op & (~skin) & (~outline) & (s < 560)
    # ★연결 컴포넌트로: 머리색 큰 덩어리는 위에 안 붙어 있어도 다 포함(한쪽 긴 머리 누락 방지).
    ytop = np.where(op.any(1))[0].min() if op.any() else 0
    seen = np.zeros((CH, CW), bool)
    visited = np.zeros((CH, CW), bool)
    NB = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))
    for sy in range(CH):
        for sx in range(CW):
            if not cand[sy, sx] or visited[sy, sx]:
                continue
            comp = []
            q = deque([(sy, sx)]); visited[sy, sx] = True
            miny = sy
            while q:
                y, x = q.popleft(); comp.append((y, x)); miny = min(miny, y)
                for dy, dx in NB:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < CH and 0 <= nx < CW and cand[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True; q.append((ny, nx))
            # 채택: 꼭대기 근처에 닿거나(주 머리) OR 큰 덩어리이면서 '위쪽에서 내려온' 것(양쪽 긴 머리).
            #   다리·발쪽에 뜬 머리색 잡티는 miny 가 낮아(=아래) 제외된다.
            if miny <= ytop + 15 or (len(comp) >= 150 and miny <= int(CH * 0.45)):
                for (y, x) in comp:
                    seen[y, x] = True
    seen = _fill_holes(seen)
    seen = _dilate1(seen) & op
    return seen

# ── 합성 ──────────────────────────────────────────────────────────────────

def compose(base_path, front, back, left, out_body_sheet,
            out_facebody=None, out_hair=None, right=None):
    base = np.array(Image.open(base_path).convert('RGBA'))
    if base.shape[:2] != (CH * ROWS, CW * 3):
        raise SystemExit('base 시트 규격이 아니다(%s): %s' % (base_path, base.shape))
    canons = {
        0: prep(front),
        1: prep(back),
        2: prep(left),
        3: prep(right) if right else prep(left, mirror=True),
    }
    # ★글로벌 스케일 = 정면 얼굴(피부) 높이를 base 정면 얼굴 높이에 맞춤 (4방향 공통)
    base_front = base[0:CH, CW:2 * CW]
    bf = skin_bbox(base_front)
    cf = skin_bbox(canons[0])
    if bf and cf:
        S = (bf[3] - bf[2]) / max(1, (cf[3] - cf[2]))
    else:
        S = 1.0
    S = min(1.6, max(0.5, S))     # 안전 범위

    # ★피부톤 정합 델타 = 정본 얼굴 살색 - base 몸통 살색 → base 몸(팔·다리·목)을 얼굴 톤에 맞춰
    #   얼굴↔몸 경계 색 끊김("댕강")을 없앤다.
    fmed = skin_median(scale_img(canons[0], S))
    bmed = skin_median(base[0:CH, CW:2 * CW])
    skin_delta = np.clip(fmed - bmed, -70, 70) if (fmed is not None and bmed is not None) else np.zeros(3)

    baked = base.copy()
    facebody = base.copy()
    hair_sheet = np.zeros_like(base)

    for R in range(ROWS):
        mid = base[R * CH:(R + 1) * CH, CW:2 * CW]
        ma = mid[..., 3]
        bt, bn, bx = head_top(ma), neck_y(ma), head_x(ma)
        cs = scale_img(canons[R], S)
        if R == 0:
            # 정면 = ★정본 얼굴의 '턱(최하단)'을 base 목선에 딱 붙이고 중심x를 머리중심에 맞춤.
            #   → 목이 짧아지고(귀신목 방지) 얼굴이 base 머리영역을 정확히 채운다.
            cn = neck_y(cs[..., 3])
            fsk = skin_mask(cs); fsk[cn:] = False          # 정본 얼굴 피부만(어깨 제외)
            ys, xs = np.where(fsk)
            if len(xs):
                canon = place(cs, int(round(xs.mean())), int(ys.max()), bx, bn - 1)
            else:
                canon = place(cs, head_x(cs[..., 3]), head_top(cs[..., 3]), bx, bt)
        else:
            # 뒤/옆 = 머리 최상단 기준 top-align (뒤통수 긴머리 안 잘림)
            canon = place(cs, head_x(cs[..., 3]), head_top(cs[..., 3]), bx, bt)

        hmask = hair_mask(canon, bn)
        hpx = canon[..., :3][hmask]
        hcol = np.array([*np.median(hpx, 0).astype(np.uint8), 255], np.uint8) if len(hpx) else None  # 머리 대표색
        op = canon[..., 3] > 128
        cnk = neck_y(canon[..., 3])            # ★정본 자기 목선 — 그 아래 어깨/몸은 버리고 '머리'만 얼굴로 씀
        above = np.zeros((CH, CW), bool)
        above[:cnk] = True                     # (예전엔 base bn 까지 써서 정본 어깨가 이중으로 붙었다)
        face_mask = op & above & (~hmask)

        # 목 브리지용 피부색(정본 목 부근 밝은 픽셀)
        nb = canon[max(0, bn - 18):bn]
        na = nb[..., 3] > 128
        npx = nb[..., :3].reshape(-1, 3); nal = nb[..., 3].reshape(-1)
        skpx = npx[(nal > 128) & (npx.sum(1) > 300)]
        skin_col = np.array([*skpx.mean(0).astype(np.uint8), 255], np.uint8) if len(skpx) else None
        neckcols = (na & (nb[..., :3].sum(2) > 300)).any(0) if len(nb) else np.zeros(CW, bool)

        for C in range(3):
            xs = slice(C * CW, (C + 1) * CW)
            cell = base[R * CH:(R + 1) * CH, xs].copy()
            sm = skin_mask(cell)                           # ★base 몸 살색을 얼굴 톤에 맞춤(이음새 색맞춤)
            if sm.any():
                cell[..., :3][sm] = np.clip(cell[..., :3][sm].astype(int) + skin_delta, 0, 255).astype(np.uint8)
            cell[:bn] = 0                                  # 목선 위 base 원래 머리 제거
            fb = cell.copy()
            fb[face_mask] = canon[face_mask]
            if skin_col is not None:                       # ★좁은 목만: head_x 중심 ±12px 를 턱밑~몸통까지 피부로 이어줌
                x0, x1 = max(0, bx - 12), min(CW, bx + 13)
                fys = np.where(face_mask[:, x0:x1].any(1))[0]
                ytop = (fys.max() + 1) if len(fys) else bn - 10
                for x in range(x0, x1):
                    for y in range(ytop, min(CH, bn + 2)):
                        px = fb[y, x]; ss = int(px[0]) + int(px[1]) + int(px[2])
                        if px[3] < 128 or ss < 170 or (y < bn and ss < 480):  # 투명·검정·어두운띠 모두 밝은 피부로
                            fb[y, x] = skin_col
            bake = fb.copy()
            bake[hmask] = canon[hmask]
            # ★목 옆 빈 공간을 '옆 머리 텍스처를 끌어와' 채움(단색 뭉갬 방지 · 목 뒤로 덮인 느낌).
            def _is_hair(px):
                r, g, b, a = int(px[0]), int(px[1]), int(px[2]), int(px[3])
                if a < 128:
                    return False
                s = r + g + b
                return (not ((r > 150) and (g > 95) and (r > b + 15))) and (95 <= s < 560)
            for y in range(max(0, bn - 14), min(CH, bn + 6)):
                opq = np.where(bake[y, :, 3] > 128)[0]
                if len(opq) >= 2:
                    for x in range(opq.min() + 1, opq.max()):
                        if bake[y, x, 3] < 128:
                            src = None
                            for d in range(1, CW):
                                xr, xl = x + d, x - d
                                if xr < CW and _is_hair(bake[y, xr]):
                                    src = bake[y, xr].copy(); break
                                if xl >= 0 and _is_hair(bake[y, xl]):
                                    src = bake[y, xl].copy(); break
                            if src is not None:
                                bake[y, x] = src
            baked[R * CH:(R + 1) * CH, xs] = bake
            facebody[R * CH:(R + 1) * CH, xs] = fb
            hs = np.zeros_like(cell); hs[hmask] = canon[hmask]
            hair_sheet[R * CH:(R + 1) * CH, xs] = hs

    os.makedirs(os.path.dirname(out_body_sheet), exist_ok=True)
    Image.fromarray(baked, 'RGBA').save(out_body_sheet)
    print('composite ->', os.path.basename(out_body_sheet), '(scale %.2f)' % S)
    if out_facebody:
        Image.fromarray(facebody, 'RGBA').save(out_facebody)
    if out_hair:
        Image.fromarray(hair_sheet, 'RGBA').save(out_hair)
    return out_body_sheet


def preview_2x(sheet_path, out_path):
    im = Image.open(sheet_path).convert('RGBA')
    im.resize((im.width * 2, im.height * 2), Image.NEAREST).save(out_path)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', required=True)
    ap.add_argument('--gender', default='여', choices=['남', '여'])
    ap.add_argument('--front', required=True)
    ap.add_argument('--back', required=True)
    ap.add_argument('--left', required=True)
    ap.add_argument('--right')
    ap.add_argument('--layers', action='store_true')
    ap.add_argument('--preview')
    a = ap.parse_args()
    base = os.path.join(M, 'char', 'walk_female.png' if a.gender == '여' else 'walk.png')
    fdir = os.path.join(M, 'char', 'faces')
    out = os.path.join(fdir, a.id + '.png')
    compose(base, a.front, a.back, a.left, out,
            out_facebody=os.path.join(fdir, a.id + '_body.png') if a.layers else None,
            out_hair=os.path.join(fdir, a.id + '_hair.png') if a.layers else None,
            right=a.right)
    if a.preview:
        preview_2x(out, a.preview)
