# -*- coding: utf-8 -*-
"""캠프파이어 불꽃에 흔들림을 넣어 APNG로 저장한다.

    python char/animate_campfire.py char/rooms/s2608_campfire.png

왜 APNG인가
  방 렌더(mwFurnHtml)는 아이템을 <img>로 그리고, 편집기 드래그도 img[data-idx]를 찾는다.
  스프라이트 시트 + CSS steps()로 가려면 <img>를 div로 바꿔야 하고 그러면 드래그가 깨진다.
  APNG는 파일만 바꾸면 되므로 앱 코드를 한 줄도 건드리지 않는다. 크롬·사파리·파이어폭스
  모두 지원하고 image-rendering:pixelated도 그대로 먹는다.

어떻게 살아있게 하는가 (★좌우 전단 폐기, 7-23)
  행마다 좌우로 미는 방식(전단)은 '움직이는 행'과 '안 움직이는 밑동' 사이에 아트픽셀 계단
  경계 = 밑동과 윗동을 가르는 '한 선'을 만든다(대표 반복 지적, 이게 문제의 정체였다). 그래서
  좌우 흔들림을 아예 버린다. 대신:
    (1) 불꽃 '끝'을 위(투명 공간)로만 날름거리게 한다 — 투명한 곳으로만 자라니 전단선·구멍이 없고
        밑동은 손대지 않는다(나뉠 선이 없다).
    (2) 전체를 은은히 밝혔다 되돌리는 '숨쉬기'만 준다(어두워지지 않음·세로 파동 없음).

  불꽃과 장작은 둘 다 따뜻한 색이라 색만으로는 못 가른다. 불꽃은 장작 위에 있으므로
  FLAME_MAX_Y 위쪽만 대상으로 삼는다.
"""
import argparse
import math
import os

from PIL import Image, ImageChops, ImageFilter

ART = 2            # 아트픽셀 크기(유닛). 이동량은 이 배수여야 한다
# 이 아래는 손대지 않는다. 40으로 두면 장작 윗부분(y 36~40)까지 마스크에 들어와
# 6시 방향 세로 장작에 1픽셀 턱이 생겼다 사라지며 들썩거린다(대표 실앱 지적, 7-22).
# 행 프로파일상 y>=38부터 불꽃 x범위가 급격히 넓어진다 = 장작이 시작되는 지점.
FLAME_MAX_Y = 26
TIP = 2            # 불꽃 끝 날름거림 최대 높이(아트픽셀). 위(투명)로만 자란다
FRAMES = 6         # 부드러운 순환 (4는 뚝뚝 끊겨 보였다)
DURATION = 130     # 프레임당 ms

# 접지 그림자(돌무더기 하단 실루엣을 따라 U자로 은은하게).
# CSS 타원 그림자는 돌무더기 전체 아래에 뜬금없이 깔려 어색했다 — 대표는 돌 링을 따라
# 하단에 은은한 U자를 원했다. 실루엣을 아래로 내린 뒤 원본과 겹치는 부분을 빼면
# '물체 아래로 삐져나온 하단 테두리'만 남아 자연스러운 U자 접지가 된다.
GROUND_PAD = 12        # 캔버스를 아래로 늘려 그림자 공간 확보(원본은 하단 여백 0)
GROUND_DROP = 6        # 실루엣을 얼마나 내릴지
GROUND_BLUR = 3.2
GROUND_ALPHA = 0.42    # 은은하게


def is_flame(p):
    r, g, b, a = p
    return a > 128 and r > 170 and g > 60 and r > b + 60


def ground_shadow(im, W, H):
    """돌무더기 하단 실루엣을 따라가는 U자 접지 그림자. 확장 캔버스(H+GROUND_PAD)로 반환."""
    HH = H + GROUND_PAD
    mask = im.getchannel('A').point(lambda v: 255 if v >= 128 else 0)
    orig = Image.new('L', (W, HH), 0); orig.paste(mask, (0, 0))
    drop = Image.new('L', (W, HH), 0); drop.paste(mask, (0, GROUND_DROP))
    below = ImageChops.subtract(drop, orig)                 # 물체 아래로 삐져나온 하단 테두리 = U자
    below = below.filter(ImageFilter.GaussianBlur(GROUND_BLUR))
    below = below.point(lambda v: int(v * GROUND_ALPHA))
    return Image.merge('RGBA', (Image.new('L', (W, HH), 0),) * 3 + (below,))


