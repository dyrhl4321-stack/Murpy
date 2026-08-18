# 필드 아우라 생성기 — 캐릭터를 감싸는 불길 (BACK/FRONT 두 겹)
#
# ★왜 코드로 그리나 (2026-08-18)
#   프롬프트로 네 번 뽑았는데 매번 같은 데서 실패했다:
#     ① 앞/뒤 분리가 안 된다 — "상상 속 타원의 뒤쪽 절반"은 공간 개념이라 모델이 못 잡는다.
#        대표: "그냥 존나 중구난방하게 앞뒤 다 깔려서 나옴"
#     ② 6프레임이 이어지지 않는다 — 모델은 6장을 따로 그린다. 루프가 안 맞는다.
#     ③ 바닥에 선으로 된 원을 그려서 훌라후프가 된다
#     ④ 프레임마다 실루엣이 널뛴다 · 안티에일리어싱이 섞인다
#   전부 코드로는 애초에 안 생기는 문제다. 앞/뒤는 밑동의 y 로 가르면 **정의상** 갈리고,
#   루프는 위상을 2*pi*i/N 으로 돌리면 **정의상** 이어진다.
#
# ★출력
#   char/fx/aura_<name>_back.png   846x224 (141x224 6프레임 가로 스트립)
#   char/fx/aura_<name>_front.png  같은 규격
#   앱에서 BACK -> 캐릭터 -> FRONT 순으로 겹친다.
#   재생은 CSS 스프라이트 steps(6) — APNG 두 개로 돌리면 앞뒤 프레임이 어긋난다.
#
# 쓰는 법:  python char/gen_aura.py

import math, os
from PIL import Image

W, H, FRAMES = 141, 224, 6          # 캐릭터 셀과 같은 규격
OUT = os.path.join(os.path.dirname(__file__), 'fx')

# ★캐릭터 실측(walk.png col0 row0): 전체 실루엣 x 9~129, y 10~220.
#   발끝이 y=220 이므로 지면은 그 언저리다. 팔까지 치면 폭이 121 이라
#   아우라가 121 안쪽에 있으면 상체에 가려진다 → 타원을 프레임 폭 가까이 넓게 잡는다.
GROUND_Y = 214
RX, RY = 66, 12                      # 지면 타원(그리지는 않는다, 밑동 배치용)
CX = 70

PALETTE = {
    'fire': [(255, 233, 168), (245, 194, 75), (138, 74, 18)],   # 파리한 금 / 골드 / 딥앰버
    'ice':  [(255, 255, 255), (168, 212, 255), (61, 126, 255)],  # 흰 / 옅은 시안 / 액션블루
    'void': [(255, 255, 255), (180, 139, 255), (90, 50, 160)],   # 흰 / 히든보라 / 짙은 보라
}


def flames(n=13):
    """밑동을 지면 타원 위에 놓는다. sin>0 이면 시청자 쪽(앞)이다.

    ★n 을 22 까지 올렸더니 갈대밭이 됐다. 불은 **가닥이 적고 굵어야** 읽힌다.
    """
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n + 0.21          # 0.21 = 정면 정중앙에 하나가 딱 오는 걸 피한다
        bx = CX + RX * math.cos(t)
        by = GROUND_Y + RY * math.sin(t)
        # ★원근을 만드는 유일한 장치 = 밑동의 y 와 불꽃 높이.
        #   바닥에 선을 그으면 훌라후프가 된다(대표 지적) → 선은 절대 안 그린다.
        #   양옆(|cos| 큰 곳)은 길게, 가운데는 짧게. 가운데가 제일 멀기 때문이다.
        h = 40 + 30 * abs(math.cos(t))
        # 가닥마다 높이·굵기를 다르게 — 다 같으면 그게 갈대밭이다
        jig = 0.78 + 0.44 * ((i * 7) % 5) / 4.0
        out.append((bx, by, h * jig, t, math.sin(t) >= 0, 6.0 + 3.0 * jig))
    return out


def draw_flame(px, bx, by, h, t, phase, cols, base_w):
    """불꽃 한 '혀'. 선이 아니라 **면**으로 채운다.

    ★2차 생성에서 배운 것: 같은 굵기의 가닥을 여럿 세우면 불길이 아니라 **갈대밭**이 된다.
      불로 읽히려면 (1) 밑이 넓고 끝이 뾰족한 혀 모양 (2) 가닥마다 높이가 다르고
      (3) 프레임마다 높이가 흔들려야 한다. 셋 다 아래에서 만든다.
    """
    pale, gold, amber = cols
    # 프레임별 깜빡임. phase 로만 흔들어야 6프레임이 한 바퀴로 딱 맞아떨어진다.
    flick = 0.82 + 0.18 * math.sin(phase + t * 2.3)
    h = h * flick
    steps = max(3, int(h))
    for s in range(steps):
        f = s / (steps - 1)                            # 0=밑동 1=끝
        # 폭: 밑이 넓고 위로 갈수록 좁아진다(끝은 1px). 이게 '혀' 실루엣을 만든다.
        w = max(1.0, base_w * (1.0 - f) ** 0.62)
        # 흔들림: 위로 갈수록 크게, 가닥마다 다른 위상
        sway = math.sin(phase + t * 1.7 + f * 2.6) * (0.8 + 5.0 * f)
        cx = bx + sway
        y = int(round(by - f * h))
        if not (0 <= y < H):
            continue
        x0, x1 = int(round(cx - w / 2)), int(round(cx + w / 2))
        for x in range(x0, x1 + 1):
            if not (0 <= x < W):
                continue
            edge = (x == x0 or x == x1)
            # 가장자리=앰버 윤곽 / 속=골드 / 밑동 속=파리한 금(제일 뜨거운 자리)
            if edge and w >= 2.5:
                col = amber
            elif f < 0.34 and w >= 3.5:
                col = pale
            else:
                col = gold
            px[x, y] = col + (255,)


def build(name='fire', n=13):
    cols = PALETTE[name]
    back = Image.new('RGBA', (W * FRAMES, H), (0, 0, 0, 0))
    front = Image.new('RGBA', (W * FRAMES, H), (0, 0, 0, 0))
    fl = flames(n)
    for i in range(FRAMES):
        # ★루프가 이어지는 이유: 위상이 한 바퀴를 정확히 FRAMES 등분한다.
        phase = 2 * math.pi * i / FRAMES
        fb = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ff = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        pb, pf = fb.load(), ff.load()
        for (bx, by, h, t, is_front, bw) in fl:
            if is_front:
                # 앞 불꽃은 짧게 — 정강이까지만. 얼굴을 덮으면 꾸민 캐릭터가 죽는다.
                draw_flame(pf, bx, by, h * 0.62, t, phase, cols, bw)
            else:
                draw_flame(pb, bx, by, h, t, phase, cols, bw)
        back.paste(fb, (i * W, 0))
        front.paste(ff, (i * W, 0))
    os.makedirs(OUT, exist_ok=True)
    back.save(os.path.join(OUT, 'aura_%s_back.png' % name))
    front.save(os.path.join(OUT, 'aura_%s_front.png' % name))
    return back, front


if __name__ == '__main__':
    for nm in PALETTE:
        build(nm)
        print('wrote aura_%s_back/front.png' % nm)
