# -*- coding: utf-8 -*-
"""얼굴 커마권 파이프라인 — 셀카 → 제미나이 생성 → 규격화 → base 몸 이식 → 피부톤 6종 → 검수 미리보기.

    python tools/face_pipeline.py --id kim --gender 남 --selfies <셀카폴더>     # 생성부터 끝까지
    python tools/face_pipeline.py --id kim --raw <생성원본.png>                 # 생성 건너뛰고 규격화부터
    python tools/face_pipeline.py --id kim --src char/faces/kim_src.png         # 이미 423x896 이면 이식부터

산출물:
    char/faces/{id}_src.png   규격(423x896) 얼굴 소스
    char/faces/{id}.png       base 몸 + 고객 머리 (앱이 쓰는 시트)
    char/skin/face_{id}_t*.png  피부톤 5종 (t3 은 원색이라 없음)
    ../Murpy_private/제작노하우/검수/{id}_preview.png  대표 검수용 (정면 셀 × 톤별)

★프롬프트와 생성용 베이스 시트 경로는 저장소 밖 비공개 설정에서 읽는다
  (../Murpy_private/제작노하우/얼굴커마-생성설정.txt) — 이 저장소는 공개라 노하우를 여기 안 적는다.
★생성 원본(고객 얼굴 학습 결과)도 저장소가 아니라 Murpy_private 에 저장한다.
제미나이 키: ~/.config/murpy/gemini.txt · 모델 gemini-2.5-flash-image (무료 등급은 이미지 429 → 결제 연결 필요)
"""
import io, os, sys, json, base64, glob, argparse, subprocess, urllib.request
import numpy as np
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')

M = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIV = os.path.join(os.path.dirname(M), 'Murpy_private', '제작노하우')
SW, SH = 423, 896   # 시트 규격 (셀 141x224 · 3열 4행)

def load_cfg():
    p = os.path.join(PRIV, '얼굴커마-생성설정.txt')
    try: txt = io.open(p, encoding='utf-8').read()
    except Exception: raise SystemExit('비공개 설정이 없다: ' + p)
    cfg, sec = {}, ''
    for line in txt.splitlines():
        s = line.strip()
        if not s: continue
        if s.startswith('['): sec = s.strip('[]'); continue
        if sec == '시트' and '=' in s:
            k, v = s.split('=', 1); cfg[k.strip()] = v.strip()
        elif sec == '프롬프트':
            cfg['prompt'] = (cfg.get('prompt', '') + '\n' + s).strip()
    for need in ('남', '여', 'prompt'):
        if not cfg.get(need): raise SystemExit('설정에 %s 가 없다' % need)
    return cfg

def gen(cfg, gender, selfies_dir, out_raw, model):
    key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not key:
        try: key = io.open(os.path.expanduser('~/.config/murpy/gemini.txt'), encoding='utf-8').read().strip()
        except Exception: pass
    if not key: raise SystemExit('제미나이 키가 없다 (~/.config/murpy/gemini.txt)')
    selfies = sorted(sum((glob.glob(os.path.join(selfies_dir, e)) for e in ('*.jpg', '*.jpeg', '*.png')), []))[:8]
    if len(selfies) < 3: raise SystemExit('셀카가 너무 적다(%d장) — 정면 6장 정도 필요' % len(selfies))
    parts = []
    for p in [cfg[gender]] + selfies:
        mime = 'image/png' if p.lower().endswith('.png') else 'image/jpeg'
        parts.append({'inlineData': {'mimeType': mime, 'data': base64.b64encode(open(p, 'rb').read()).decode()}})
    parts.append({'text': cfg['prompt']})
    body = {'contents': [{'parts': parts}], 'generationConfig': {'responseModalities': ['IMAGE']}}
    req = urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s' % (model, key),
                                 data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    try: r = json.loads(urllib.request.urlopen(req, timeout=180).read().decode())
    except urllib.error.HTTPError as e: raise SystemExit('API %s %s' % (e.code, e.read().decode()[:300]))
    for p in r.get('candidates', [{}])[0].get('content', {}).get('parts', []):
        if 'inlineData' in p:
            img = Image.open(io.BytesIO(base64.b64decode(p['inlineData']['data']))).convert('RGBA')
            os.makedirs(os.path.dirname(out_raw), exist_ok=True)
            img.save(out_raw); print('생성 원본', img.size, '→', out_raw)
            return out_raw
    raise SystemExit('이미지가 안 왔다: ' + json.dumps(r)[:300])

