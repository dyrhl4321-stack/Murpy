# -*- coding: utf-8 -*-
"""캠프파이어 불꽃에 흔들림을 넣어 APNG로 저장한다.

    python char/animate_campfire.py char/rooms/s2608_campfire.png

왜 APNG인가
  방 렌더(mwFurnHtml)는 아이템을 <img>로 그리고, 편집기 드래그도 img[data-idx]를 찾는다.
  스프라이트 시트 + CSS steps()로 가려면 <img>를 div로 바꿔야 하고 그러면 드래그가 깨진다.
  APNG는 파일만 바꾸면 되므로 앱 코드를 한 줄도 건드리지 않는다. 크롬·사파리·파이어폭스
  모두 지원하고 image-rendering:pixelated도 그대로 먹는다.

어떻게 흔드는가
  불꽃 픽셀만 골라 행 단위로 좌우로 민다. 이동량은 항상 아트픽셀(2유닛)의 배수여야
  픽셀 격자가 깨지지 않는다. 진폭은 위로 갈수록 크고 밑동에서 0이 되게 감쇠시킨다 —
  밑동까지 흔들면 장작과 맞닿은 자리에 틈이 생긴다.

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
AMP = 4            # 꼭대기 최대 진폭(유닛) = 아트픽셀 2칸
FRAMES = 4
DURATION = 170     # 프레임당 ms

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

    # ★움직여도 안전한 픽셀만 고른다: 8이웃이 전부 마스크이거나 투명인 것.
    #   돌·장작에 맞닿은 픽셀을 옮기면 원래 자리가 투명해지면서 이웃에 구멍이 뚫린다(실측 90px).
    safe = set()
    for (x, y) in mask:
        ok = True
        for dy in (-1, 0, 1):
            for dx2 in (-1, 0, 1):
                nx, ny = x + dx2, y + dy
                if 0 <= nx < W and 0 <= ny < H and (nx, ny) not in mask and px[nx, ny][3] > 128:
                    ok = False
        if ok:
            safe.add((x, y))

    base = im.copy()
    bpx = base.load()
    for x, y in safe:
        bpx[x, y] = (0, 0, 0, 0)

    out = []
    for f in range(frames):
        fr = base.copy()
        fpx = fr.load()
        # 프레임마다 하나의 기울기. 행에 따라 진동시키면(sin(y·k)) 전단이 생겨 불꽃이 찢어진다.
        lean = math.sin(2 * math.pi * f / frames)
        glow = 1.0 + 0.07 * math.cos(2 * math.pi * f / frames)   # 흔들림과 위상을 어긋나게
        for (x, y) in safe:
            taper = max(0.0, 1.0 - (y / float(FLAME_MAX_Y)))     # 위=1, 밑동=0 (단조 감쇠)
            dx = int(round(AMP * taper * lean / ART)) * ART      # 아트픽셀 격자 유지
            nx = x + dx
            # 목적지가 원래 돌·장작이면 덮지 않는다. 안 막으면 불꽃이 돌 위로 번진다(실측 15~18px).
            if 0 <= nx < W and ((nx, y) in mask or px[nx, y][3] <= 128):
                fpx[nx, y] = px[x, y]
        # 불꽃 전체는 밝기로 맥동시킨다 — 기하가 안 변하니 구멍이 날 수 없다
        for (x, y) in mask:
            p = fpx[x, y]
            if p[3] > 128 and is_flame(p):
                fpx[x, y] = (min(255, int(p[0] * glow)), min(255, int(p[1] * glow)),
                             min(255, int(p[2] * glow)), p[3])
        out.append(fr)

    # 접지 그림자를 맨 아래 레이어로 깔고 프레임을 얹는다 (캔버스는 아래로 GROUND_PAD 확장)
    shadow = ground_shadow(im, W, H)
    final = []
    for fr in out:
        canvas = shadow.copy()
        canvas.alpha_composite(fr, (0, 0))
        final.append(canvas)
    return final, len(mask), len(safe)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('--out', default=None, help='기본: 원본을 덮어씀')
    ap.add_argument('--frames', type=int, default=FRAMES)
    ap.add_argument('--contact', default=None, help='프레임을 가로로 이어붙인 확인용 이미지')
    args = ap.parse_args()

    im = Image.open(args.src).convert('RGBA')
    frames, n, nsafe = build_frames(im, args.frames)
    print(f'원본 {im.size}, 불꽃+테두리 {n}개, 그중 이동 가능 {nsafe}개, 프레임 {len(frames)}장')

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
