# 대숲 '저에요' 손 아이콘 만들기 (대표 제작본 → 앱용 PNG)
#
# 입력 : Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차\아이콘\대숲저에요.png
#        (나노바나나 산출물 — 형광초록 #00FF00 배경 + 흰색 라인아트)
# 출력 : char/ui/ic_me_green.png  (#4ADE80) — 목록 수치·상세·신청자 버튼용
#        char/ui/ic_me_dark.png   (#08210f) — 꽉 찬 초록 '저에요' 버튼 위에 얹는 용
#
# ★왜 두 색으로 뽑나: PNG 는 <img> 로 넣으면 currentColor 를 못 받는다.
#   쓰이는 배경이 두 가지(어두운 배경 / 초록 버튼)라 색마다 파일을 만든다.
#
# ★워터마크: 제미나이가 우하단에 ✦ 를 굽는다. 여기서 지운다.
#   [[feedback_ai_dot_sheet_props]] 계열 함정 — 워터마크 점검을 빼먹으면 앱에 그대로 올라간다.
import os
from PIL import Image

SRC = r'C:\Users\allys\Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차\아이콘\대숲저에요.png'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui')
SIZE = 96                      # 화면에선 14~18px. 레티나 대비 넉넉히 4배 이상으로 뽑는다.
PAD = 4                        # 잘라낸 뒤 사방 여백(출력 크기 기준)

im = Image.open(SRC).convert('RGB')
W, H = im.size
px = im.load()

# 1) 크로마키 — 초록기(g 가 r,b 보다 얼마나 큰가)로 알파를 만든다.
#    흰색은 g-max(r,b)=0 → 불투명, 순초록은 255 → 투명, 경계의 섞인 색은 그 중간.
#    RGB 는 통째로 목표색으로 갈아끼우므로 초록 번짐(despill)이 저절로 해결된다.
alpha = Image.new('L', (W, H), 0)
ap = alpha.load()
for y in range(H):
    for x in range(W):
        r, g, b = px[x, y]
        key = g - max(r, b)
        if key < 0:
            key = 0
        a = 255 - int(key * 255 / 200)      # 200 이상 초록이면 완전 투명
        ap[x, y] = 0 if a < 0 else (255 if a > 255 else a)

# 2) 워터마크 제거 — 우하단 구석. 손은 여기까지 오지 않는다.
wm = [int(W * 0.78), int(H * 0.76), W, H]
removed = 0
for y in range(wm[1], wm[3]):
    for x in range(wm[0], wm[2]):
        if ap[x, y] > 8:
            removed += 1
        ap[x, y] = 0
print('워터마크 영역에서 지운 픽셀: %d' % removed)

# 3) 남은 알파의 bbox 로 자른다(여백 균등하게 맞추려고)
bbox = alpha.getbbox()
if not bbox:
    raise SystemExit('알파가 비었습니다 — 크로마키 임계값을 확인하세요')
alpha = alpha.crop(bbox)
bw, bh = alpha.size
print('아이콘 bbox: %s (%dx%d)' % (str(bbox), bw, bh))

# 정사각 캔버스에 가운데 정렬 (손이 세로로 길어 세로 기준으로 맞춘다)
side = max(bw, bh)
sq = Image.new('L', (side, side), 0)
sq.paste(alpha, ((side - bw) // 2, (side - bh) // 2))

inner = SIZE - PAD * 2
sq = sq.resize((inner, inner), Image.LANCZOS)
canvas_a = Image.new('L', (SIZE, SIZE), 0)
canvas_a.paste(sq, (PAD, PAD))

os.makedirs(OUT_DIR, exist_ok=True)
for name, hexcol in (('ic_me_green', '#4ADE80'), ('ic_me_dark', '#08210f')):
    rgb = tuple(int(hexcol[i:i + 2], 16) for i in (1, 3, 5))
    out = Image.new('RGBA', (SIZE, SIZE), rgb + (0,))
    out.putalpha(canvas_a)
    p = os.path.join(OUT_DIR, name + '.png')
    out.save(p)
    print('저장: %s' % p)
