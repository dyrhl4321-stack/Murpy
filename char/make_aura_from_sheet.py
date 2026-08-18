# 아우라 앞/뒤 두 겹 만들기 — **뒷면 한 장에서** 둘 다 뽑는다
#
# ★핵심 (2026-08-18, 여러 번 헤맨 끝에 나온 결론)
#   앞면을 AI 로 따로 뽑으면 안 된다. 매번 뒷면과 높이·모양·색이 어긋난다
#   (대표: "앞면이 저렇게 불꽃이 낮으면 안된다고, 뒷면이랑 똑같아야한다고").
#   기하학적으로 **앞 불꽃은 같은 링의 가까운 쪽**이다. 즉 뒷면의 불꽃을
#   타원 단축(SHIFT)만큼 아래로 내린 것이 곧 앞면이다. 그래서 높이가 저절로 같다.
#
# ★앞뒤가 아니라 위아래로 나뉘는 이유
#   지면 타원의 **윗호**에서 자란 불꽃 = 멀다 = 캐릭터 뒤
#   **아랫호**에서 자란 불꽃 = 가깝다 = 캐릭터 앞
#   한 장에 윗호 불꽃만 있으면, 그걸 단축만큼 내려서 아랫호 불꽃을 만든다.
#
# ★앱에서 겹치는 순서:  BACK -> 캐릭터 -> FRONT
#   재생은 CSS 스프라이트 steps(6). APNG 두 개로 돌리면 앞뒤 프레임이 어긋난다.
#
# 쓰는 법:
#   python char/make_aura_from_sheet.py <뒷면.png> <이름> [ELL_TOP] [SHIFT]
# 예:
#   python char/make_aura_from_sheet.py "...\뒷면.png" fire 167 39

import sys, os
from PIL import Image

W, H, FRAMES = 141, 224, 6
OUT = os.path.join(os.path.dirname(__file__), 'fx')

# 앱 팔레트로 스냅한다 — AI 가 뱉은 중간색·반투명 가장자리를 그대로 두면
# 정수배로 확대할 때 지저분해진다(NEAREST 라 뭉개지지 않고 그대로 보인다).
PALETTE = [(255, 233, 168), (245, 194, 75), (255, 160, 40), (138, 74, 18)]


def key_and_shrink(src):
    """형광초록 빼고 → 셀 크기로 줄이고 → 알파 이진화 + 팔레트 스냅."""
    sw, sh = src.size
    fw = sw // FRAMES
    out = []
    for i in range(FRAMES):
        f = src.crop((i * fw, 0, (i + 1) * fw, sh)).convert('RGBA')
        p = f.load()
        for y in range(sh):
            for x in range(fw):
                r, g, b, a = p[x, y]
                # 초록이 확실히 우세한 픽셀만 뺀다(불꽃의 노랑을 지키려고 여유를 둔다)
                if g > 150 and r < 160 and b < 130 and g - max(r, b) > 50:
                    p[x, y] = (0, 0, 0, 0)
        f = f.resize((W, H), Image.BOX)          # 면적평균 — NEAREST 는 얇은 불꽃을 떨군다
        p = f.load()
        for y in range(H):
            for x in range(W):
                r, g, b, a = p[x, y]
                if a < 90:
                    p[x, y] = (0, 0, 0, 0)
                else:
                    c = min(PALETTE, key=lambda c: (c[0]-r)**2 + (c[1]-g)**2 + (c[2]-b)**2)
                    p[x, y] = c + (255,)
        out.append(f)
    return out


