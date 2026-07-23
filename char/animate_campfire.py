# -*- coding: utf-8 -*-
"""캠프파이어 불꽃에 흔들림을 넣어 APNG로 저장한다.

    python char/animate_campfire.py char/rooms/s2608_campfire.png

왜 APNG인가
  방 렌더(mwFurnHtml)는 아이템을 <img>로 그리고, 편집기 드래그도 img[data-idx]를 찾는다.
  스프라이트 시트 + CSS steps()로 가려면 <img>를 div로 바꿔야 하고 그러면 드래그가 깨진다.
  APNG는 파일만 바꾸면 되므로 앱 코드를 한 줄도 건드리지 않는다. 크롬·사파리·파이어폭스
  모두 지원하고 image-rendering:pixelated도 그대로 먹는다.

어떻게 살아있게 하는가 (★불꽃 덩어리 통째, 7-23 최종)
  '밑동과 윗동이 한 선으로 나뉜다'의 진짜 원인: 옛 마스크가 y<26만 불꽃으로 취급해
  노란 심장 대부분(y 26~35, 불꽃에서 제일 넓고 밝은 부분!)이 애니·밝기에서 통째로
  빠져 있었다(대표가 정확히 지적 — "처음부터 경계선 위쪽만 작업"). 실측: 불꽃 몸통은
  y 0~35 (x 64~91), y 36~37 경계, y 38부터 장작.

  그래서 불꽃 전체(y<FLAME_MAX_Y=36)를 한 덩어리로 잡고:
    (1) 열(세로줄)마다 위아래로 일렁인다 — 원본을 그대로 둔 채 그 위에 이동본을 덮어
        그리므로(draw-over) 구멍이 안 생기고, 목적지가 돌·장작이면 덮지 않아 침범도 없다.
        가로 전단(행 좌우밀기)은 계단 경계선을 만들어 금지.
    (2) 불꽃 '전체'에 은은한 밝기 숨쉬기(어두워지지 않음·세로 파동 없음) — 일부만
        밝히면 그 경계가 또 선이 된다.

  불꽃과 장작은 둘 다 따뜻한 색이라 색만으로는 못 가른다. 위치(y<36, x 60~95)로 가른다.
"""
import argparse
import math
import os

from PIL import Image, ImageChops, ImageFilter

ART = 2            # 아트픽셀 크기(유닛). 이동량은 이 배수여야 한다
# 불꽃 몸통의 진짜 바닥. 실측(행 프로파일): y 0~35 불꽃, 36~37 경계, 38부터 장작.
# ※26으로 두면 노란 심장 아랫부분이 정지해 '한 선으로 나뉜' 느낌(대표 지적의 원인).
# ※40이면 장작 윗부분이 들어와 세로 장작에 1픽셀 턱이 들썩인다(7-22 실앱 지적).
FLAME_MAX_Y = 36
FLAME_X = (60, 95) # 불꽃 x 범위 가드(실측 64~91 + 여유). 왼쪽 장작 끝(x58)이 y36에 걸린다
AMP = 3.0          # 열 일렁임 기본 진폭(유닛)
AMP2 = 1.5         # 2배속 하모닉(유닛) — 단일 사인은 기계적으로 보인다
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

    x0, x1 = FLAME_X
    flame = set((x, y) for y in range(min(FLAME_MAX_Y, H)) for x in range(x0, min(x1 + 1, W))
                if is_flame(px[x, y]))
    if not flame:
        raise SystemExit('불꽃 픽셀을 못 찾았습니다 — FLAME_MAX_Y나 색 조건을 확인하세요')

    # ★검은 테두리를 반드시 함께 옮긴다. 채움색만 옮기면 테두리가 제자리에 남아 형태가 부서진다.
    #   돌(밝은 회색)은 제외해야 하므로 어두운 픽셀만 고른다 — 사각 영역으로 자르면 뒤쪽 돌이 딸려온다.
    mask = set(flame)
    for (x, y) in list(flame):
        for dy in (-1, 0, 1):
            for dx2 in (-1, 0, 1):
                nx, ny = x + dx2, y + dy
                if 0 <= nx < W and 0 <= ny < H and (nx, ny) not in mask and ny <= FLAME_MAX_Y + 1:
                    p = px[nx, ny]
                    if p[3] > 128 and (p[0] + p[1] + p[2]) < 240:   # 어두운 것 = 테두리
                        mask.add((nx, ny))

    # 열(세로줄)별 불꽃 픽셀 목록. 덩어리 전체가 열 단위로 위아래 일렁인다.
    cols = {}
    for (x, y) in mask:
        cols.setdefault(x, []).append(y)

    out = []
    for f in range(frames):
        fr = im.copy()          # ★원본을 그대로 두고 그 위에 이동본을 덮어 그린다 → 구멍 원천 차단
        fpx = fr.load()
        phase = 2 * math.pi * f / frames

        # 1) 열별 세로 일렁임 — 불꽃 '전체'가 움직인다(경계선 없음).
        #    열마다 위상이 달라 물결치고, 2배속 하모닉을 섞어 기계적 반복감을 죽인다.
        #    ★아래 방향은 1아트픽셀로 제한 — 테두리가 몸통 깊숙이 내려오면 불꽃 안에 검은 얼룩이 남는다.
        for x, ys in cols.items():
            v = AMP * math.sin(phase + x * 0.45) + AMP2 * math.sin(2 * phase + x * 0.9)
            k = int(round(v / ART)) * ART                        # 아트픽셀 격자 유지
            k = max(-ART, min(2 * ART, k))                       # 아래 -1아트픽셀, 위 +2아트픽셀
            if k == 0:
                continue
            # ★몸통에서 이어지는 데까지만 그린다. 목적지가 돌·장작에 막히면 그 너머(위/아래)는
            #   전부 중단 — 안 그러면 돌 위 하늘에 '떨어져 나온 점'이 뜬다(검수 실측).
            run = sorted(ys, reverse=(k > 0))                    # 위로 갈 땐 아래(몸통)부터 위로
            for y in run:
                ny = y - k                                       # k>0 = 위로
                if not (0 <= ny < H):
                    break
                # 목적지가 원래 돌·장작이면 덮지 않는다(불꽃이 돌 위로 번지는 것 방지).
                if (x, ny) in mask or px[x, ny][3] <= 128:
                    fpx[x, ny] = px[x, y]
                else:
                    break                                        # 막힌 지점 너머는 고립 조각 → 버림

        # 2) 은은한 밝기 숨쉬기 — 반드시 불꽃 '전체'에. 일부만 밝히면 그 경계가 또 선이 된다.
        #    ★어두워지면(g<1) '검은 그림자 밴드'로 보이고 세로 위상차는 그 밴드가 훑는다(금기 2개).
        for (x, y) in mask:
            p = fpx[x, y]
            if p[3] > 128 and is_flame(p):
                g = 1.0 + 0.10 * (0.5 + 0.5 * math.cos(phase))
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
