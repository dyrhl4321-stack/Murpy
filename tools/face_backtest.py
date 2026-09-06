# -*- coding: utf-8 -*-
"""얼굴 커스터마이징 백테스트 — 같은 셀카로 N번 생성해 **한 번에 잘 뽑히는 비율**과 실패 유형을 잰다.

    python tools/face_backtest.py --id hyunsu --gender 남 --selfies <셀카 폴더|파일> --n 3
    python tools/face_backtest.py --id hyunsu --gender 남 --raws <이미 생성된 원본 폴더>   # 생성 없이 채점만

★왜 있나 (대표 9-06): "한 번에 잘 뽑히려면 프롬프트·누끼·정합을 더 백테 돌려보자." 눈으로 한 장씩 보던 걸
  숫자로 바꾼다. 채점 항목(자동):
    cells     규격화가 base 앵커를 찾은 칸 수 (12 여야 정상 — 못 찾은 칸은 비어 나온다)
    dy/dx     칸마다 캐릭터 발끝 y·중심 x 가 base 와 몇 px 어긋나는지 (최대·평균). 2px 이내가 목표
    hratio    캐릭터 높이 / base 높이 (0.95~1.05 목표 — 벗어나면 머리 크기가 다른 것)
    semi/mag  잔상 수술 뒤 남은 반투명·마젠타 픽셀 (0 이어야)
    hair      헤어 레이어 픽셀 수 (긴 머리면 3만↑, 짧으면 작다 — 급변하면 머리 모양이 튄 것)
    bald      정면 칸 머리 위 영역에 머리색 픽셀이 거의 없으면 '빡빡이' 실패
  산출: Murpy_private/제작노하우/생성원본/backtest/<id>_<n>.png (원본) · 같은 폴더 <id>_<n>_ai.png (규격화)
        검수용 대조표 = 스크래치 또는 --out 폴더의 backtest_<id>.png (base | 시도1 | 시도2 …, 정면·뒤·옆 3칸)
"""
import os, sys, io, glob, json, argparse, time
import numpy as np
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from face_pipeline import load_cfg, gen, PRIV, M
from face_grid import regrid_cells, foreground
from face_hair_layer import extract as hair_extract

CW, CH = 141, 224

def cell_metrics(ai_path, base_path):
    A = np.array(Image.open(ai_path).convert('RGBA')); B = np.array(Image.open(base_path).convert('RGBA'))
    rows = []
    for r in range(4):
        for c in range(3):
            a = A[r*CH:(r+1)*CH, c*CW:(c+1)*CW, 3] > 128
            b = B[r*CH:(r+1)*CH, c*CW:(c+1)*CW, 3] > 128
            if a.sum() < 200:
                rows.append(None); continue
            ay, ax = np.where(a); by, bx = np.where(b)
            rows.append({'dy': int(ay.max() - by.max()), 'dx': int(round(ax.mean() - bx.mean())),
                         'h': (ay.max() - ay.min() + 1) / (by.max() - by.min() + 1)})
    return rows

def fringe_stats(path):
    a = np.array(Image.open(path).convert('RGBA')).astype(int); al = a[..., 3]; mx = a[..., :3].max(-1)
    semi = int(((al > 0) & (al < 255)).sum())
    mag = int(((al == 255) & (mx > 100) & (a[..., 0] > a[..., 1] + 40) & (a[..., 2] > a[..., 1] + 40)).sum())
    return semi, mag

def bald_check(ai_path):
    """정면 칸(1행1열) 머리 위쪽 띠(y 8~40)에 살색이 아닌 불투명 픽셀이 얼마나 있나 — 적으면 빡빡이/머리 누락."""
    a = np.array(Image.open(ai_path).convert('RGBA')).astype(int)[8:40, 30:111]
    op = a[..., 3] > 128
    # ★살색 = 주황이면서 G−B 가 작다(≈25). 금발 그늘(200,170,100)은 G−B≈70 이라 살로 세면 안 된다
    skin = (a[..., 0] > 150) & (a[..., 0] > a[..., 1] + 20) & (a[..., 1] > a[..., 2]) & (a[..., 1] - a[..., 2] < 45)
    return int((op & ~skin).sum())

