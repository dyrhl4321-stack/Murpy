# -*- coding: utf-8 -*-
"""옷 색상 파생 — 정합이 검증된 기존 아이템 시트의 **색만** 바꿔 새 아이템을 만든다(9-08, 대표: "새 커마 에셋 생성이 제일 두렵다").
새 기하를 만들지 않으므로 정합 오류가 구조적으로 0 이다(민준이 노란 티가 첫 사례).

    python tools/item_recolor.py top_basic_tee "#3D7EFF" top_tee_blue --name "파란 티"            # 시트+썸네일 생성 + 검수 미리보기
    python tools/item_recolor.py top_f_hoodzip "#F5C24B" top_f_hoodzip_yellow --name "노랑 후드집업" --mode tint
    python tools/item_recolor.py --batch tools/recolor_batch.txt                                     # 여러 줄 한 번에

모드
  tint : 흰/회색(채도 낮음) 천 → 목표 색. 명도(그늘)는 원본 유지, 채도는 목표치. 어두운 외곽선은 그대로. (기본 티·회색 후드·츄리닝·나시)
  hue  : 이미 색이 있는 천 → 색상(hue)만 목표로 돌림. 채도·명도 유지. (레드 후디·보라 집업)
  auto : 채도 있는 픽셀 비율로 자동 선택
산출: char/items/<out>.png, <out>_thumb.png(원본 썸네일 같은 방식으로 재색), 검수 폴더에 12칸 합성(기본 몸통 + 커마 몸통) 미리보기.
등록은 하지 않는다 — 대표 승인 뒤 CHAR_ITEMS 에 한 줄 추가(출력에 그 줄을 찍어준다).
"""
import os, sys, io, re, argparse, colorsys, subprocess, datetime
import numpy as np
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ITEMS = os.path.join(ROOT, 'char', 'items')
REVIEW_ROOT = r'C:\Users\dyrhl\Desktop\머피브랜딩\머피월드 캐릭터\커스터마이징 3차\에셋검수'

def hex2rgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def recolor_array(a, target, mode):
    a = a.astype(float); out = a.copy()
    th, ts, tv = colorsys.rgb_to_hsv(*(np.array(target) / 255.0))
    op = a[..., 3] > 0
    ys, xs = np.where(op)
    if mode == 'auto':
        sat = 0; tot = 0
        for y, x in zip(ys[::5], xs[::5]):
            h, s, v = colorsys.rgb_to_hsv(*(a[y, x, :3] / 255.0)); tot += 1
            if s > 0.25 and v > 0.3: sat += 1
        mode = 'hue' if tot and sat / tot > 0.3 else 'tint'
    # ★밝기 정규화: 천에서 가장 밝은 픽셀이 목표 밝기(tv)가 되고 그늘은 비례해서 어두워진다.
    #   (없으면 회색 천 위 노랑은 올리브, 검정은 회청색이 된다 — 9-08 1차 배치)
    vmax = 0.0
    for y, x in zip(ys[::3], xs[::3]):
        h, s, v = colorsys.rgb_to_hsv(*(a[y, x, :3] / 255.0))
        if v >= 0.30 and (mode != 'tint' or s <= 0.35): vmax = max(vmax, v)
    vmax = vmax or 1.0
    for y, x in zip(ys, xs):
        r, g, b = a[y, x, :3] / 255.0; h, s, v = colorsys.rgb_to_hsv(r, g, b)
        if v < 0.30: continue                                   # 외곽선·깊은 그늘은 그대로
        if mode == 'tint':
            if s > 0.35: continue                               # 이미 색이 있는 부분(프린트·지퍼 등)은 유지
            rel = v / vmax
            nv = max(0.12, tv * rel) if tv >= 0.35 else max(0.10, tv + (rel - 1.0) * 0.12)   # 어두운 목표(검정)는 그늘 폭을 좁게
            ns = ts if tv >= 0.35 else min(ts, 0.35)
            nr, ng, nb = colorsys.hsv_to_rgb(th, ns, nv)
        else:  # hue
            if s < 0.20: continue
            nr, ng, nb = colorsys.hsv_to_rgb(th, s, v)
        out[y, x, :3] = [nr * 255, ng * 255, nb * 255]
    return out.astype(np.uint8), mode

