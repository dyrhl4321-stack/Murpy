"""누끼 마무리 공통 단계 — 2026-09-08 대표: "누끼 딸 때 테두리에 마젠타/초록 배경이 조금씩 딸려 들어온다, 앞으로 이럴 일 없게".

모든 시트(NPC·엑스트라·커마·아이템)는 키잉 뒤 반드시 이걸 거친다:
  1) 알파 128 이진화 (반투명 가장자리 = 배경색이 섞인 픽셀)
  2) 실루엣 가장자리 2px 안의 픽셀 중 배경색끼(초록: g>r+35&g>b+35 / 마젠타·보라: r>g+10&b>g+10&어두움) → 무채색(밝기 유지)
  3) 남은 작은 조각(minpx 미만) 제거
  4) 검사: 가장자리 픽셀에 배경색끼가 남아 있으면 개수를 출력하고 종료코드 1 (배포 전 확인용)
사용: python tools/key_defringe.py <png> [--out <png>] [--bg green|magenta|both] [--minpx 200]
"""
import sys, argparse, numpy as np
from PIL import Image
from scipy import ndimage

def defringe(a, bg='both', minpx=200):
    a = a.astype(int); r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    out = a.copy(); out[..., 3] = np.where(al >= 128, 255, 0)
    op = out[..., 3] > 0
    edge = op & ~ndimage.binary_erosion(op, iterations=2)
    tint = np.zeros_like(op)
    if bg in ('green', 'both'): tint |= (g > r + 35) & (g > b + 35)
    if bg in ('magenta', 'both'): tint |= (r > g + 10) & (b > g + 10) & (r + g + b < 330)
    fr = edge & tint
    lum = (r + g + b) // 3
    out[fr, 0] = lum[fr]; out[fr, 1] = lum[fr]; out[fr, 2] = np.minimum(255, lum[fr] + 2)
    lab, n = ndimage.label(out[..., 3] > 0)
    if n > 1:
        sz = ndimage.sum(out[..., 3] > 0, lab, range(1, n + 1))
        out[..., 3] = np.where(np.isin(lab, [i + 1 for i, s in enumerate(sz) if s >= minpx]), out[..., 3], 0)
    return out.astype(np.uint8), int(fr.sum()), int(((al > 0) & (al < 128)).sum())

def check(a, bg='both'):
    a = a.astype(int); r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    op = al > 0; edge = op & ~ndimage.binary_erosion(op, iterations=2)
    bad = edge & (((g > r + 35) & (g > b + 35)) | ((r > g + 10) & (b > g + 10) & (r + g + b < 330)))
    return int(bad.sum()), int(((al > 0) & (al < 255)).sum())

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('png'); ap.add_argument('--out'); ap.add_argument('--bg', default='both'); ap.add_argument('--minpx', type=int, default=200); ap.add_argument('--check', action='store_true')
    o = ap.parse_args()
    a = np.array(Image.open(o.png).convert('RGBA'))
    if o.check:
        bad, semi = check(a, o.bg); print('%s: 가장자리 배경색끼 %d px, 반투명 %d px' % (o.png, bad, semi)); sys.exit(1 if (bad or semi) else 0)
    out, fr, semi = defringe(a, o.bg, o.minpx)
    Image.fromarray(out).save(o.out or o.png)
    bad, _ = check(out, o.bg)
    print('%s → %s: 가장자리 배경색끼 %d 정리, 반투명 %d 제거, 남은 배경색끼 %d' % (o.png, o.out or o.png, fr, semi, bad))
    sys.exit(1 if bad else 0)