def back_face_check(ai_path):
    """뒤 칸(2행1열) 머리 영역(y 30~110, x 40~100)에 살색 픽셀 — 뒤통수라면 거의 0. 많으면 **뒤 칸에 얼굴을 그린** 실패
    (9-06 백테스트 hyunsu2 가 정확히 이것 — 정합 채점은 OK 였다)."""
    a = np.array(Image.open(ai_path).convert('RGBA')).astype(int)[CH + 30:CH + 110, 40:100]
    skin = (a[..., 3] > 128) & (a[..., 0] > 150) & (a[..., 0] > a[..., 1] + 20) & (a[..., 1] > a[..., 2]) & (a[..., 1] - a[..., 2] < 45)
    return int(skin.sum())

def outfit_check(ai_path, base_path):
    """정면 칸 몸통 띠(y 128~170, x 50~92)의 평균색이 base 속옷과 얼마나 다른가 — 옷을 바꿔 그린 실패
    (hyunsu 1호가 흰 나시로 바뀜). 색거리 60 넘으면 의심."""
    Af = np.array(Image.open(ai_path).convert('RGBA')).astype(int); Bf = np.array(Image.open(base_path).convert('RGBA')).astype(int)
    worst = 0
    for (y0, y1) in ((128, 170), (168, 200)):          # 상의 띠 + 하의 띠(흰 바지 실전 사고, 9-07)
        A, B = Af[y0:y1, 50:92], Bf[y0:y1, 50:92]; ma, mb = A[..., 3] > 128, B[..., 3] > 128
        if ma.sum() < 50 or mb.sum() < 50: continue
        worst = max(worst, int(round(float(np.sqrt(((A[ma][:, :3].mean(0) - B[mb][:, :3].mean(0)) ** 2).sum())))))
    return worst

def score(ai_path, base_path, hair_path):
    cm = cell_metrics(ai_path, base_path)
    found = [m for m in cm if m]
    semi, mag = fringe_stats(ai_path)
    hair_px = int((np.array(Image.open(hair_path).convert('RGBA'))[..., 3] > 0).sum()) if hair_path and os.path.exists(hair_path) else 0
    return {'cells': len(found),
            'dy_max': max((abs(m['dy']) for m in found), default=None), 'dx_max': max((abs(m['dx']) for m in found), default=None),
            'dy_avg': round(sum(abs(m['dy']) for m in found) / max(1, len(found)), 2),
            'h_min': round(min((m['h'] for m in found), default=0), 3), 'h_max': round(max((m['h'] for m in found), default=0), 3),
            'semi': semi, 'mag': mag, 'hair': hair_px, 'crown': bald_check(ai_path),
            'backface': back_face_check(ai_path), 'outfit': outfit_check(ai_path, base_path)}

def verdict(s):
    bad = []
    if s['cells'] < 12: bad.append('칸누락%d' % (12 - s['cells']))
    if s['dy_max'] is not None and s['dy_max'] > 3: bad.append('세로%dpx' % s['dy_max'])
    if s['dx_max'] is not None and s['dx_max'] > 3: bad.append('가로%dpx' % s['dx_max'])
    if s['h_min'] < 0.93 or s['h_max'] > 1.07: bad.append('크기%.2f~%.2f' % (s['h_min'], s['h_max']))
    if s['semi'] or s['mag']: bad.append('잔상')
    if s['crown'] < 300: bad.append('머리없음?')
    if s['backface'] > 150: bad.append('뒤칸에얼굴')
    if s['outfit'] > 45: bad.append('옷바뀜')
    return 'OK' if not bad else ' '.join(bad)