def build_frames(im, frames=FRAMES):
    W, H = im.size
    px = im.load()

    flame = set((x, y) for y in range(min(FLAME_MAX_Y, H)) for x in range(W) if is_flame(px[x, y]))
    if not flame:
        raise SystemExit('불꽃 픽셀을 못 찾았습니다 — FLAME_MAX_Y나 색 조건을 확인하세요')

    # ★검은 테두리를 반드시 함께 옮긴다. 채움색만 옮기면 테두리가 제자리에 남아 형태가 부서진다.
    #   돌(밝은 회색)은 제외해야 하므로 어두운 픽셀만 고른다 — 사각 영역으로 자르면 뒤쪽 돌이 딸려온다.
    mask = set(flame)
    for (x, y) in list(flame):
        for dy in (-1, 0, 1):
            for dx2 in (-1, 0, 1):
                nx, ny = x + dx2, y + dy
                if 0 <= nx < W and 0 <= ny < H and (nx, ny) not in mask:
                    p = px[nx, ny]
                    if p[3] > 128 and (p[0] + p[1] + p[2]) < 240:   # 어두운 것 = 테두리
                        mask.add((nx, ny))

    # 각 열의 불꽃 꼭대기 y. 좌우 전단은 밑동↔윗동을 가르는 '한 선'을 만드니 안 쓴다(대표 지적).
    #  대신 불꽃 끝만 위(투명)로 날름거리게 한다 → 투명한 곳으로만 자라 전단선·구멍이 없다.
    cols = {}
    for (x, y) in flame:
        if x not in cols or y < cols[x]:
            cols[x] = y
    xs = sorted(cols)
    xmid = (xs[0] + xs[-1]) / 2.0
    span = max(1.0, (xs[-1] - xs[0]) / 2.0)

    out = []
    for f in range(frames):
        fr = im.copy()
        fpx = fr.load()
        phase = 2 * math.pi * f / frames

        # 1) 불꽃 끝 날름거림(세로). 중심 열일수록 크게·가장자리 0, 열마다 위상이 달라 자연스레 일렁인다.
        for x, ty in cols.items():
            edge = 1.0 - abs(x - xmid) / span                    # 중심 1 → 가장자리 0(가장자리는 안 튄다)
            if edge <= 0:
                continue
            n = 0.5 + 0.32 * math.sin(phase + x * 0.55) + 0.18 * math.sin(2 * phase + x * 0.31)
            add = int(round(max(0.0, min(1.0, n)) * edge * TIP)) * ART   # 0~TIP*ART 유닛, 아트픽셀 격자
            src = px[x, ty]                                      # 그 열 끝색을 위로 복제
            for k in range(1, add + 1):
                yy = ty - k
                if yy < 0:
                    break
                if px[x, yy][3] <= 128:                          # 원래 투명한 곳에만 → 구멍·덮어쓰기 없음
                    fpx[x, yy] = src

        # 2) 은은한 밝기 숨쉬기. ★어두워지면(g<1) '검은 그림자 밴드'로 보이고 세로 위상차를 주면 그게
        #    위→아래로 훑어 더 이상하다(대표 지적) → g는 항상 ≥1, 전체 같은 위상, 파동 없음.
        for (x, y) in mask:
            p = fpx[x, y]
            if p[3] > 128 and is_flame(p):
                g = 1.0 + 0.12 * (0.5 + 0.5 * math.cos(phase))
                fpx[x, y] = (min(255, int(p[0] * g)), min(255, int(p[1] * g)),
                             min(255, int(p[2] * g)), p[3])
        out.append(fr)

    # 접지 그림자를 맨 아래 레이어로 깔고 프레임을 얹는다 (캔버스는 아래로 GROUND_PAD 확장)
    shadow = ground_shadow(im, W, H)
    final = []
    for fr in out:
        canvas = shadow.copy()
        canvas.alpha_composite(fr, (0, 0))
        final.append(canvas)
    return final, len(mask), len(cols)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('--out', default=None, help='기본: 원본을 덮어씀')
    ap.add_argument('--frames', type=int, default=FRAMES)
    ap.add_argument('--contact', default=None, help='프레임을 가로로 이어붙인 확인용 이미지')
    args = ap.parse_args()

    im = Image.open(args.src).convert('RGBA')
    frames, n, ncols = build_frames(im, args.frames)
    print(f'원본 {im.size}, 불꽃+테두리 {n}개, 혀 낼 열 {ncols}개, 프레임 {len(frames)}장')

    dst = args.out or args.src
    # disposal=1(배경 복원) + blend=0(덮어쓰기): 매 프레임을 통짜로 교체한다.
    # 기본값으로 두면 프레임이 합쳐져 장수가 줄고 잔상이 남는다(실측: 4장 저장 -> 3장으로 읽힘).
    frames[0].save(dst, save_all=True, append_images=frames[1:],
                   duration=DURATION, loop=0, disposal=1, blend=0)
    print(f'저장(APNG): {dst}  {os.path.getsize(dst)} bytes')

    if args.contact:
        W, H = im.size
        sheet = Image.new('RGBA', (W * len(frames), H), (0, 0, 0, 0))
        for i, fr in enumerate(frames):
            sheet.paste(fr, (i * W, 0))
        sheet.resize((sheet.size[0] * 3, sheet.size[1] * 3), Image.NEAREST).save(args.contact)
        print(f'확인용: {args.contact}')


if __name__ == '__main__':
    main()
