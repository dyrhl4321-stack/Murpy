# -*- coding: utf-8 -*-
"""월간 한정 오브젝트(char/rooms/s{YYMM}_*.png) 추출 파이프라인.

나노바나나 생성 → Photoroom 누끼 원본을 앱에 등록 가능한 방 오브젝트로 변환한다.

    python char/extract_season_item.py <원본.png> <출력이름> --w 158
    python char/extract_season_item.py <원본.png> <출력이름> --h 111
    python char/extract_season_item.py <원본.png> <출력이름> --w 108 --largest

단계
  1) 알파 노이즈 제거(a < ALPHA_FLOOR → 0). 누끼 잔여물 정리.
  2) --largest: 최대 연결 컴포넌트만 남김. 누끼 과정에서 생긴 유령 조각(초록 잔상 등) 제거용.
  3) content bbox로 크롭 — 여백이 남으면 앱의 (x,y) 배치 좌표가 실제 형태와 어긋난다.
  4) 프리멀티플라이드 알파로 LANCZOS 리샘플. 그냥 리샘플하면 투명 픽셀 밑의 RGB가
     섞여 들어와 테두리에 검은 띠(halo)가 생긴다.
  5) --w 또는 --h 중 하나만 주면 나머지는 원본 비율로 계산. 찌그러짐 방지.

주의: 저장된 PNG의 실제 크기가 index.html SEASON_ITEMS의 w/h와 반드시 일치해야 한다.
      축하 연출이 정수배 스케일을 계산할 때 이 값을 쓴다.
"""
import argparse
import os
import sys
from collections import deque

from PIL import Image

ALPHA_FLOOR = 8          # 이하 알파는 완전 투명 처리
ALPHA_SOLID = 128        # 컴포넌트 판정 기준
MIN_COMPONENT = 50       # 이보다 작은 조각은 컴포넌트로 세지 않음

ROOMS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rooms')


def clean_alpha(im):
    """희미한 알파 노이즈를 완전 투명으로."""
    r, g, b, a = im.split()
    a = a.point(lambda v: 0 if v < ALPHA_FLOOR else v)
    return Image.merge('RGBA', (r, g, b, a))


def largest_component(im):
    """최대 연결 컴포넌트만 남기고 나머지는 투명 처리."""
    w, h = im.size
    alpha = im.getchannel('A')
    data = alpha.tobytes()
    mask = bytearray(1 if data[i] >= ALPHA_SOLID else 0 for i in range(w * h))

    seen = bytearray(w * h)
    best = None
    best_n = 0
    for sy in range(h):
        row = sy * w
        for sx in range(w):
            i = row + sx
            if seen[i] or not mask[i]:
                continue
            q = deque([i])
            seen[i] = 1
            cells = []
            while q:
                p = q.popleft()
                cells.append(p)
                px, py = p % w, p // w
                for nx, ny in ((px+1, py), (px-1, py), (px, py+1), (px, py-1)):
                    if 0 <= nx < w and 0 <= ny < h:
                        j = ny * w + nx
                        if not seen[j] and mask[j]:
                            seen[j] = 1
                            q.append(j)
            if len(cells) > best_n:
                best_n = len(cells)
                best = cells

    if best is None:
        return im, 0, 0

    keep = bytearray(w * h)
    for p in best:
        keep[p] = 1
    # 유지 컴포넌트에 인접한 반투명 가장자리는 살린다 (안티에일리어싱 보존)
    new_a = bytearray(w * h)
    src_a = data
    for p in range(w * h):
        if keep[p]:
            new_a[p] = src_a[p]
        elif src_a[p]:
            px, py = p % w, p // w
            for nx, ny in ((px+1, py), (px-1, py), (px, py+1), (px, py-1)):
                if 0 <= nx < w and 0 <= ny < h and keep[ny * w + nx]:
                    new_a[p] = src_a[p]
                    break

    dropped = sum(1 for p in range(w * h) if src_a[p] >= ALPHA_SOLID and not keep[p])
    r, g, b, _ = im.split()
    out = Image.merge('RGBA', (r, g, b, Image.frombytes('L', (w, h), bytes(new_a))))
    return out, best_n, dropped


def solid_bbox(im, margin=3):
    """불투명(>=ALPHA_SOLID) 픽셀 기준 bbox + 여유.

    getbbox()는 알파 1짜리 잔여물까지 포함해 버려서, 누끼 찌꺼기가 조금만 남아도
    크롭 범위가 통째로 어긋난다(실측: 램프 320x959 -> 1362x1131). 실제 형태만
    잡고, 안티에일리어싱 가장자리를 위해 margin 픽셀만 여유를 둔다.
    """
    w, h = im.size
    a = im.getchannel('A').tobytes()
    x0, y0, x1, y1 = w, h, -1, -1
    for y in range(h):
        row = y * w
        for x in range(w):
            if a[row + x] >= ALPHA_SOLID:
                if x < x0: x0 = x
                if x > x1: x1 = x
                if y < y0: y0 = y
                if y > y1: y1 = y
    if x1 < 0:
        return None
    return (max(0, x0 - margin), max(0, y0 - margin),
            min(w, x1 + 1 + margin), min(h, y1 + 1 + margin))


