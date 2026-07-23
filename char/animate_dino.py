# -*- coding: utf-8 -*-
"""아기 공룡에 '둥가둥가'(배 안고 살랑살랑) 아이들 모션을 넣어 APNG로 저장한다.

    python char/animate_dino.py char/rooms/s2608_dino.png

왜 APNG인가 — 캠프파이어와 동일. 방 렌더(mwFurnHtml)가 <img>라 스프라이트시트+CSS를
쓰면 드래그가 깨진다. APNG는 파일만 갈면 된다. 저장 시 disposal=1, blend=0 필수
(기본값이면 프레임이 뭉개진다 — 캠프파이어에서 실측).

모션(배 두들기며 둥가둥가):
  ★손만 따로 떼어내는 건 불가(발이 몸통과 같은 초록이라 색으로 못 가름 — 마스크가 몸통까지
    뭉텅이로 잡힘). 그래서 '세로 워프'로 간다: 머리(위)·발(아래)은 고정하고 배 밴드(BELLY)만
    위아래로 눌렸다 폈다 한다. 손이 배 위에 얹혀 있으니 배가 눌릴 때 손도 같이 눌려 '배 두들기'로
    읽히고, 전체가 통째로 흔들리던 둥가둥가는 사라진다.
  워프 = 열마다 동일한 세로 변위장(disp)을 준다 → 구멍·이음새·가로 어긋남이 없다.
    disp(y) = AMP·pulse(f)·bump(y). bump는 배 중심에서 최대, 머리·발에서 0(양끝 고정).
  ※재생성은 반드시 애니 이전 정적 원본에서(현재 png가 APNG면 0프레임만 읽힘).
"""
import argparse
import math
from PIL import Image

FRAMES = 8
DURATION = 120       # 프레임당 ms
AMP = 4.5            # 배 눌림 최대 변위(px). 손을 더 확실히 두들기게 키움(대표 피드백)
BELLY_Y0 = 50        # 배 밴드 상단(이 위=머리, 안 움직임)
BELLY_Y1 = 101       # 배 밴드 하단(이 아래=발/바닥, 안 움직임)
BODY_SQUISH = 0.012  # 전체 둥가둥가는 확 줄임(5.5%→1.2%, 대표: 둥가둥가 과함). 0이면 배만


def _bump(y):
    if y <= BELLY_Y0 or y >= BELLY_Y1:
        return 0.0
    return math.sin(math.pi * (y - BELLY_Y0) / (BELLY_Y1 - BELLY_Y0))   # 배 중심 1, 양끝 0


def build_frames(im, frames=FRAMES):
    W, H = im.size
    src = im.load()
    bbox = im.getbbox()
    cx = (bbox[0] + bbox[2]) / 2.0
    cb = bbox[3]
    cw = bbox[2] - bbox[0]
    ch = bbox[3] - bbox[1]

    out = []
    for f in range(frames):
        ph = 2 * math.pi * f / frames
        pulse = math.sin(2 * ph)     # 한 사이클에 2번 두들김(탭·탭)
        # 1) 배 밴드 세로 워프(머리·발 고정)
        warp = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        wpx = warp.load()
        for y in range(H):
            d = AMP * pulse * _bump(y)          # 이 출력행이 원본 어디서 샘플할지
            ys = int(round(y - d))
            if 0 <= ys < H:
                for x in range(W):
                    wpx[x, y] = src[x, ys]
        # 2) 아주 옅은 전체 둥가둥가(엉덩이 고정 스쿼시)
        if BODY_SQUISH > 0:
            sy = 1.0 - BODY_SQUISH * math.cos(ph)
            sx = 1.0 / math.sqrt(sy)
            content = warp.crop((bbox[0], bbox[1], bbox[2], bbox[3]))
            nw = max(1, round(cw * sx)); nh = max(1, round(ch * sy))
            sc = content.resize((nw, nh), Image.NEAREST)
            frame = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            frame.alpha_composite(sc, (round(cx - nw / 2.0), round(cb - nh)))
            out.append(frame)
        else:
            out.append(warp)
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
    print(f'원본 {im.size}, 프레임 {len(frames)}장')

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
