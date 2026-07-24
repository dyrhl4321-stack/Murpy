# -*- coding: utf-8 -*-
"""아기 공룡에 '둥가둥가' 아이들 모션을 넣어 APNG로 저장한다.

    python char/animate_dino.py char/rooms/s2608_dino.png

왜 APNG인가 — 캠프파이어와 동일. 방 렌더(mwFurnHtml)가 <img>라 스프라이트시트+CSS를
쓰면 드래그가 깨진다. APNG는 파일만 갈면 된다. 저장 시 disposal=1, blend=0 필수.

모션(둥가둥가): 엉덩이(바닥)를 고정하고 배만 세로로 눌렀다 폈다 → 얼굴이 그 위에 얹혀
  통통 오르내린다. 배 위 두 손도 함께 움직여 '배 안고 둥가둥가'로 읽힌다.
  ★얼굴(눈·입이 있는 상단 HEAD_RATIO 영역)은 절대 리샘플하지 않는다 — 통째로 정수픽셀
    이동만 한다. 예전엔 스프라이트 전체를 매 프레임 리샘플(가로세로 스케일)해서, NEAREST
    반올림이 프레임마다 눈 픽셀을 다르게 스냅 → '오른쪽 눈이 커졌다 작아졌다' 했다(대표 지적
    2026-07-24). 가로 스케일이 좌우 눈을 비대칭으로 만든 게 특히 원인. 지금은 가로 스케일을
    없애고(세로만), 얼굴은 리지드로 이동해 눈이 매 프레임 픽셀 단위로 동일하다.
  ※재생성은 반드시 애니 이전 정적 원본에서(현재 png가 APNG면 0프레임만 읽힘).
    공룡의 정적 원본 = char/rooms/s2608_dino_still.png (도감 썸네일과 겸용, 바이트 동일).

★캔버스 여백(2026-07-24): 위로 오르는 프레임이 캔버스를 넘으면 뿔 끝이 잘려 '투명 벽에
  숨었다 나타났다' 한다. 그래서 최대 프레임 높이를 먼저 재고 그만큼 위에 투명 여백을 붙인다.
  바닥(엉덩이)은 캔버스 밑변에 붙여 접지선을 지킨다.
  → 캔버스가 바뀌므로 index.html SEASON_ITEMS의 w/h를 출력된 새 크기로 반드시 갱신할 것.
"""
import argparse
import math
from PIL import Image

FRAMES = 8
DURATION = 120       # 프레임당 ms
SQUISH = 0.022       # 배 세로 눌림 진폭(±2.2%). 배만 눌리므로 전신 스쿼시보다 체감은 절반쯤.
HEAD_RATIO = 0.60    # 콘텐츠 상단 이 비율(눈·입·얼굴)은 리지드 — 리샘플 금지. 아래(배)만 눌린다.
                     # 분할선 = round(ch*0.60) ≈ y62. 정적 원본에서 입은 ~y55, 그 아래는 배(크림).


def belly_heights(belly_h, frames):
    """프레임별 배 높이(px). 세로만 스케일 — 가로는 안 건드려 좌우 대칭·얼굴 무관."""
    out = []
    for f in range(frames):
        ph = 2 * math.pi * f / frames
        # cos: f=0에서 최대로 눌림(짧아짐) → 폈다(길어짐) 반복. 부드러운 순환.
        sy = 1.0 - SQUISH * math.cos(ph)
        out.append(max(1, round(belly_h * sy)))
    return out


def build_frames(im, frames=FRAMES):
    W, H = im.size
    bbox = im.getbbox()
    if not bbox:
        raise SystemExit('빈 이미지입니다')
    content = im.crop(bbox)
    cw, ch = content.size
    cx = (bbox[0] + bbox[2]) / 2.0      # 콘텐츠 가로중심
    cb = bbox[3]                        # 콘텐츠 바닥 y(고정점=엉덩이)

    head_h = max(1, round(ch * HEAD_RATIO))
    belly_h = ch - head_h
    head = content.crop((0, 0, cw, head_h))          # 눈·입 포함 상단 — 리샘플 안 함
    belly = content.crop((0, head_h, cw, ch))        # 배 하단 — 세로로만 눌림

    sizes = belly_heights(belly_h, frames)
    # 위 여백 = 가장 큰 프레임(머리+배 최대)이 바닥 위로 넘치는 만큼. 가로는 원폭 그대로.
    pad_t = max(0, (head_h + max(sizes)) - cb)
    NW, NH = W, H + pad_t
    cbn = cb + pad_t                     # 새 캔버스 기준 바닥(엉덩이 고정점)
    ox = round(cx - cw / 2.0)            # 원본 그대로면 0

    out = []
    for nbh in sizes:
        belly_sc = belly.resize((cw, nbh), Image.NEAREST)   # 세로만 · 픽셀 유지
        canvas = Image.new('RGBA', (NW, NH), (0, 0, 0, 0))
        oy_belly = cbn - nbh                      # 배 밑 = 엉덩이(고정)
        oy_head = oy_belly - head_h               # 머리는 배 위에 리지드로 얹혀 함께 오르내림
        canvas.alpha_composite(head, (ox, oy_head))
        canvas.alpha_composite(belly_sc, (ox, oy_belly))
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
    print(f'★출력 캔버스 {frames[0].size} — index.html SEASON_ITEMS의 w/h를 이 값으로 맞출 것')

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
