# -*- coding: utf-8 -*-
"""AI 가 뽑은 마젠타 3x4 시트를 앱 규격(423x896 / 칸 141x224)으로 앉힌다.

    python char/fit_npc_sheet.py char/game/walk_sulle3.png char/game/walk_sulle.png

★왜 필요한가 (2026-09-02)
  제미나이는 3x4 구조와 톤은 잘 지키는데 **캔버스를 꽉 채운다.** 네 번 뽑는 동안
  네 번 다 맨 아랫줄 발이 캔버스 경계에 닿아 잘렸고, 여백을 달라고 명시해도 안 됐다.
  프롬프트로 밀 문제가 아니다 — 어차피 앱 규격으로 재배치해야 하니 여기서 정확히 앉힌다.

  하는 일: 마젠타 → 투명 / 12칸 각각의 캐릭터를 찾아서 / 레퍼런스(walk.png) 같은 줄의
  캐릭터 높이에 맞춰 NEAREST 로 줄이고 / 칸 안에 **바닥 정렬 + 가로 가운데**로 앉힌다.

★픽셀아트라 보간은 전부 NEAREST 다. LANCZOS 를 쓰면 도트가 뭉개진다.
★바닥 정렬이 핵심 — 캐릭터는 발밑이 기준이다. 가운데 정렬하면 걸을 때 위아래로 떤다.
"""
import io, os, sys
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

SRC = sys.argv[1] if len(sys.argv) > 1 else 'char/game/walk_sulle3.png'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'char/game/walk_sulle.png'
REF = 'char/walk.png'
CW, CH = 141, 224          # 앱 규격 한 칸
COLS, ROWS = 3, 4

# ── 레퍼런스에서 줄마다 캐릭터 높이·바닥선을 잰다 ───────────────────────────
ref = Image.open(REF).convert('RGBA')
tgt = []
for r in range(ROWS):
    hs, bots = [], []
    for c in range(COLS):
        bb = ref.crop((c * CW, r * CH, (c + 1) * CW, (r + 1) * CH)).getbbox()
        if bb:
            hs.append(bb[3] - bb[1])
            bots.append(bb[3])
    tgt.append((sum(hs) // len(hs), max(bots)))       # (높이, 칸 안 바닥 y)
    print('레퍼런스 %d행 — 캐릭터 높이 %d, 바닥 y %d' % (r + 1, tgt[r][0], tgt[r][1]))

# ── 원본에서 마젠타를 걷어낸다 ─────────────────────────────────────────────
src = Image.open(SRC).convert('RGBA')
SW, SH = src.size
px = src.load()
n = 0
for y in range(SH):
    for x in range(SW):
        r, g, b, a = px[x, y]
        # 마젠타 = R·B 가 높고 G 가 낮다. 살색(F4A97D)·남색(1E2A4A)·흰색 어디에도 없는 조합.
        if r > 150 and b > 150 and g < 120 and (r - g) > 60 and (b - g) > 60:
            px[x, y] = (0, 0, 0, 0)
            n += 1
print('마젠타 %d픽셀 제거 (전체의 %.0f%%)' % (n, 100.0 * n / (SW * SH)))

# ── 12칸을 각각 찾아 앱 규격 칸에 앉힌다 ───────────────────────────────────
sc_w, sc_h = SW // COLS, SH // ROWS
out = Image.new('RGBA', (CW * COLS, CH * ROWS), (0, 0, 0, 0))
clipped = []
for r in range(ROWS):
    th, tb = tgt[r]
    for c in range(COLS):
        cell = src.crop((c * sc_w, r * sc_h, (c + 1) * sc_w, (r + 1) * sc_h))
        bb = cell.getbbox()
        if not bb:
            print('  ★%d행%d열 비어 있음 — 건너뜀' % (r + 1, c + 1))
            continue
        # 원본에서 발이 칸 경계에 닿아 있으면 잘린 것이다. 지우지 않고 알려만 준다.
        if bb[3] >= sc_h:
            clipped.append('%d행%d열' % (r + 1, c + 1))
        art = cell.crop(bb)
        s = th / art.height                                    # 높이를 레퍼런스에 맞춘다
        w2, h2 = max(1, round(art.width * s)), max(1, round(art.height * s))
        art = art.resize((w2, h2), Image.NEAREST)              # ★픽셀아트 = NEAREST 고정
        x0 = c * CW + (CW - w2) // 2                           # 가로 가운데
        y0 = r * CH + tb - h2                                  # ★바닥 정렬
        out.alpha_composite(art, (x0, max(r * CH, y0)))

out.save(OUT)
print('저장 %s → %s' % (out.size, OUT))
if clipped:
    print('★원본에서 잘린 칸: ' + ', '.join(clipped))
    print('  (그 칸은 발끝 픽셀이 애초에 없다 — 다시 뽑아야 완전해진다)')

# ── 검증: 12칸이 다 찼고 바닥이 맞았나 ────────────────────────────────────
bad = 0
for r in range(ROWS):
    line = []
    for c in range(COLS):
        bb = out.crop((c * CW, r * CH, (c + 1) * CW, (r + 1) * CH)).getbbox()
        if not bb:
            line.append('빈칸'); bad += 1; continue
        line.append('h%d b%d' % (bb[3] - bb[1], bb[3]))
        if abs(bb[3] - tgt[r][1]) > 2:
            bad += 1
    print('%d행: %s   (레퍼런스 h%d b%d)' % (r + 1, ' | '.join(line), tgt[r][0], tgt[r][1]))
print('FIT-OK' if not bad else '★확인 필요 %d칸' % bad)
