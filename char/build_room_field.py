# -*- coding: utf-8 -*-
"""머피룸 배경(char/fields/field_room.png) 생성.

    python char/build_room_field.py <PixelInteriors시트.png>
    python char/build_room_field.py <시트.png> --wall sage
    python char/build_room_field.py <시트.png> --wall-base 233,224,205 --wall-stripe 222,210,186

왜 코드로 그리는가
  보유한 두 에셋 팩(Pixel Interiors, sierrassets) 모두 **탑다운 방 프레임**이라
  벽을 정면으로 보는 우리 사선 시점과 원근이 맞지 않는다. 바닥 타일만 팩에서 쓰고
  벽은 코드로 만든다. 기존 field_workshop.png의 어색한 상단 띠도 같은 한계의 산물이었다.

기하 (768x768, 16타일 그리드이므로 1타일 = 48유닛)
  벽 3타일 = 144유닛. _FIELDS.home.map의 막힌 행 0~2와 정확히 일치해야
  캐릭터가 벽에 파묻히거나 허공에 뜨지 않는다.

    y   0.. 5   상단 몰딩       6유닛
    y   6..121  벽지          116유닛  (세로 스트라이프 12유닛 주기)
    y 122..126  걸레받이 윗립    5유닛
    y 127..143  걸레받이 몸통   17유닛   -> 걸레받이 합 22유닛
    y 144..767  바닥          624유닛  (마루 타일 4배 = 128유닛, 세로는 끝에서 잘림)

★바닥 배율 4배 (설계서의 2배를 실측으로 뒤집음)
  설계서는 "64유닛 = 실제 69cm"라는 치수 근거로 2배를 지정했으나, 앱은 768 원본을
  320px로 줄여 BILINEAR로 스무딩한다. 2배에서는 널 이음새 간격이 화면상 4px밖에
  안 돼 축소 과정에서 대각선 무아레가 생기고 마루가 아니라 마대자루처럼 보인다.
  3배는 벽돌결, 4배라야 나무 널로 읽힌다(비교본 10_바닥배율비교_2-3-4.png).
  4배여도 널 한 장이 약 23cm라 광폭 마루로 자연스럽고, Phase 2 가구도 4배라
  아트픽셀 크기(4유닛)가 방 전체에서 일치한다.

벽지 색은 파라미터로 분리해 두었다. 나중에 '벽지 바꾸기' 기능을 붙일 때
이 스크립트로 색만 바꿔 여러 장 뽑으면 된다.
"""
import argparse
import os

from PIL import Image

SIZE = 768               # 필드 한 변 (16타일 x 48유닛)
MOLDING_H = 6            # 상단 몰딩
WALL_H = 144             # 벽 전체 = 3타일. map의 막힌 행 수와 반드시 일치
BASEBOARD_H = 22         # 걸레받이 전체
BASEBOARD_LIP = 5        # 그중 윗립(밝은 쪽)
STRIPE_W = 12            # 벽지 세로 스트라이프 폭

FLOOR_TILE = (0, 64, 32, 96)   # Pixel Interiors 나무마루 타일
FLOOR_SCALE = 4                # 정수배만 (픽셀 아트 하드룰). 위 주석의 실측 근거 참고

TRIM = (150, 108, 74)          # 몰딩 / 걸레받이 윗립
TRIM_DARK = (120, 84, 56)      # 걸레받이 몸통

# 벽지 프리셋 (base, stripe). 대표 승인본은 cream.
WALLPAPERS = {
    'cream': ((233, 224, 205), (222, 210, 186)),
    'sage':  ((214, 224, 205), (199, 212, 186)),
    'blue':  ((205, 217, 233), (186, 201, 222)),
    'rose':  ((233, 212, 210), (222, 194, 192)),
}

CHAR_H = 158             # 캐릭터 키(3.3타일). 미리보기 기준선용


def parse_rgb(s):
    parts = [int(v) for v in s.split(',')]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError('R,G,B 형식이어야 합니다')
    return tuple(parts)