def composite_preview(sheet_path, body_key, out_path):
    W, H = 141, 224
    bodies = {'human': os.path.join(ROOT, 'char', 'walk.png'), 'human_f': os.path.join(ROOT, 'char', 'walk_female.png')}
    faces = [('jaejin', os.path.join(ROOT, 'char', 'faces', 'jaejin.png'), None)] if body_key == 'human' else [('paesuhyun', os.path.join(ROOT, 'char', 'faces', 'paesuhyun.png'), os.path.join(ROOT, 'char', 'faces', 'paesuhyun_hair.png'))]
    t = Image.open(sheet_path).convert('RGBA')
    panels = []
    for name, bp, hp in [('base', bodies[body_key], None)] + faces:
        if not os.path.exists(bp): continue
        b = Image.open(bp).convert('RGBA'); bg = Image.new('RGBA', b.size, (60, 60, 70, 255)); bg.alpha_composite(b); bg.alpha_composite(t)
        if hp and os.path.exists(hp): bg.alpha_composite(Image.open(hp).convert('RGBA'))
        panels.append(bg)
    out = Image.new('RGB', (sum(p.width for p in panels) + 10 * (len(panels) - 1), panels[0].height), (60, 60, 70)); x = 0
    for p in panels: out.paste(p.convert('RGB'), (x, 0)); x += p.width + 10
    out = out.resize((out.width * 2, out.height * 2), Image.NEAREST); out.save(out_path)

def one(src_id, color, out_id, name, mode, review_dir, body_key=None):
    src = os.path.join(ITEMS, src_id + '.png'); assert os.path.exists(src), src
    a = np.array(Image.open(src).convert('RGBA'))
    out, used = recolor_array(a, hex2rgb(color), mode)
    dst = os.path.join(ITEMS, out_id + '.png'); Image.fromarray(out).save(dst)
    th_src = os.path.join(ITEMS, src_id + '_thumb.png'); th_dst = None
    if os.path.exists(th_src):
        ta = np.array(Image.open(th_src).convert('RGBA')); tout, _ = recolor_array(ta, hex2rgb(color), used)
        th_dst = os.path.join(ITEMS, out_id + '_thumb.png'); Image.fromarray(tout).save(th_dst)
    body_key = body_key or ('human_f' if src_id.split('_')[1] == 'f' else 'human')
    base = os.path.join(ROOT, 'char', 'walk_female.png' if body_key == 'human_f' else 'walk.png')
    pur = subprocess.run([sys.executable, os.path.join(HERE, 'item-purity-check.py'), dst, '--base', base], capture_output=True, text=True, encoding='utf-8', errors='replace')
    ok = pur.stdout.strip().splitlines()[-1] if pur.stdout.strip() else pur.stderr.strip()[-200:]
    os.makedirs(review_dir, exist_ok=True)
    composite_preview(dst, body_key, os.path.join(review_dir, out_id + '_미리보기.png'))
    if th_dst: Image.open(th_dst).save(os.path.join(review_dir, out_id + '_thumb.png'))
    slot = src_id.split('_')[0]
    line = "  { id: '%s', slot: '%s', body: '%s', name: '%s', price: 12, sheet: 'char/items/%s.png', thumb: 'char/items/%s.png' }," % (out_id, slot, body_key, name, out_id, (out_id + '_thumb') if th_dst else (src_id + '_thumb'))
    print('%-24s ← %-18s %s mode=%s | 순도: %s' % (out_id, src_id, color, used, ok))
    print('   등록줄:', line)
    return line

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src', nargs='?'); ap.add_argument('color', nargs='?'); ap.add_argument('out', nargs='?')
    ap.add_argument('--name', default=''); ap.add_argument('--mode', default='auto', choices=['auto', 'tint', 'hue'])
    ap.add_argument('--batch', help='줄마다: src color out 이름 [mode]')
    ap.add_argument('--review', default=None, help='검수 폴더(기본: 에셋검수/<오늘>_색상파생)')
    a = ap.parse_args()
    review = a.review or os.path.join(REVIEW_ROOT, datetime.date.today().strftime('%Y-%m-%d') + '_색상파생')
    lines = []
    if a.batch:
        for raw in io.open(a.batch, encoding='utf-8'):
            raw = raw.strip()
            if not raw or raw.startswith('#'): continue
            parts = raw.split()
            src, color, out, name = parts[0], parts[1], parts[2], parts[3]
            mode = parts[4] if len(parts) > 4 else 'auto'
            lines.append(one(src, color, out, name, mode, review))
    else:
        assert a.src and a.color and a.out, '인자: src color out --name ...'
        lines.append(one(a.src, a.color, a.out, a.name or a.out, a.mode, review))
    io.open(os.path.join(review, '_등록줄.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    io.open(os.path.join(review, '_읽어주세요.txt'), 'w', encoding='utf-8').write(
        '색상 파생 아이템 검수\n- 기존 정합 시트의 색만 바꾼 것이라 정합 오류 없음(순도 검사 통과분만).\n- *_미리보기.png = 기본 몸통 + 커마 몸통 12칸 합성. *_thumb.png = 썸네일.\n- 승인하시면 _등록줄.txt 의 줄을 카탈로그에 넣어 배포합니다.\n')
    print('검수 폴더:', review)

if __name__ == '__main__':
    main()
