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


def build(sheet_path, name, ell_top=167, shift=39):
    frames = key_and_shrink(Image.open(sheet_path))
    back = Image.new('RGBA', (W * FRAMES, H), (0, 0, 0, 0))
    front = Image.new('RGBA', (W * FRAMES, H), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        # ★★지면 타원(갈색 고리)은 **버린다** — 대표 8-18: "저딴식으로 원이 들어가면
        #   안된다고, 무슨 훌라후프같잖아. 스킬 이펙트처럼 느껴지게 해야한다고."
        #   선으로 그린 원이 바닥에 있으면 그 순간 '고리 안에 서 있는 캐릭터'가 된다.
        #   원근은 **불꽃 두 띠의 높이 차이**만으로 만든다(먼 쪽은 위, 가까운 쪽은 아래).
        flame = f.crop((0, 0, W, ell_top))          # 타원 윗선 위 = 불꽃만
        b = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        b.paste(flame, (0, 0), flame)
        back.paste(b, (i * W, 0))
        # 같은 불꽃을 타원 단축만큼 내리면 가까운 쪽 호에서 자란 불꽃이 된다.
        # 새로 그리는 게 아니라 내리는 것이라 **높이가 저절로 같다.**
        cell = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        cell.paste(flame, (0, shift), flame)
        front.paste(cell, (i * W, 0))
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
          int(sys.argv[4]) if len(sys.argv) > 4 else 39)