def contact(base_path, ai_paths, out_path):
    """대조표: base | 시도별 — 정면(0,0)·뒤(1,0)·좌(2,1) 3칸을 세로로."""
    cells = [(0, 0), (1, 0), (2, 1)]
    cols = [base_path] + ai_paths
    W = CW * len(cols) + 6 * (len(cols) - 1); H = CH * 3
    out = Image.new('RGBA', (W, H), (40, 40, 48, 255))
    for i, pth in enumerate(cols):
        try: S = Image.open(pth).convert('RGBA')
        except Exception: continue
        for j, (r, c) in enumerate(cells):
            out.alpha_composite(S.crop((c*CW, r*CH, (c+1)*CW, (r+1)*CH)), (i * (CW + 6), j * CH))
    out.resize((W * 2, H * 2), Image.NEAREST).save(out_path)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', required=True)
    ap.add_argument('--gender', default='남', choices=['남', '여'])
    ap.add_argument('--selfies')
    ap.add_argument('--raws', help='이미 생성된 원본들이 있는 폴더 (생성 건너뜀)')
    ap.add_argument('--n', type=int, default=3)
    ap.add_argument('--hue', default='blonde')
    ap.add_argument('--out', default=None, help='대조표 저장 폴더 (기본: 생성원본/backtest)')
    ap.add_argument('--prompt-extra', default='', help='프롬프트 뒤에 덧붙일 제약(A/B 용). 비공개 설정 파일은 안 건드린다')
    a = ap.parse_args()
    cfg = load_cfg()
    if a.prompt_extra: cfg['prompt'] = cfg['prompt'] + ' ' + a.prompt_extra; print('프롬프트 변형 +%d자' % len(a.prompt_extra))
    base = os.path.join(M, 'char', 'walk_female.png' if a.gender == '여' else 'walk.png')
    bt = os.path.join(PRIV, '생성원본', 'backtest'); os.makedirs(bt, exist_ok=True)
    raws = []
    if a.raws:
        raws = sorted(p for p in glob.glob(os.path.join(a.raws, '*.png')) if not p.endswith('_ai.png') and not p.endswith('_hair.png'))
    else:
        if not a.selfies: raise SystemExit('--selfies 또는 --raws')
        for i in range(a.n):
            t0 = time.time()
            raw = os.path.join(bt, '%s_%d.png' % (a.id, i + 1))
            try: gen(cfg, a.gender, a.selfies, raw)
            except SystemExit as e: print('  생성 실패', i + 1, e); continue
            print('  생성 %.0fs' % (time.time() - t0)); raws.append(raw)
    results = []; ais = []
    for raw in raws:
        ai = raw[:-4] + '_ai.png'
        try: regrid_cells(raw, base, ai)
        except SystemExit as e: print('  규격화 실패', raw, e); results.append((raw, None)); continue
        hair = raw[:-4] + '_hair.png'
        try: hair_extract(ai, hair, a.hue)
        except Exception as e: print('  헤어 실패', e); hair = None
        s = score(ai, base, hair); s['verdict'] = verdict(s)
        results.append((raw, s)); ais.append(ai)
    print('\n== 결과 ==')
    ok = 0
    for raw, s in results:
        name = os.path.basename(raw)
        if not s: print(name, '규격화 실패'); continue
        ok += s['verdict'] == 'OK'
        print('%-16s %-28s cells=%d dy≤%s dx≤%s h=%.2f~%.2f semi=%d mag=%d hair=%d crown=%d backface=%d outfit=%d' % (
            name, s['verdict'], s['cells'], s['dy_max'], s['dx_max'], s['h_min'], s['h_max'], s['semi'], s['mag'], s['hair'], s['crown'], s['backface'], s['outfit']))
    print('한 번에 OK: %d / %d' % (ok, len(results)))
    outdir = a.out or bt
    contact(base, ais, os.path.join(outdir, 'backtest_%s.png' % a.id))
    json.dump([{'raw': r, **(s or {})} for r, s in results], io.open(os.path.join(bt, 'backtest_%s.json' % a.id), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('대조표', os.path.join(outdir, 'backtest_%s.png' % a.id))
