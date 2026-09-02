# -*- coding: utf-8 -*-
"""에셋 캔버스 채움률 검사 — "안 보인다" 사고를 등록 전에 잡는다.

    python tools/check_asset_fill.py                  # char/ 전체
    python tools/check_asset_fill.py char/game        # 폴더 지정
    python tools/check_asset_fill.py char/game/golf_mole.png   # 파일 하나

★왜 있나 (9-02 골프 두더지)
  golf_mole.png 이 캔버스 160x180 중 그림 58x37(가로 36%·세로 21%), 불투명 픽셀 1% 였다 —
  누끼가 갈색 몸통을 통째로 지운 것. CSS contain 은 투명 여백까지 칸에 맞추므로
  화면엔 10x7px 로 그려졌고, 대표는 두더지를 "한 번도 본 적이 없다"고 했다.
  정상 스프라이트는 캔버스를 91~100% 채운다. 한 줄 검사로 잡히는 사고였다.

판정
  ★깨짐   : 채움 가로·세로 어느 쪽이든 50% 미만, 또는 불투명 5% 미만
  ?의심    : 채움 50~70%, 또는 불투명 5~15%
  (raw/미리보기/시트 등 원본류는 건너뛴다 — *.raw.png, *_thumb.png 는 규칙이 다르다)
"""
import io, os, sys
from PIL import Image

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'char')

files = []
if os.path.isfile(target):
    files = [target]
else:
    for dp, dn, fn in os.walk(target):
        for f in fn:
            if f.lower().endswith('.png') and '.raw.' not in f and '_thumb' not in f:
                files.append(os.path.join(dp, f))

bad, warn, ok = [], [], 0
for p in sorted(files):
    try:
        im = Image.open(p).convert('RGBA')
    except Exception as e:
        bad.append((p, '열기 실패: %s' % e))
        continue
    w, h = im.size
    bb = im.getbbox()
    if not bb:
        bad.append((p, '완전히 비어 있음'))
        continue
    fx = (bb[2] - bb[0]) / w
    fy = (bb[3] - bb[1]) / h
    a = im.getchannel('A')
    hist = a.histogram()
    opaque = sum(hist[11:]) / (w * h)          # 알파 >10
    msg = '채움 %3.0f%%x%3.0f%% · 불투명 %3.0f%%' % (fx * 100, fy * 100, opaque * 100)
    # ★시트 종류별로 잣대가 다르다 (첫 전체검사에서 배운 것):
    #   items/ = 캐릭터 시트에 겹쳐 입히는 오버레이 — 반바지·신발·마스크는 원래 3~4%만 불투명하다.
    #   rooms/ = 배치 격자 맞춤 여백이 정상. → 이 둘은 "아예 비었나"만 본다.
    #   단독 스프라이트(game/fields/pets/ui 등)만 채움률 잣대를 적용한다.
    overlay = ('items' + os.sep) in p or ('rooms' + os.sep) in p
    if overlay:
        if opaque < 0.005:
            bad.append((p, msg + ' (오버레이인데 사실상 비어 있음)'))
        else:
            ok += 1
    elif fx < 0.5 or fy < 0.5 or opaque < 0.05:
        bad.append((p, msg))
    elif fx < 0.7 or fy < 0.7 or opaque < 0.15:
        warn.append((p, msg))
    else:
        ok += 1

rel = lambda p: os.path.relpath(p, os.path.join(HERE, '..'))
for p, m in bad:
    print('★깨짐  %-52s %s' % (rel(p), m))
for p, m in warn:
    print('?의심  %-52s %s' % (rel(p), m))
print('')
print('검사 %d개 — 정상 %d · 의심 %d · 깨짐 %d' % (len(files), ok, len(warn), len(bad)))
sys.exit(1 if bad else 0)
