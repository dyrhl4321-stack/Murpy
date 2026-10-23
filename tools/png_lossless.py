# PNG 무손실 재압축(10-23 속도) — 파일 이름·픽셀 그대로, 안쪽 압축만 바꾼다. 코드 수정 없음.
#   후보: ① 색이 256개 이하면 정확한 팔레트 PNG(투명도는 tRNS) ② 아니면 같은 모드로 최대 압축. 둘 중 작은 것.
#   조건: 디코딩한 RGBA 바이트가 원본과 1비트도 다르지 않을 것, 10% 이상 작아질 것.
#   색 보정 정보(gAMA·iCCP·sRGB 등)가 있는 파일은 건너뛴다(브라우저가 색을 다르게 그릴 수 있다).
#   제외: 작업 폴더(work·_src 등)·파이프라인 원본(*_source.png)·홍보 그림(promo), 크루 그림(개발 창 관리).
#   사용: python tools/png_lossless.py [--dry]
import os, io, sys
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIRS = ['char', 'ob']
SKIP_DIRS = {'work', '_src', 'src', 'raw', 'orig', 'crews', 'promo'}
SKIP_NAMES = ('season_box', 'cz_', 'ui_ic_crew', 'crew_plaza', 'agit_')
MIN = 20 * 1024

def pal_png(rgba):
    a = np.asarray(rgba).reshape(-1, 4)
    u, inv = np.unique(a.view(np.uint32).ravel(), return_inverse=True)
    if len(u) > 256: return None
    cols = u.view(np.uint8).reshape(-1, 4)
    p = Image.fromarray(inv.astype(np.uint8).reshape(rgba.size[1], rgba.size[0]), 'P')
    p.putpalette(cols[:, :3].ravel().tolist() + [0] * (768 - 3 * len(cols)))
    kw = {}
    if (cols[:, 3] != 255).any(): kw['transparency'] = bytes(cols[:, 3].tolist())
    b = io.BytesIO(); p.save(b, 'PNG', optimize=True, **kw); return b.getvalue()

def same_mode_png(im):
    b = io.BytesIO(); im.save(b, 'PNG', optimize=True); return b.getvalue()

def main():
    dry = '--dry' in sys.argv
    tot = [0, 0, 0]; skipped_color = 0
    for d in DIRS:
        for dp, dn, fn in os.walk(os.path.join(ROOT, d)):
            dn[:] = [x for x in dn if x not in SKIP_DIRS]
            for f in fn:
                if not f.lower().endswith('.png') or f.startswith(SKIP_NAMES) or f.endswith('_source.png'): continue
                p = os.path.join(dp, f); sz = os.path.getsize(p)
                if sz < MIN: continue
                im = Image.open(p); im.load()
                if any(k in im.info for k in ('gamma', 'icc_profile', 'srgb', 'chromaticity')): skipped_color += 1; continue
                ref = im.convert('RGBA').tobytes()
                cands = [x for x in (pal_png(im.convert('RGBA')), same_mode_png(im) if im.mode in ('RGB', 'RGBA', 'L', 'LA', 'P') else None) if x]
                best = min(cands, key=len)
                if len(best) > sz * 0.9: continue
                if Image.open(io.BytesIO(best)).convert('RGBA').tobytes() != ref: print('!! 픽셀 다름, 건너뜀', p); continue
                tot[0] += sz; tot[1] += len(best); tot[2] += 1
                print('%6dKB -> %6dKB  %s' % (sz // 1024, len(best) // 1024, os.path.relpath(p, ROOT)))
                if not dry:
                    open(p, 'wb').write(best)
    print('%s %d개 %.1fMB -> %.1fMB (색 보정 정보 있어 건너뜀 %d개)' % ('예상' if dry else '바꿈', tot[2], tot[0] / 1048576, tot[1] / 1048576, skipped_color))

main()