def build(sheet_path, base, stripe, floor_scale=FLOOR_SCALE):
    im = Image.new('RGB', (SIZE, SIZE))
    px = im.load()

    # --- 벽 ---
    for y in range(WALL_H):
        if y < MOLDING_H:
            row = [TRIM] * SIZE
        elif y >= WALL_H - BASEBOARD_H:
            row = [TRIM if y < WALL_H - BASEBOARD_H + BASEBOARD_LIP else TRIM_DARK] * SIZE
        else:
            # 세로 스트라이프. 폭이 12유닛인 이유: 방은 768 원본을 320px 남짓으로 축소해
            # 보여주므로(약 0.42배) 이보다 가늘면 축소 스무딩에 뭉개져 사라진다.
            row = [stripe if (x // STRIPE_W) % 2 else base for x in range(SIZE)]
        for x in range(SIZE):
            px[x, y] = row[x]

    # --- 바닥 ---
    sheet = Image.open(sheet_path).convert('RGB')
    tile = sheet.crop(FLOOR_TILE)
    tw, th = tile.size
    tile = tile.resize((tw * floor_scale, th * floor_scale), Image.NEAREST)
    tw, th = tile.size
    for ty in range(WALL_H, SIZE, th):
        for tx in range(0, SIZE, tw):
            im.paste(tile, (tx, ty))   # 오른쪽/아래로 넘치는 부분은 캔버스 밖으로 잘린다

    return im


def preview(field, out_path):
    """캐릭터 키(158유닛) 기준선을 얹은 확인용 이미지."""
    p = field.copy()
    d = p.load()
    y0 = SIZE - 120 - CHAR_H
    for y in range(y0, y0 + CHAR_H):
        for x in range(60, 64):
            d[x, y] = (255, 0, 255)
    for x in range(56, 68):
        d[x, y0] = (255, 0, 255)
        d[x, y0 + CHAR_H - 1] = (255, 0, 255)
    p.save(out_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sheet', help='Pixel Interiors 32x32pxl.png 경로')
    ap.add_argument('--wall', choices=sorted(WALLPAPERS), default='cream',
                    help='벽지 프리셋 (기본: cream — 대표 승인본)')
    ap.add_argument('--wall-base', type=parse_rgb, help='벽지 바탕색 R,G,B (프리셋 무시)')
    ap.add_argument('--wall-stripe', type=parse_rgb, help='벽지 줄무늬색 R,G,B (프리셋 무시)')
    ap.add_argument('--floor-scale', type=int, default=FLOOR_SCALE,
                    help='마루 타일 정수배 (기본 %d). 앱은 768을 320으로 줄여 스무딩하므로 '
                         '배율이 낮으면 널 이음새가 뭉개져 마루가 아니라 직물처럼 보인다' % FLOOR_SCALE)
    ap.add_argument('--out', default=None, help='출력 경로 (기본: char/fields/field_room.png)')
    ap.add_argument('--preview', default=None, help='캐릭터 기준선 얹은 확인용 이미지 경로')
    args = ap.parse_args()

    base, stripe = WALLPAPERS[args.wall]
    if args.wall_base: base = args.wall_base
    if args.wall_stripe: stripe = args.wall_stripe

    here = os.path.dirname(os.path.abspath(__file__))
    out = args.out or os.path.join(here, 'fields', 'field_room.png')

    field = build(args.sheet, base, stripe, args.floor_scale)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    field.save(out)
    print(f'저장: {out}  {field.size[0]}x{field.size[1]}')
    print(f'  벽 {WALL_H}유닛(3타일) / 걸레받이 {BASEBOARD_H} / 바닥 시작 y={WALL_H}')
    print(f'  벽지 바탕{base} 줄무늬{stripe} 폭{STRIPE_W}')
    print(f'  마루 {args.floor_scale}배 = 타일 {32 * args.floor_scale}유닛')

    if args.preview:
        preview(field, args.preview)
        print(f'미리보기: {args.preview} (자홍색 막대 = 캐릭터 키 {CHAR_H}유닛)')


if __name__ == '__main__':
    main()