def regrid(raw_path, out_src):
    """단색 배경(마젠타 등) 제거 + 423x896 NEAREST + 알파 128 이진화.
    배경은 gen_asset 과 같은 방식 — 네 모서리 색을 배경으로 보고 **테두리에서 이어진** 픽셀만 지운다
    (안쪽의 비슷한 색은 남는다). 재진 전례: 704x1504 → 423x896 통짜 리샘플."""
    img = Image.open(raw_path).convert('RGBA')
    px = img.load(); W, H = img.size
    corners = [px[0, 0], px[W - 1, 0], px[0, H - 1], px[W - 1, H - 1]]
    bg = tuple(sum(c[i] for c in corners) // 4 for i in range(3))
    tol = 60
    seen = bytearray(W * H); stack = []
    for x in range(W): stack.append((x, 0)); stack.append((x, H - 1))
    for y in range(H): stack.append((0, y)); stack.append((W - 1, y))
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= W or y >= H: continue
        i = y * W + x
        if seen[i]: continue
        seen[i] = 1
        c = px[x, y]
        if (c[0] - bg[0]) ** 2 + (c[1] - bg[1]) ** 2 + (c[2] - bg[2]) ** 2 > tol * tol: continue
        px[x, y] = (0, 0, 0, 0)
        stack.append((x + 1, y)); stack.append((x - 1, y)); stack.append((x, y + 1)); stack.append((x, y - 1))
    img = img.resize((SW, SH), Image.NEAREST)
    a = np.array(img)
    a[..., 3] = np.where(a[..., 3] >= 128, 255, 0)
    Image.fromarray(a, 'RGBA').save(out_src)
    print('규격화 %dx%d(배경 %s 제거) → %s' % (W, H, str(bg), out_src))
    return out_src

def preview(cid, grafted_path):
    """정면 셀(1행 1열)을 원색 + 톤 5종으로 나란히 — 대표가 이 한 장으로 승인한다."""
    cells = [('base', grafted_path)]
    for t in ('t1', 't2', 't4', 't5', 't6'):
        p = os.path.join(M, 'char', 'skin', 'face_%s_%s.png' % (cid, t))
        if os.path.exists(p): cells.append((t, p))
    tiles = []
    for name, p in cells:
        im = Image.open(p).convert('RGBA').crop((0, 0, 141, 224)).resize((141 * 3, 224 * 3), Image.NEAREST)
        tiles.append(im)
    board = Image.new('RGBA', (sum(t.width for t in tiles) + 8 * (len(tiles) + 1), 224 * 3 + 16), (14, 19, 32, 255))
    x = 8
    for t in tiles: board.paste(t, (x, 8), t); x += t.width + 8
    out = os.path.join(PRIV, '검수', cid + '_preview.png')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    board.convert('RGB').save(out)
    print('검수 미리보기 →', out)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', required=True, help='고객 id (영문 소문자) — 파일·몸통 키에 쓰인다')
    ap.add_argument('--gender', default='남', choices=['남', '여'])
    ap.add_argument('--selfies', help='정면 셀카 폴더 (생성부터)')
    ap.add_argument('--raw', help='이미 생성된 원본 (규격화부터)')
    ap.add_argument('--src', help='이미 423x896 규격인 소스 (이식부터)')
    ap.add_argument('--model', default='gemini-2.5-flash-image')
    ap.add_argument('--no-bake', action='store_true')
    a = ap.parse_args()

    src = a.src
    raw = a.raw
    if not src:
        if not raw:
            if not a.selfies: raise SystemExit('--selfies / --raw / --src 중 하나는 필요하다')
            raw = gen(load_cfg(), a.gender, a.selfies,
                      os.path.join(PRIV, '생성원본', a.id + '.png'), a.model)
        src = regrid(raw, os.path.join(M, 'char', 'faces', a.id + '_src.png'))

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from face_graft import graft
    base = os.path.join(M, 'char', 'walk_female.png' if a.gender == '여' else 'walk.png')
    out = os.path.join(M, 'char', 'faces', a.id + '.png')
    graft(base, src, out)

    if not a.no_bake:
        r = subprocess.run([sys.executable, os.path.join(M, 'tools', 'skin_bake.py'),
                            '--src', out, '--pre', 'face_' + a.id], capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip()[:300])
        if r.returncode: raise SystemExit('피부톤 굽기 실패')

    preview(a.id, out)
    print('\n다음 수순: ①미리보기로 대표 승인 ②index.html _CHAR_BODIES.%s + SQ_MG_EYES.%s 등록(가이드 5단계) ③배포' % (a.id, a.id))
