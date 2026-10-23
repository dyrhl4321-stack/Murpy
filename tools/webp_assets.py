# 큰 불투명 그림을 WebP 로 옆에 만들고 index.html 참조를 바꾼다(10-23 속도). 원본 PNG 는 남긴다(크루 화면 등 다른 곳이 쓴다).
#   품질은 그림마다 고른 값 — 픽셀별 최대 채널 오차 > 24 인 픽셀이 0.1% 미만인 가장 낮은 q(평균 PSNR 만 보면 픽셀 경계 번짐을 놓친다).
#   그 기준을 못 맞춘 그림은 무손실 WebP. 크게 확대해 보여 주는 오픈월드 맵(park2·walk·outgym)·worldmap 은 무손실이어도 15% 라 그대로.
#   사용: python tools/webp_assets.py            (WebP 만들기 + index.html 참조 바꾸기)
#         python tools/webp_assets.py --check    (검증만: 오차 다시 재기)
import os, io, re, sys
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PICK = {   # 경로: 품질(0 = 무손실)
    'char/fields/field_mugung_tall.png': 90, 'char/fields/field_tennis.png': 90, 'char/fields/field_running_wide.png': 90,
    'char/fields/field_gym_wide.png': 90, 'char/fields/field_golf.png': 90, 'char/fields/field_gym.png': 90,
    'char/fields/portal_anim.png': 90, 'char/game/tennis_title.png': 90, 'char/game/golf_title.png': 90,
    'char/game/run_title.png': 90, 'char/game/golf_grass.png': 90,
    'char/fields/field_running.png': 0, 'char/npc/npc_group.png': 0, 'char/fields/field_oxquiz_tall.png': 0,
    # 스쿼드 카드 종목·시간대 필드(squadFieldSrc 가 이름을 이어 붙여 만든다 — 여기 하나라도 빠지면 그 카드 배경이 빈다)
    'char/fields/field_climbing_wide.png': 90, 'char/fields/field_dance_wide.png': 90, 'char/fields/field_golf_wide.png': 90,
    'char/fields/field_hiking_pm_wide.png': 90, 'char/fields/field_hiking_wide.png': 90, 'char/fields/field_hyrox_wide.png': 90,
    'char/fields/field_running_am_wide.png': 90, 'char/fields/field_tennis_wide.png': 90, 'char/fields/field_yoga_wide.png': 90,
}
# 이 줄들은 손대지 않는다(크루 화면 — 개발 창 관리). 원본 PNG 가 그대로 있으니 그대로 동작한다.
SKIP_LINE = ('const _crewField',)

def bad_ratio(a, b):
    return (np.abs(a.astype(np.int16) - b.astype(np.int16)).max(axis=2) > 24).mean() * 100

def main():
    check = '--check' in sys.argv
    tot = [0, 0]
    for rel, q in PICK.items():
        src = os.path.join(ROOT, rel); dst = src[:-4] + '.webp'
        im0 = Image.open(src)
        # 투명 픽셀이 조금이라도 있으면 알파째로(알파는 무손실) — 없으면 RGB
        rgb = im0.convert('RGBA') if im0.convert('RGBA').getextrema()[3][0] < 255 else im0.convert('RGB')
        if not check:
            if q: rgb.save(dst, 'WEBP', quality=q, method=6, alpha_quality=100)
            else: rgb.save(dst, 'WEBP', lossless=True, quality=100, method=6)
        out = np.asarray(Image.open(dst).convert(rgb.mode)); a = np.asarray(rgb)
        br = bad_ratio(a, out)
        assert out.shape == a.shape, rel
        assert br < 0.1, (rel, br)
        if not q: assert (out == a).all(), rel
        s0, s1 = os.path.getsize(src), os.path.getsize(dst); tot[0] += s0; tot[1] += s1
        print('%6dKB -> %5dKB  %s  bad%%=%.3f  %s' % (s0 // 1024, s1 // 1024, 'q%d' % q if q else '무손실', br, rel))
    print('합계 %.1fMB -> %.1fMB' % (tot[0] / 1048576, tot[1] / 1048576))
    if check: return
    p = os.path.join(ROOT, 'index.html'); h = open(p, encoding='utf-8', newline='').read()
    lines = h.split('\n'); n = 0
    pat = re.compile(r"(%s)\.png(?=\?v=|['\"\)])" % '|'.join(re.escape(r[:-4]) for r in PICK))
    for i, ln in enumerate(lines):
        if any(s in ln for s in SKIP_LINE): continue
        new, k = pat.subn(r'\1.webp', ln)
        if k: lines[i] = new; n += k
    open(p, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print('index.html 참조 %d곳 바꿈' % n)

main()
