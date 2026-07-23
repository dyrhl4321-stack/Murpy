# -*- coding: utf-8 -*-
"""아기 공룡에 '둥가둥가' 아이들 모션을 넣어 APNG로 저장한다.

    python char/animate_dino.py char/rooms/s2608_dino.png

왜 APNG인가 — 캠프파이어와 동일. 방 렌더(mwFurnHtml)가 <img>라 스프라이트시트+CSS를
쓰면 드래그가 깨진다. APNG는 파일만 갈면 된다. 저장 시 disposal=1, blend=0 필수.

모션(둥가둥가): 엉덩이(바닥)를 고정한 스쿼시-스트레치 바운스. 아래로 눌릴 땐 세로로
  눌리고 가로로 살짝 벌어지며(부피보존 근사), 위로는 늘어난다 → 젤리처럼 통통. 배 위에
  얹힌 두 손도 함께 오르내려 '배 안고 둥가둥가'로 읽힌다.
  ※대표 피드백: 세로 워프(배만 눌림)보다 이 스쿼시 버전이 낫다 → 이 버전 유지, 진폭만 줄임.
  ※재생성은 반드시 애니 이전 정적 원본에서(현재 png가 APNG면 0프레임만 읽힘).
"""
import argparse
import math
from PIL import Image

FRAMES = 8
DURATION = 120       # 프레임당 ms
SQUISH = 0.028       # 세로 스쿼시 진폭(±2.8%). 대표 피드백으로 5.5%→2.8%로 크게 줄임


def build_frames(im, frames=FRAMES):
    W, H = im.size
    bbox = im.getbbox()
    if not bbox:
        raise SystemExit('빈 이미지입니다')
    content = im.crop(bbox)
    cw, ch = content.size
    cx = (bbox[0] + bbox[2]) / 2.0      # 콘텐츠 가로중심
    cb = bbox[3]                        # 콘텐츠 바닥 y(고정점=엉덩이)

    out = []
    for f in range(frames):
        ph = 2 * math.pi * f / frames
        # cos: f=0에서 최대로 눌림(아래) → 위로 늘었다 반복. 부드러운 순환.
        sy = 1.0 - SQUISH * math.cos(ph)          # 세로 배율
        sx = 1.0 / math.sqrt(sy)                  # 가로는 반대(부피보존 근사)
        nw = max(1, round(cw * sx))
        nh = max(1, round(ch * sy))
        sc = content.resize((nw, nh), Image.NEAREST)   # 픽셀 유지
        canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ox = round(cx - nw / 2.0)                  # 가로중심 정렬
        oy = round(cb - nh)                        # ★바닥(엉덩이) 정렬 = 위에서만 늘고줄음
        canvas.alpha_composite(sc, (ox, oy))
        out.append(canvas)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('--out', default=None)
    ap.add_argument('--frames', type=int, default=FRAMES)
    ap.add_argument('--contact', default=None)
    args = ap.parse_args()

    im = Image.open(args.src).convert('RGBA')
    frames = build_frames(im, args.frames)
    print(f'원본 {im.size}, 프레임 {len(frames)}장, SQUISH {SQUISH}')

    dst = args.out or args.src
    frames[0].save(dst, save_all=True, append_images=frames[1:],
                   duration=DURATION, loop=0, disposal=1, blend=0)
    import os
    print(f'저장(APNG): {dst}  {os.path.getsize(dst)} bytes')

    if args.contact:
        W, H = im.size
        sheet = Image.new('RGBA', (W * len(frames), H), (30, 30, 40, 255))
        for i, fr in enumerate(frames):
            sheet.paste(fr, (i * W, 0), fr)
        sheet.resize((sheet.size[0] * 4, sheet.size[1] * 4), Image.NEAREST).save(args.contact)
        print(f'확인용: {args.contact}')


if __name__ == '__main__':
    main()
