# 발밑 아우라 고리 — 외부 에셋(itch.io aura pack)을 우리 규격으로 자른다
#
# ★왜 이 방식인가 (2026-08-18)
#   앞서 AI 로 불길 아우라를 만들려다 여덟 번 갈아엎고 폐기했다. 캐릭터와 **겹치는**
#   이펙트라 앞/뒤를 갈라야 했고, 두 겹을 맞물리게 하는 게 매번 어긋났다.
#   이 에셋은 **고리**라서 그 문제가 없다 — 가로로 반 자르면 위=뒤, 아래=앞이다. 끝.
#
# ★규격
#   원본: 96x96 6프레임 가로 스트립, 알파 투명(누끼 불필요). 고리 실측 bbox = 31x28
#   우리 캐릭터는 셀 141x224 에 실루엣 폭 121 → 고리를 가로 4배(124)로 키워야 맞는다
#   세로는 2배만(56) — 4배로 키우면 고리가 세로로 서서 훌라후프처럼 보인다(대표 지적).
#   가로4 세로2 = 바닥에 납작하게 누운 고리로 읽힌다. 대표 확정 2026-08-18.
#
# ★출력  char/fx/aurring_<색>_back.png / _front.png
#   각 744x28 (124x28 6프레임). 겹치는 순서 BACK -> 캐릭터 -> FRONT.
#   재생은 CSS steps(6) 한 벌로 두 레이어를 같이 돌린다(APNG 두 개면 서로 어긋난다).
#
# 쓰는 법:
#   python char/make_aura_ring.py "<aura_effect_3_blue.png>" blue

import sys, os
from PIL import Image

FRAMES = 6
SRC_CELL = 96
BB = (33, 33, 64, 61)        # 고리 실측 bbox (31x28) — 팩 안에서 모든 색이 같은 자리다
SX, SY = 4, 2                # 가로 4배 / 세로 2배 (대표 확정)
OUT = os.path.join(os.path.dirname(__file__), 'fx')


def build(sheet_path, name):
    a = Image.open(sheet_path).convert('RGBA')
    w = (BB[2] - BB[0]) * SX
    h = (BB[3] - BB[1]) * SY
    half = h // 2
    back = Image.new('RGBA', (w * FRAMES, half), (0, 0, 0, 0))
    front = Image.new('RGBA', (w * FRAMES, h - half), (0, 0, 0, 0))
    for i in range(FRAMES):
        fr = a.crop((i * SRC_CELL + BB[0], BB[1], i * SRC_CELL + BB[2], BB[3]))
        # ★NEAREST 정수배만 — 알파가 이미 이진에 가까워 보간하면 가장자리가 지저분해진다
        fr = fr.resize((w, h), Image.NEAREST)
        back.paste(fr.crop((0, 0, w, half)), (i * w, 0))
        front.paste(fr.crop((0, half, w, h)), (i * w, 0))
    os.makedirs(OUT, exist_ok=True)
    back.save(os.path.join(OUT, 'aurring_%s_back.png' % name))
    front.save(os.path.join(OUT, 'aurring_%s_front.png' % name))
    print('wrote char/fx/aurring_%s_back.png (%dx%d) / _front.png (%dx%d)'
          % (name, w * FRAMES, half, w * FRAMES, h - half))
    print('  프레임 %d개 · 한 칸 %dx%d' % (FRAMES, w, half))


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: make_aura_ring.py <aura_effect_N_<color>.png> <name>')
        sys.exit(1)
    build(sys.argv[1], sys.argv[2])