def resize_premultiplied(im, tw, th):
    """프리멀티플라이드 알파 기준 LANCZOS 축소 — 테두리 halo 방지."""
    src = im.convert('RGBA')
    w, h = src.size
    px = src.load()

    pm = Image.new('RGBA', (w, h))
    pmx = pm.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            f = a / 255.0
            pmx[x, y] = (int(r * f + 0.5), int(g * f + 0.5), int(b * f + 0.5), a)

    pm = pm.resize((tw, th), Image.LANCZOS)
    out = Image.new('RGBA', (tw, th))
    ox = out.load()
    ix = pm.load()
    for y in range(th):
        for x in range(tw):
            r, g, b, a = ix[x, y]
            if a == 0:
                ox[x, y] = (0, 0, 0, 0)
            else:
                f = 255.0 / a
                ox[x, y] = (
                    min(255, int(r * f + 0.5)),
                    min(255, int(g * f + 0.5)),
                    min(255, int(b * f + 0.5)),
                    a,
                )
    return out


def pixelate(im, cell, colors):
    """픽셀 밀도를 방 가구(Pixel Interiors 4배)와 맞춘다.

    나노바나나 원본은 2400px급이라 그대로 줄이면 정보량이 팩 가구(24x46 원본)보다
    수십 배 많아 혼자 튄다. 아트 격자로 한 번 줄였다가 NEAREST로 되키워 '한 아트픽셀
    = cell 유닛'을 강제하고, 팔레트도 줄여 같은 화풍의 일원으로 만든다.
    최종 크기는 cell의 배수가 된다.
    """
    w, h = im.size
    aw, ah = max(1, round(w / cell)), max(1, round(h / cell))
    small = resize_premultiplied(im, aw, ah)

    # 알파 이진화 — 픽셀아트는 반투명 가장자리가 없다
    r, g, b, a = small.split()
    a = a.point(lambda v: 255 if v >= 128 else 0)

    # 불투명 영역만 팔레트 축소 (투명부 RGB가 팔레트를 오염시키지 않게)
    rgb = Image.merge('RGB', (r, g, b))
    q = rgb.quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.NONE).convert('RGB')
    small = Image.merge('RGBA', (*q.split(), a))

    return small.resize((aw * cell, ah * cell), Image.NEAREST)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('name', help='출력 파일명 (확장자 없이). 예: s2608_dumbbell')
    ap.add_argument('--w', type=int, help='목표 가로. 미지정 시 --h와 원본 비율로 계산')
    ap.add_argument('--h', type=int, help='목표 세로. 미지정 시 --w와 원본 비율로 계산')
    ap.add_argument('--largest', action='store_true',
                    help='최대 연결 컴포넌트만 남김 (유령 조각 제거)')
    ap.add_argument('--pixel', type=int, default=0, metavar='CELL',
                    help='아트픽셀 크기. 4를 주면 방 가구와 같은 밀도로 맞춤 (0=원본 유지)')
    ap.add_argument('--colors', type=int, default=24, help='--pixel 사용 시 팔레트 색 수')
    ap.add_argument('--out', default=ROOMS, help='출력 폴더 (기본: char/rooms)')
    args = ap.parse_args()

    if not args.w and not args.h:
        sys.exit('--w 또는 --h 중 하나는 필요합니다')

    im = Image.open(args.src).convert('RGBA')
    print(f'원본: {im.size}')

    im = clean_alpha(im)

    if args.largest:
        im, kept, dropped = largest_component(im)
        print(f'최대 컴포넌트 유지: {kept}px, 제거된 조각: {dropped}px')

    bbox = solid_bbox(im)
    if not bbox:
        sys.exit('내용이 없습니다')
    im = im.crop(bbox)
    cw, ch = im.size
    print(f'크롭: {bbox} -> {cw}x{ch} (비율 {cw/ch:.4f})')

    if args.w and args.h:
        tw, th = args.w, args.h
        want = args.w / args.h
        got = cw / ch
        if abs(want - got) / got > 0.02:
            print(f'  경고: 지정 비율 {want:.4f}가 원본 {got:.4f}와 달라 찌그러집니다')
    elif args.w:
        tw = args.w
        th = max(1, round(args.w * ch / cw))
    else:
        th = args.h
        tw = max(1, round(args.h * cw / ch))

    out = resize_premultiplied(im, tw, th)
    if args.pixel:
        out = pixelate(out, args.pixel, args.colors)
        tw, th = out.size
        print(f'픽셀화: 아트격자 {tw//args.pixel}x{th//args.pixel} (1아트픽셀={args.pixel}유닛), 팔레트 {args.colors}색')

    os.makedirs(args.out, exist_ok=True)
    dst = os.path.join(args.out, args.name + '.png')
    out.save(dst)
    print(f'저장: {dst}  {tw}x{th}')
    print(f'  → index.html SEASON_ITEMS에 w:{tw}, h:{th} 로 등록할 것')


if __name__ == '__main__':
    main()
