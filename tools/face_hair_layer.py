# -*- coding: utf-8 -*-
"""얼굴 커마 시트에서 머리카락만 뽑아 **헤어 레이어**를 만든다.

    python tools/face_hair_layer.py --id paesuhyun            # char/faces/paesuhyun.png → char/faces/paesuhyun_hair.png
    python tools/face_hair_layer.py --id kim --preview        # 검수용 3분할(원본|헤어|나머지) 도 저장

★왜 있나 (2026-09-06, 대표 폰 검수)
  커마는 머리카락이 몸통 시트에 **구워져** 있어 맨 밑 레이어에 깔린다. 앱은 헤어를 상의 **위**에
  그리므로(_CHAR_LAYER_ORDER: body < top < hair) 긴 머리가 상의에 덮여 —
    · ART 링거티 뒷모습에서 왼쪽 머리가 프레임마다 나타났다 사라졌다 하고
    · 레드 후디는 목 틈으로 밑의 노란 머리가 비쳤다.
  머리 픽셀만 따로 뽑아 헤어 레이어(hairOverlay)로 **한 번 더** 그리면 상의 위로 머리가 내려온다.
  몸통 시트는 그대로 둔다(머리를 두 번 그려도 같은 픽셀이라 무해).

★판정 = 색. 얼굴·살·속옷과 갈라야 한다.
  노란 머리 (247,232,147): G−B≈85, R−B≈100, |R−G|≈15
  살       (213,180,155): G−B≈25  ← G−B 가 갈라준다
  목걸이(주황)           : R−G 가 크다 ← |R−G| 상한이 갈라준다
  머리색이 다른 사람은 --hue 로 조건을 바꾼다(아래 PRESET). 흑발은 별도 규칙이 필요하다.
★30px 미만 조각은 버린다 — 머리는 셀마다 큰 덩어리다. 발 하이라이트 같은 잡티가 걸린다.
★외곽선(어두운 픽셀)은 머리에 붙은 1px 만 딸려온다 — 상의 위에서 머리 테두리가 살아야 한다.
"""
import os, sys, argparse
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, label
sys.stdout.reconfigure(encoding='utf-8')

M = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PRESET = {
    # 이름: (r,g,b,al) → bool 마스크
    'blonde': lambda r, g, b, al: (al > 0) & (g - b > 45) & (r - b > 60) & (g >= 100) & (np.abs(r - g) < 35),
}

def extract(src, out, hue='blonde', min_px=30, preview=None):
    S = Image.open(src).convert('RGBA'); a = np.array(S).astype(int)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    hair = PRESET[hue](r, g, b, al)
    lab, n = label(hair, structure=np.ones((3, 3)))
    sizes = np.bincount(lab.ravel()); keep = sizes >= min_px; keep[0] = False
    hair = keep[lab]
    outline = (al > 0) & (np.maximum(np.maximum(r, g), b) < 90)
    m = hair | (outline & binary_dilation(hair, iterations=1))
    o = np.zeros_like(a); o[m] = a[m]
    H = Image.fromarray(o.astype('uint8'), 'RGBA'); H.save(out)
    print('헤어 레이어 %s — 조각 %d→%d, 머리 %dpx(+외곽선 %dpx)' % (out, n, int(keep.sum()), int(hair.sum()), int(m.sum() - hair.sum())))
    if preview:
        rest = a.copy(); rest[m] = 0
        p = Image.new('RGBA', (S.width * 3, S.height), (40, 40, 48, 255))
        p.alpha_composite(S, (0, 0)); p.alpha_composite(H, (S.width, 0))
        p.alpha_composite(Image.fromarray(rest.astype('uint8'), 'RGBA'), (S.width * 2, 0))
        p.resize((p.width * 2, p.height * 2), Image.NEAREST).save(preview)
        print('미리보기', preview)
    return out

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', required=True)
    ap.add_argument('--hue', default='blonde', choices=list(PRESET))
    ap.add_argument('--min-px', type=int, default=30)
    ap.add_argument('--preview', action='store_true')
    a = ap.parse_args()
    src = os.path.join(M, 'char', 'faces', a.id + '.png')
    out = os.path.join(M, 'char', 'faces', a.id + '_hair.png')
    extract(src, out, a.hue, a.min_px, os.path.join(M, 'char', 'faces', a.id + '_hair_preview.png') if a.preview else None)
