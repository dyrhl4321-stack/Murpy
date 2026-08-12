# 나노바나나에 첨부할 **참조 이미지**를 리터치본에서 만든다.
#
# ★왜 리터치본이어야 하나(대표 8-12): 리터치를 거친 파일이 우리가 정한 '정답 형태'다.
#   (팔 살 튀어나온 것까지 정리된 상태) 그걸 참조로 줘야 새로 뽑는 컷도 같은 형태를 따라간다.
#   내가 레이어로 합성한 ref_murpy_front.png 는 옷만 입힌 기본 자세라 그 다음 단계가 아니다.
#
# 하는 일: 배포본(작은 도트)을 정수배 NEAREST 로 키우고 흰 배경에 얹는다.
#   AI 는 작은 이미지를 참조로 주면 디테일을 놓친다. 정수배라 도트는 안 뭉개진다.
#
# 사용:  python char/make_ref_from_emote.py char/ui/murpy_sad.png <출력.png> [배율]
import sys, os
from PIL import Image

SRC = sys.argv[1] if len(sys.argv) > 1 else r'char/ui/murpy_sad.png'
OUT = sys.argv[2] if len(sys.argv) > 2 else r'ref_from_emote.png'
SCALE = int(sys.argv[3]) if len(sys.argv) > 3 else 6

im = Image.open(SRC).convert('RGBA')
big = im.resize((im.width * SCALE, im.height * SCALE), Image.NEAREST)   # 정수배 NEAREST 만
pad = 60
canvas = Image.new('RGBA', (big.width + pad * 2, big.height + pad * 2), (255, 255, 255, 255))
canvas.alpha_composite(big, (pad, pad))
os.makedirs(os.path.dirname(OUT) or '.', exist_ok=True)
canvas.convert('RGB').save(OUT)
print('참조 이미지 저장:', OUT, canvas.size, '(원본 %dx%d 를 %d배)' % (im.width, im.height, SCALE))