def build(sheet_path, name, ell_top=176, shift=54, rx=68, front_len=62):
    frames = key_and_shrink(Image.open(sheet_path))
    back = Image.new('RGBA', (W * FRAMES, H), (0, 0, 0, 0))
    front = Image.new('RGBA', (W * FRAMES, H), (0, 0, 0, 0))
    # ★★지면 타원(갈색 고리)은 **버린다** — 대표 8-18: "저딴식으로 원이 들어가면
    #   안된다고, 무슨 훌라후프같잖아. 스킬 이펙트처럼 느껴지게 해야한다고."
    #   선으로 그린 원이 바닥에 있으면 그 순간 '고리 안에 서 있는 캐릭터'가 된다.
    #
    # ★★★그렇다고 **수평선으로 자르면 안 된다** (대표 8-18, 두 번째 지적):
    #   "밑부분을 저렇게 수평으로 자르는 게 아니라, 캐릭터 발바닥 주변을 두르는
    #    원형으로 하단부가 나와야 하잖아."
    #   맞다. 밑동이 일직선이면 불꽃이 벽처럼 서고 발을 두르지 않는다.
    #   → 열(x)마다 **타원 곡선의 y** 로 자른다. 그러면 밑동이 발을 도는 곡선이 된다.
    #
    # ★내리는 양도 고정이면 안 된다. 먼 호와 가까운 호의 간격은
    #   가운데가 제일 넓고(2*ry) 양끝에서 0 으로 만난다. 그래서 열마다 다르게 내린다.
    ry = shift / 2.0                  # shift = 두 호 사이 최대 간격 = 단축(2*ry)
    cx, cy = W / 2.0 - 2, ell_top + ry
    for i, f in enumerate(frames):
        src = f.load()
        fb = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ff = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        pb, pf = fb.load(), ff.load()
        for x in range(W):
            u = (x - cx) / float(rx)
            if abs(u) > 1.0:
                continue                      # 타원 밖 열은 불꽃이 설 자리가 없다
            k = (1.0 - u * u) ** 0.5
            y_far = int(round(cy - ry * k))    # 먼 호 (뒤) — 여기가 뒷불의 밑동
            gap = int(round(2 * ry * k))       # 두 호 사이 간격: 가운데 최대, 양끝 0
            # 이 열에서 불꽃이 시작되는 꼭대기
            ytop = None
            for y in range(H):
                if src[x, y][3] != 0 and y <= y_far:
                    ytop = y
                    break
            if ytop is None:
                continue
            span = max(1, y_far - ytop)
            # ★FRONT 는 **내리는 게 아니라 늘린다** (대표 8-18 세 번째 지적:
            #   "앞에 있는 몇 불꽃은 캐릭터의 정강이 부분 뒤로 오히려 숨어진다").
            #   통째로 내리면 꼭대기까지 같이 내려가 앞 불꽃이 **짧아진다.**
            #   가까운 쪽은 원래 더 커 보여야 한다 → 꼭대기는 두고 밑동만 가까운 호까지
            #   끌어내려 세로로 늘린다. 그래야 발 앞에서 시작해 정강이를 타고 오른다.
            # ★앞 불꽃의 **최종 길이를 직접 못 박는다.**
            #   원본 쪽에만 상한을 걸었더니 늘린 뒤 다시 길어져 목까지 올라왔다.
            #   밑동은 가까운 호(=발바닥)에 붙이고, 거기서 front_len 만큼만 위로 올린다.
            y_near = y_far + gap                       # 가까운 호 = 앞 불꽃의 밑동
            k2 = front_len / float(span)
            for y in range(H):
                p = src[x, y]
                if p[3] == 0 or y > y_far:     # 곡선 아래(=타원 안쪽)는 버린다
                    continue
                pb[x, y] = p                   # BACK: 곡선 위 불꽃 그대로
                y2 = int(round(y_near - (y_far - y) * k2))
                if 0 <= y2 < H:
                    pf[x, y2] = p
                    # 늘리면 픽셀 사이가 벌어진다 — 아래 한 칸을 같이 채워 끊김을 막는다
                    if k2 > 1.15 and y2 + 1 < H and pf[x, y2 + 1][3] == 0:
                        pf[x, y2 + 1] = p
        back.paste(fb, (i * W, 0))
        front.paste(ff, (i * W, 0))
    os.makedirs(OUT, exist_ok=True)
    back.save(os.path.join(OUT, 'aura_%s_back.png' % name))
    front.save(os.path.join(OUT, 'aura_%s_front.png' % name))
    print('wrote char/fx/aura_%s_back.png / _front.png' % name)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__ or 'usage: make_aura_from_sheet.py <sheet.png> <name> [ELL_TOP] [SHIFT]')
        sys.exit(1)
    build(sys.argv[1], sys.argv[2],
          int(sys.argv[3]) if len(sys.argv) > 3 else 167,
          int(sys.argv[4]) if len(sys.argv) > 4 else 39,
          int(sys.argv[5]) if len(sys.argv) > 5 else 68,
          int(sys.argv[6]) if len(sys.argv) > 6 else 62)
