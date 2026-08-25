# -*- coding: utf-8 -*-
"""아기 공룡 펫 시트를 만든다 — 둥가둥가(대기) + 4방향 걷기.

    python char/build_dino_walk.py                 # 기본(측면 절충 = 대표 확정)
    python char/build_dino_walk.py --side-mode head
    python char/build_dino_walk.py --variants      # 미리보기용 3종 동시 출력

출력: char/rooms/s2608_dino_pet.png
      행 0 = 대기(둥가둥가) 8프레임 / 행 1~4 = 걷기 앞·좌·뒤·우 각 3프레임
      (행 순서는 산 펫 팩 Top-Down-Pet-Pack 과 같은 앞·좌·뒤·우 규칙)

원본은 저장소 밖 대표 작업 폴더에 있다:
    Desktop/머피브랜딩/머피월드 캐릭터/커스터마이징 3차/펫움직임구현/
    공룡걸음걸이 정면.png · 공룡걸음걸이 뒷면.png · 공룡 걸음걸이 측면.png

★여기서 데인 것들 (다시 만난다)

1. 배경 초록이 시트마다 다르다. 정면·뒷면은 순수 초록(초록기 200+)인데 **측면만 연두**
   (116,239,70 = 초록기 123)다. nukki.py 기본 임계값 120 으로는 아슬아슬하게 걸려서
   측면은 90 으로 낮춰 잡는다. 공룡 몸의 초록기는 20~60 이라 여유가 충분하다.

2. **제미나이 워터마크(반짝이)가 세 시트 전부 우하단에 있다.** 초록 위에 살짝 밝은 초록이라
   눈으로는 거의 안 보인다. 정면·뒷면 것은 초록기가 높아 배경으로 함께 지워지고,
   측면 것은 756px 짜리 독립 덩어리로 남는다 → **최대 덩어리의 10% 미만은 버린다**로 걸러진다.
   ★새 시트를 받으면 프레임 수가 3개인지 반드시 확인할 것. 4개면 워터마크가 섞인 것이다.

3. **프레임마다 캐릭터 크기가 다르다.** bbox 높이로 맞추면 다리를 뻗은 프레임이 작아져
   걸을 때마다 캐릭터가 커졌다 작아졌다 한다. → **머리 폭**으로 정규화한다. 자세가 바뀌어도
   머리 크기는 안 변하는 게 맞다. 머리 폭 = 콘텐츠 상단 42% 안에서 가장 넓은 줄.

4. **측면만 몸이 5~9% 길다.** 머리 폭을 맞추면 정면·뒷면은 높이 104(기존 앉은 공룡과 일치)
   인데 측면은 110~113 이 된다. 꼬리가 처져서가 아니다 — 바닥에 닿은 건 두 발이 맞고
   (실측: x 27~50%, 65~91%) 몸 자체가 길게 그려졌다. 그래서 측면에만 보정 배율을 건다.
     --side-mode mid    : 절충 — **대표 확정(8-24)**. 키·머리 오차를 반씩 나눈다
     --side-mode height : 정면과 키를 맞춘다. 머리가 8% 작아진다
     --side-mode head   : 머리를 맞춘다. 대신 옆을 보면 몸이 9px 커진다

5. **가로 정렬은 bbox 중심이 아니라 발 중심**이다. 측면은 꼬리가 한쪽으로 뻗어서 bbox 중심을
   쓰면 몸이 타일 밖으로 밀린다. 앱이 캐릭터를 '발끝을 타일 바닥 중앙에' 놓는 것과 같은 규칙.

6. 축소는 **프리멀티플라이드 LANCZOS**. 그냥 줄이면 투명 픽셀 밑 RGB 가 섞여 테두리에
   검은 띠가 생긴다(extract_season_item.py 와 같은 이유).

7. ★**기존 공룡은 일부러 저퀄 픽셀화를 거친 물건이다**(대표 지적). 그냥 매끈하게 줄이면
   같은 캐릭터인데 결이 달라서 앉은 것과 걷는 것이 딴 그림처럼 보인다. 그래서
   `extract_season_item.py --pixel 2` 와 **똑같은 처리**를 태운다:
   아트격자(1아트픽셀=2유닛)로 줄였다가 NEAREST 로 되키우고 알파를 이진화한다.
   실측: 앉은 공룡 = 고유색 22개, 알파 0/255 뿐, 색마다 픽셀 수가 4의 배수(=2x2 격자).

8. ★팔레트는 **새로 뽑지 않고 앉은 공룡 것을 그대로 쓴다.** 프레임마다 quantize 하면
   팔레트가 조금씩 달라져 걸을 때 색이 깜빡인다. 게다가 원본 시트끼리도 밝기가 다르다
   (실측 평균밝기: 정면 157 / 뒷면 148 / 측면 143). 같은 팔레트로 스냅하면
   "앉았다 걸으면 어두워진다"가 원천적으로 사라진다.
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOMS = os.path.join(HERE, 'rooms')
SRCDIR = os.path.join(os.path.expanduser('~'), 'Desktop', '머피브랜딩', '머피월드 캐릭터',
                      '커스터마이징 3차', '펫움직임구현')

IDLE_APNG = os.path.join(ROOMS, 's2608_dino.png')      # 둥가둥가 8프레임 (animate_dino.py 산출물)
SITTING = os.path.join(ROOMS, 's2608_dino_still.png')  # 크기 기준 = 이미 앱에 있는 공룡

# 원본 시트와 초록기 임계값 (위 주석 1번)
SHEETS = {
    'front': ('공룡걸음걸이 정면.png', 120),
    'back':  ('공룡걸음걸이 뒷면.png', 120),
    'side':  ('공룡 걸음걸이 측면.png', 90),
}
HEAD_TOP = 0.42          # 머리 판정 = 콘텐츠 상단 이 비율
MIN_PART = 0.10          # 최대 덩어리의 이 비율 미만은 버린다(워터마크 제거)
FLOOR_BAND = 0.94        # 발 중심 계산용 바닥 밴드(아래에서 6%)
PAD = 2                  # 셀 여백
# 테두리 색 — 앉은 공룡 실루엣 한 겹의 실측 최빈색(63%가 이 계열 남색)
OUTLINE = np.array([11, 34, 52], np.uint8)
ALPHA_T = 96             # 알파 이진화 문턱. 128 이면 원본 테두리가 깎인다


def key_frames(path, thr):
    """초록 배경을 지우고 프레임(연결 덩어리)들을 왼쪽부터 돌려준다."""
    im = Image.open(path).convert('RGBA')
    a = np.asarray(im).astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    bg = (g > 120) & ((g - np.maximum(r, b)) > thr)      # 초록기 = G - max(R,B)
    lab, n = ndimage.label(~bg)
    if not n:
        raise SystemExit('전경을 못 찾았습니다: ' + path)
    sizes = np.array(ndimage.sum(~bg, lab, range(1, n + 1)))
    boxes = ndimage.find_objects(lab)
    keep = sorted([i for i in range(n) if sizes[i] > sizes.max() * MIN_PART],
                  key=lambda i: boxes[i][1].start)

    arr = np.asarray(im).copy()
    arr[..., 3] = np.where(bg, 0, 255)

    # ★초록 번짐 제거(despill). 남기는 픽셀 중 **투명과 맞닿은 한 겹**은 배경 초록이 섞여 있다.
    #   그대로 두면 테두리에 초록 물이 든 채 팔레트로 스냅돼 색이 튄다 = "테두리가 이상하고
    #   전체적으로 퀄리티가 떨어진다"(대표 지적 8-24, 측면에서 특히 심했다).
    #   측면 시트는 배경 초록기가 123 이고 몸이 최대 60 이라 간격이 좁아 번짐이 더 넓게 남는다.
    #   char/nukki.py 와 같은 방식 — 가장자리에서 G 를 max(R,B) 근처로 눌러 초록기를 없앤다.
    solid_mask = ~bg          # ★keep 이라는 이름을 쓰지 말 것 — 아래에서 프레임 목록 이름이다
    edge = np.zeros_like(bg)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy or dx:
                edge |= solid_mask & np.roll(np.roll(bg, dy, 0), dx, 1)
    cap = np.maximum(arr[..., 0].astype(np.int16), arr[..., 2].astype(np.int16)) + 12
    hit = edge & (arr[..., 1].astype(np.int16) > cap)
    g2 = arr[..., 1].astype(np.int16)
    g2[hit] = cap[hit]
    arr[..., 1] = np.clip(g2, 0, 255).astype(np.uint8)

    keyed = Image.fromarray(arr)

    out = []
    for i in keep:
        sl = boxes[i]
        crop = keyed.crop((sl[1].start, sl[0].start, sl[1].stop, sl[0].stop))
        # 이 덩어리만 남긴다 — 옆 프레임 꼬리가 상자에 걸쳐 있을 수 있다
        m = Image.fromarray(((lab[sl] == (i + 1)) * 255).astype(np.uint8))
        crop.putalpha(Image.composite(crop.getchannel('A'), Image.new('L', crop.size, 0), m))
        out.append(crop)
    return out


def head_width(im):
    """머리 폭 = 콘텐츠 상단 HEAD_TOP 안에서 가장 넓은 줄. 자세가 바뀌어도 안 변한다."""
    a = np.asarray(im.convert('RGBA'))[..., 3] > 100
    rows = np.where(a.any(1))[0]
    y0, y1 = rows[0], rows[-1]
    best = 0
    for y in range(y0, y0 + int((y1 - y0) * HEAD_TOP) + 1):
        xs = np.where(a[y])[0]
        if len(xs):
            best = max(best, xs[-1] - xs[0] + 1)
    return best


def foot_center(im):
    """바닥에 닿은 부분의 가로 중심. 꼬리가 뻗은 쪽으로 몸이 밀리지 않게 하는 기준."""
    a = np.asarray(im.convert('RGBA'))[..., 3] > 100
    band = a[int(a.shape[0] * FLOOR_BAND):, :]
    xs = np.where(band.any(0))[0]
    if not len(xs):
        return im.width / 2.0
    return (xs[0] + xs[-1] + 1) / 2.0


def head_center(im):
    """머리 한가운데의 x.

    ★가로 정렬을 이걸로 바꿔 봤다가 되돌렸다(8-24). 발 중심일 때 머리 흔들림이 5px 였는데
      머리 중심으로 맞추니 8px 로 더 나빠졌다 — 셀 높이가 프레임마다 달라 머리 밴드가
      다른 자리를 재기 때문이다. 남겨 두는 건 다음에 또 시도하지 않기 위해서다.

    ★발 중심으로 맞추면 컷마다 머리가 좌우로 흔들린다(실측 5px). 걷는 그림은 다리가 움직이니
      발 위치가 컷마다 다른 게 당연한데, 그걸 기준으로 삼으면 그 흔들림이 몸통·머리로 옮겨간다.
      걷기는 **머리가 제자리에 있고 다리가 움직여야** 맞다.
    """
    a = np.asarray(im.convert('RGBA'))[..., 3] > 100
    rows = np.where(a.any(1))[0]
    y0, y1 = rows[0], rows[-1]
    band = a[y0:y0 + int((y1 - y0) * HEAD_TOP) + 1]
    xs = np.where(band.any(0))[0]
    if not len(xs):
        return im.width / 2.0
    return (xs[0] + xs[-1] + 1) / 2.0


def scale_to(im, factor):
    """프리멀티플라이드 LANCZOS 축소 (검은 테두리 방지)."""
    return resize_to(im, max(1, int(round(im.width * factor))),
                     max(1, int(round(im.height * factor))))


def resize_to(im, w, h):
    a = np.asarray(im.convert('RGBA')).astype(np.float32)
    al = a[..., 3:4] / 255.0
    pm = np.concatenate([a[..., :3] * al, a[..., 3:4]], -1).astype(np.uint8)
    sm = np.asarray(Image.fromarray(pm).resize((w, h), Image.LANCZOS)).astype(np.float32)
    al2 = np.clip(sm[..., 3:4] / 255.0, 1e-4, 1.0)
    rgb = np.clip(sm[..., :3] / al2, 0, 255)
    return Image.fromarray(np.concatenate([rgb, sm[..., 3:4]], -1).astype(np.uint8))


MERGE_D = 30             # 이 거리 안의 색은 같은 색으로 본다


def ref_palette():
    """앉은 공룡의 팔레트 — **비슷한 색을 합쳐서** 돌려준다.

    ★원본 22색을 그대로 쓰면 걸을 때 화면이 필름처럼 떨린다(대표 지적).
      걷기 3컷은 각각 따로 생성된 그림이라 음영이 미세하게 다른데, 22색이 너무 촘촘해서
      그 미세한 차이가 컷마다 **다른 색으로 갈린다**(실측: 겹치는 자리의 53~64%가 컷마다 바뀜).
      실제로 22색 중 (144,218,169)·(144,219,170)·(145,219,170)·(149,222,171) 처럼
      눈으로 구분이 안 되는 것이 여럿이다. 합치면 그 차이가 같은 색으로 내려앉는다.
    """
    a = np.asarray(Image.open(SITTING).convert('RGBA'))
    px = a[..., :3][a[..., 3] >= 128].reshape(-1, 3)
    cols, cnt = np.unique(px, axis=0, return_counts=True)
    order = np.argsort(-cnt)                       # 많이 쓰인 색이 대표가 된다
    keep = []
    for i in order:
        c = cols[i].astype(np.int32)
        if all(((c - k) ** 2).sum() > MERGE_D * MERGE_D for k in keep):
            keep.append(c)
    return np.array(keep, np.int16)


def pixelate(im, cell, pal, outline=OUTLINE):
    """저퀄 픽셀화 — extract_season_item.py --pixel 과 같은 처리 + 팔레트 고정 + 테두리 복원.

    아트격자로 줄였다가 NEAREST 로 되키운다(1아트픽셀 = cell 유닛).
    알파는 이진화하고(픽셀아트엔 반투명 가장자리가 없다), 색은 기준 팔레트로 스냅한다.
    """
    aw = max(1, int(round(im.width / cell)))
    ah = max(1, int(round(im.height / cell)))
    small = np.asarray(resize_to(im, aw, ah)).astype(np.int32)

    # 각 픽셀을 가장 가까운 기준색으로. 프레임마다 팔레트를 새로 뽑으면 색이 깜빡인다.
    # ★int32 로 올려서 뺀다 — int16 이면 차이의 제곱(최대 65025)이 넘쳐 음수가 되고
    #   argmin 이 엉뚱한 색을 고른다(배가 까매지고 테두리가 밝아졌다).
    d = ((small[..., None, :3] - pal[None, None, :, :].astype(np.int32)) ** 2).sum(-1)
    rgb = pal[d.argmin(-1)].astype(np.uint8)

    # ★테두리는 **덧그리지 않는다**. 예전엔 실루엣을 한 칸 넓혀 테두리 색으로 칠했는데,
    #   원본 테두리가 살아남은 자리에는 두 겹이 되어 걸을 때만 선이 확 두꺼워졌다(대표 지적).
    #   대신 알파 문턱을 낮춰 **원본의 검은 테두리가 그대로 살아남게** 한다. 축소 과정에서
    #   테두리가 투명과 섞여 알파가 떨어지는데, 128 로 자르면 그 겹이 통째로 깎였다.
    alpha = np.where(small[..., 3] >= ALPHA_T, 255, 0).astype(np.uint8)

    out = Image.fromarray(np.dstack([rgb, alpha]))
    return out.resize((aw * cell, ah * cell), Image.NEAREST)


LOCK_TOP = 0.52          # 콘텐츠 상단 이 비율까지가 '얼굴' — 컷마다 새로 그리지 않는다


def lock_head(frames):
    """한 방향의 모든 컷에 **첫 컷의 얼굴을 그대로 붙인다**.

    ★걷는데 얼굴이 컷마다 38~49% 바뀌고 있었다(실측). 다리는 움직이니 바뀌는 게 맞지만
      얼굴은 바뀔 이유가 없다 — AI 가 컷마다 조금씩 다르게 그린 것이고, 그게 재생하면
      옛날 필름처럼 점이 섞여 보인다(대표 지적 8-24).
    이 저장소가 이미 쓰는 규칙과 같다 — animate_dino.py 는 아예 "얼굴은 절대 리샘플하지 않고
    정수픽셀 이동만 한다"고 못박아 뒀다(눈 크기가 프레임마다 달라졌던 사고 때문).

    붙이는 자리는 **그 컷 자신의 얼굴 위치**다(가로 중심 + 위끝). 얼굴이 살짝 오르내리는
    것은 걷는 느낌이라 살리고, 그림이 바뀌는 것만 없앤다.
    """
    if len(frames) < 2:
        return frames

    def head_box(im):
        a = np.asarray(im.convert('RGBA'))[..., 3] > 100
        rows = np.where(a.any(1))[0]
        y0, y1 = rows[0], rows[-1]
        hy = y0 + int((y1 - y0) * LOCK_TOP)
        xs = np.where(a[y0:hy + 1].any(0))[0]
        return int(xs[0]), int(y0), int(xs[-1]) + 1, int(hy) + 1

    b0 = head_box(frames[0])
    head = frames[0].crop(b0)
    out = [frames[0]]
    for f in frames[1:]:
        b = head_box(f)
        cx = (b[0] + b[2]) / 2.0
        x = int(round(cx - head.width / 2.0))
        y = b[1]
        g = f.copy()
        # 원래 얼굴을 지우고(그 자리 알파를 비우고) 첫 컷 얼굴을 올린다.
        # 지우지 않으면 두 얼굴의 테두리가 겹쳐 선이 두 겹이 된다.
        blank = Image.new('RGBA', (b[2] - b[0], b[3] - b[1]), (0, 0, 0, 0))
        g.paste(blank, (b[0], b[1]))
        g.alpha_composite(head, (max(0, x), max(0, y)))
        out.append(g)
    return out


def temporal_mode(frames):
    """한 방향 3컷의 색을 **다수결로 모은다**.

    ★걷는데 머리 색이 컷마다 38~49% 바뀌고 있었다(실측). 다리는 실제로 움직이니 바뀌는 게
      맞지만 머리는 바뀔 이유가 없다 — AI 가 컷마다 얼굴을 조금씩 다르게 그린 것이다.
      그대로 두면 옛날 필름처럼 점이 섞여 보인다(대표 지적 8-24).
    세 컷 모두 불투명한 자리에서 **둘 이상이 같은 색이면 그 색으로 통일**한다.
    셋 다 다르면 원래 색을 둔다(진짜로 움직이는 부분이다).
    이 저장소가 이미 쓰던 규칙과 같은 방향이다 — animate_dino.py 는 아예 얼굴을 리샘플하지 않는다.
    """
    if len(frames) < 3:
        return frames
    h = min(f.height for f in frames)
    w = min(f.width for f in frames)
    arr = [np.asarray(f.convert('RGBA'))[:h, :w].copy() for f in frames]
    solid = np.ones((h, w), bool)
    for a in arr:
        solid &= a[..., 3] >= 128
    same01 = (arr[0][..., :3] == arr[1][..., :3]).all(-1)
    same12 = (arr[1][..., :3] == arr[2][..., :3]).all(-1)
    same02 = (arr[0][..., :3] == arr[2][..., :3]).all(-1)
    for i, pair in enumerate([(same12, 1), (same02, 0), (same01, 0)]):
        agree, src = pair
        m = solid & agree                       # 나머지 둘이 합의한 자리
        arr[i][..., :3][m] = arr[src][..., :3][m]
    return [Image.fromarray(a) for a in arr]


def idle_frames():
    """기존 둥가둥가 APNG 8프레임. 그림은 안 건드린다."""
    im = Image.open(IDLE_APNG)
    n = getattr(im, 'n_frames', 1)
    out = []
    for i in range(n):
        im.seek(i)
        out.append(im.convert('RGBA'))
    return out


def build(side_mode, pixel=2):
    ref_head = head_width(Image.open(SITTING))          # 기준 머리 폭 = 앱에 이미 있는 공룡
    print('기준(앉은 공룡) 머리 폭 %dpx' % ref_head)

    # 1) 방향별로 프레임을 뽑아 머리 폭으로 정규화한다
    norm = {}
    for key, (name, thr) in SHEETS.items():
        frames = key_frames(os.path.join(SRCDIR, name), thr)
        if len(frames) != 3:
            raise SystemExit('%s 프레임이 %d개입니다(3개여야 함). 워터마크가 섞였는지 확인하세요.'
                             % (key, len(frames)))
        # ★배율은 **방향마다 하나**다. 프레임마다 따로 계산하면 배율이 미세하게 달라(0.0970 vs
        #   0.0963) 축소할 때 픽셀 격자가 프레임마다 다른 자리에 떨어진다. 그러면 몸 안쪽 무늬가
        #   컷마다 기어다녀서 **옛날 필름처럼 점이 섞여 보인다**(대표 지적 8-24).
        #   프레임 간 색 변화 실측: 프레임별 배율 38~50% -> 방향별 한 배율 로 내려간다.
        hw = sorted(head_width(f) for f in frames)[len(frames) // 2]      # 머리 폭 중앙값
        fac = ref_head / hw
        scaled = [scale_to(f, fac) for f in frames]
        print('  %-5s 배율 %.4f (머리폭 중앙값 %d) -> 높이 %s'
              % (key, fac, hw, [f.height for f in scaled]))
        norm[key] = scaled

    # 2) 측면 보정 (주석 4번)
    ref_h = sorted(f.height for f in norm['front'])[1]
    side_h = sorted(f.height for f in norm['side'])[1]
    fix = {'height': ref_h / side_h,
           'mid': (ref_h / side_h + 1.0) / 2.0,
           'head': 1.0}[side_mode]
    print('측면 보정(--side-mode %s) = %.4f  (정면 중앙값 %d / 측면 중앙값 %d)'
          % (side_mode, fix, ref_h, side_h))
    if abs(fix - 1.0) > 1e-6:
        norm['side'] = [scale_to(f, fix) for f in norm['side']]

    # 2.5) 저퀄 픽셀화 + 팔레트 고정 (주석 7·8번)
    # 대기(둥가둥가)는 이미 이 처리를 거친 물건이라 손대지 않는다.
    if pixel:
        pal = ref_palette()
        print('팔레트 %d색을 앉은 공룡에서 가져와 걷기에 강제한다 (아트픽셀 %d)' % (len(pal), pixel))
        for k in norm:
            # 얼굴 고정 -> 저퀄 픽셀화 -> 남은 잔떨림 다수결. 순서를 바꾸지 말 것 —
            # 얼굴은 원해상도에서 붙여야 이음매에 계단이 안 생긴다.
            # ★측면(좌·우)에는 얼굴 고정을 안 건다. 옆모습은 컷마다 목 각도가 달라서
            #   첫 컷 얼굴을 붙이면 목에 베이지색 가로선이 생겨 **목이 잘린 것처럼 보인다**
            #   (대표 지적 8-24). 정면·뒷면은 목이 정면이라 이음매가 안 보인다.
            locked = lock_head(norm[k]) if k != 'side' else norm[k]
            norm[k] = temporal_mode([pixelate(f, pixel, pal) for f in locked])

    # 3) 행 구성 — 앞·좌·뒤·우. 좌향은 측면을 좌우반전(대표 지시)
    rows = [
        ('idle',  idle_frames()),
        ('front', norm['front']),
        ('left',  [f.transpose(Image.FLIP_LEFT_RIGHT) for f in norm['side']]),
        ('back',  norm['back']),
        ('right', norm['side']),
    ]

    # 4) 셀 크기 — 발 중심 기준이라 좌우로 필요한 폭이 다르다. 가장 큰 쪽에 맞춘다.
    left_need = right_need = top_need = 0
    for _, frames in rows:
        for f in frames:
            fc = foot_center(f)
            left_need = max(left_need, fc)
            right_need = max(right_need, f.width - fc)
            top_need = max(top_need, f.height)
    cw = int(np.ceil(max(left_need, right_need))) * 2 + PAD * 2
    ch = int(np.ceil(top_need)) + PAD
    cols = max(len(f) for _, f in rows)
    print('셀 %dx%d · %d행 x %d열' % (cw, ch, len(rows), cols))

    sheet = Image.new('RGBA', (cw * cols, ch * len(rows)), (0, 0, 0, 0))
    for ri, (name, frames) in enumerate(rows):
        for ci, f in enumerate(frames):
            x = ci * cw + int(round(cw / 2.0 - foot_center(f)))   # 발 중심을 셀 중앙에
            y = ri * ch + (ch - f.height)                         # 발을 셀 바닥에
            sheet.alpha_composite(f, (x, y))
    return sheet, cw, ch, cols, [n for n, _ in rows], [len(f) for _, f in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--side-mode', default='mid', choices=['height', 'mid', 'head'],
                    help='측면 보정 방식 (대표 확정: mid = 절충)')
    ap.add_argument('--pixel', type=int, default=2,
                    help='아트픽셀 크기(기존 공룡과 같은 저퀄 픽셀화). 0=끔')
    ap.add_argument('--variants', action='store_true', help='미리보기용 3종을 함께 출력')
    a = ap.parse_args()

    modes = ['height', 'mid', 'head'] if a.variants else [a.side_mode]
    for m in modes:
        sheet, cw, ch, cols, names, counts = build(m, a.pixel)
        suffix = '' if (m == a.side_mode and not a.variants) else '_' + m
        if a.variants:
            suffix = '_' + m
        out = os.path.join(ROOMS, 's2608_dino_pet%s.png' % suffix)
        sheet.save(out)
        print('%s  (%dx%d)' % (out, sheet.width, sheet.height))
        print('   행: %s / 프레임 수: %s\n' % (', '.join(names), counts))


if __name__ == '__main__':
    main()
