# 캐릭터 감정 아이콘(단발 UI 에셋) 만들기 — 마젠타 배경 AI 생성물 → 도트 PNG
#
# 쓰임새: 매칭 '오늘 추천을 다 봤어요' 같은 빈 화면에 올리는 머피 한 컷.
# 스프라이트 시트가 아니라 **UI 아이콘 한 장**이라 3x4 시트 규칙은 적용하지 않는다.
#
# 하는 일
#   1) 형광 마젠타 배경을 지운다(누끼)
#   2) 캐릭터만 남게 자른다
#   3) base 캐릭터 셀 높이(224)에 맞춰 **NEAREST** 로 내린다 — AI 생성물은 픽셀이 뭉개져 있어서
#      중심 샘플링으로 도트 격자를 되살린다
#   4) 알파를 128 에서 이진화(반투명 테두리 금지 — 앱 하드룰)
#   5) 지워진 마젠타가 번진 가장자리를 되살린다(despill): 분홍끼를 뺀다
#
# 사용:  python char/make_ui_emote.py <입력.png> <출력.png>
import sys, os
from PIL import Image

SRC = sys.argv[1] if len(sys.argv) > 1 else None
OUT = sys.argv[2] if len(sys.argv) > 2 else None
if not SRC or not OUT:
    print('사용: python char/make_ui_emote.py <입력.png> <출력.png>'); sys.exit(1)

TARGET_H = 224          # base 캐릭터 셀 높이와 같게

im = Image.open(SRC).convert('RGBA')
w, h = im.size
px = im.load()

def is_bg(c):
    r, g, b, a = c
    return a > 0 and r > 170 and b > 170 and g < 110      # 형광 마젠타 계열

# 1) 누끼 + 2) 경계 찾기
x0, y0, x1, y1 = w, h, -1, -1
for y in range(h):
    for x in range(w):
        c = px[x, y]
        if is_bg(c):
            px[x, y] = (0, 0, 0, 0)
        else:
            if x < x0: x0 = x
            if y < y0: y0 = y
            if x > x1: x1 = x
            if y > y1: y1 = y
if x1 < 0:
    print('내용을 못 찾았습니다(전부 배경?)'); sys.exit(1)
im = im.crop((x0, y0, x1 + 1, y1 + 1))
print('잘라낸 크기', im.size)

# 3) 도트 격자로 내리기 (중심 샘플링 = NEAREST)
ratio = im.width / im.height
tw = max(1, round(TARGET_H * ratio))
im = im.resize((tw, TARGET_H), Image.NEAREST)

# 4) 알파 이진화 + 5) despill (마젠타 잔상 제거)
im = im.convert('RGBA')
p = im.load()
for y in range(im.height):
    for x in range(im.width):
        r, g, b, a = p[x, y]
        if a < 128:
            p[x, y] = (0, 0, 0, 0); continue
        # 분홍끼: 초록이 유난히 낮으면 빨강·파랑을 초록 쪽으로 눌러 준다
        if r > g and b > g:
            m = (r + b) // 2
            if m - g > 40:
                r = min(r, g + (r - g) // 3)
                b = min(b, g + (b - g) // 3)
        p[x, y] = (r, g, b, 255)

os.makedirs(os.path.dirname(OUT) or '.', exist_ok=True)
im.save(OUT)
print('저장', OUT, im.size)
