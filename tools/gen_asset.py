# -*- coding: utf-8 -*-
"""제미나이(나노바나나)로 에셋을 뽑아 규격에 맞춘다 — 대표가 프롬프트를 복붙하지 않게 (2026-08-30).

    python tools/gen_asset.py "<프롬프트>" char/game/golf_ball.png --w 160 --h 160 --nukki
    python tools/gen_asset.py "<프롬프트>" char/game/golf_bg.jpg --w 720 --h 1290          # 배경(누끼 없음)
    python tools/gen_asset.py --file docs/prompts/03-golf-game-assets.txt --block 3 char/game/golf_ball.png --w 160 --h 160 --nukki

키: C:\\Users\\allys\\.config\\murpy\\gemini.txt (저장소 밖) 또는 환경변수 GEMINI_API_KEY
모델: gemini-2.5-flash-image (장당 약 $0.04). 무료 등급은 이미지 429 → 결제 연결 필요.

흐름: 생성 → (--nukki: #00FF00 형광초록 키잉, char/nukki.py 와 같은 규칙) → 여백 트림 → 규격 안에 NEAREST 로 맞춤(비율 유지, 가운데) → 저장.
      원본은 out 옆에 `<이름>.raw.png` 로 남긴다(다시 누끼할 때).
"""
import io, os, sys, json, base64, re, urllib.request, argparse
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')

ap = argparse.ArgumentParser()
ap.add_argument('prompt', nargs='?', default='')
ap.add_argument('out')
ap.add_argument('--file'); ap.add_argument('--block', type=int)
ap.add_argument('--w', type=int); ap.add_argument('--h', type=int)
ap.add_argument('--nukki', action='store_true'); ap.add_argument('--greenness', type=int, default=60)
# ★대표 9-04 강명령: 에셋·그림카드는 항상 **가장 높은 모델(나노바나나 Pro)** 로 뽑는다.
#   덤벨피하기 타이틀(역대 최고 퀄)이 Pro 였다. 실패(404/미지원) 시 --model gemini-2.5-flash-image 폴백.
ap.add_argument('--model', default='gemini-3-pro-image-preview')
ap.add_argument('--from-raw', action='store_true', help='생성하지 않고 out 옆 .raw.png 로 누끼·규격만 다시')
ap.add_argument('--tol', type=int, default=48, help='배경색 허용 거리(0~441)')
ap.add_argument('--ref', action='append', default=[], help='레퍼런스 이미지(여러 개 가능) — 캐릭터·화풍을 그대로 따르게')
a = ap.parse_args()

KEY = os.environ.get('GEMINI_API_KEY', '').strip()
if not KEY:
    try: KEY = io.open(os.path.expanduser('~/.config/murpy/gemini.txt'), encoding='utf-8').read().strip()
    except Exception: pass
if not KEY: raise SystemExit('제미나이 키가 없다 (~/.config/murpy/gemini.txt)')

prompt = a.prompt
if a.file:
    txt = io.open(a.file, encoding='utf-8').read()
    blocks = re.split(r'\n(?:-{20,}\n)?\[(\d+)\][^\n]*\n(?:-{20,}\n)?', txt)
    # blocks = [머리, '1', 본문1, '2', 본문2, ...]  (구분선이 있든 없든 [N] 줄로 자른다)
    want = str(a.block)
    for i in range(1, len(blocks) - 1, 2):
        if blocks[i] == want: prompt = blocks[i + 1].strip(); break
    if not prompt: raise SystemExit('블록 [%s] 을 못 찾았다' % want)
if a.nukki and '#00FF00' not in prompt: prompt += '\nBackground must be SOLID flat chroma green #00FF00, no gradient. Nothing else in the image.'

raw = os.path.splitext(a.out)[0] + '.raw.png'
if a.from_raw:
    img = Image.open(raw).convert('RGBA'); print('원본 재사용', img.size, raw)
else:
    parts = []
    for rp in a.ref:
        mime = 'image/png' if rp.lower().endswith('.png') else 'image/jpeg'
        parts.append({'inlineData': {'mimeType': mime, 'data': base64.b64encode(open(rp, 'rb').read()).decode()}})
    parts.append({'text': prompt})
    body = {'contents': [{'parts': parts}], 'generationConfig': {'responseModalities': ['IMAGE']}}
    req = urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s' % (a.model, KEY),
                                 data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    try: r = json.loads(urllib.request.urlopen(req, timeout=120).read().decode())
    except urllib.error.HTTPError as e: raise SystemExit('API %s %s' % (e.code, e.read().decode()[:300]))
    img = None
    for p in r.get('candidates', [{}])[0].get('content', {}).get('parts', []):
        if 'inlineData' in p: img = Image.open(io.BytesIO(base64.b64decode(p['inlineData']['data']))).convert('RGBA'); break
    if img is None: raise SystemExit('이미지가 안 왔다: ' + json.dumps(r)[:300])
    img.save(raw)
    print('원본', img.size, '→', raw)

if a.nukki:
    # ★모델이 #00FF00 을 정확히 안 준다(올리브·연두로 온다). 네 모서리 색을 배경으로 보고,
    #   테두리에서 이어진 비슷한 색만 지운다(안쪽의 비슷한 색은 남는다 — 공의 초록 그림자 등).
    px = img.load(); W, H = img.size
    corners = [px[0, 0], px[W - 1, 0], px[0, H - 1], px[W - 1, H - 1]]
    bg = tuple(sum(c[i] for c in corners) // 4 for i in range(3))
    def near(c): return (c[0] - bg[0]) ** 2 + (c[1] - bg[1]) ** 2 + (c[2] - bg[2]) ** 2 <= a.tol * a.tol
    seen = bytearray(W * H); stack = []
    for x in range(W): stack.append((x, 0)); stack.append((x, H - 1))
    for y in range(H): stack.append((0, y)); stack.append((W - 1, y))
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= W or y >= H: continue
        i = y * W + x
        if seen[i]: continue
        seen[i] = 1
        if not near(px[x, y]): continue
        px[x, y] = (0, 0, 0, 0)
        stack.append((x + 1, y)); stack.append((x - 1, y)); stack.append((x, y + 1)); stack.append((x, y - 1))
    print('배경색', bg, '제거')
    # 여백 트림
    bbox = img.getbbox()
    if bbox: img = img.crop(bbox)
    # 테두리 초록 번짐 완화: 알파 있는 픽셀 중 초록기 강한 것은 채도 낮춤
    # 테두리에 남은 배경색 번짐은 가장자리 1px 만 배경과 가까우면 지운다
    px = img.load(); W, H = img.size
    for y in range(H):
        for x in range(W):
            c = px[x, y]
            if c[3] and (c[0] - bg[0]) ** 2 + (c[1] - bg[1]) ** 2 + (c[2] - bg[2]) ** 2 <= (a.tol * 1.6) ** 2:
                nb = [px[x + dx, y + dy][3] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if 0 <= x + dx < W and 0 <= y + dy < H]
                if any(v == 0 for v in nb): px[x, y] = (0, 0, 0, 0)

if a.w and a.h:
    tw, th = a.w, a.h
    if a.nukki:
        sc = min(tw / img.width, th / img.height)
        small = img.resize((max(1, int(img.width * sc)), max(1, int(img.height * sc))), Image.NEAREST)
        canvas = Image.new('RGBA', (tw, th), (0, 0, 0, 0))
        canvas.paste(small, ((tw - small.width) // 2, th - small.height))   # 바닥 정렬(그림자·홀은 아래에 붙는다)
        img = canvas
    else:
        # 배경은 cover 로 채우고 가운데 자른다
        sc = max(tw / img.width, th / img.height)
        big = img.resize((int(img.width * sc), int(img.height * sc)), Image.LANCZOS)
        l = (big.width - tw) // 2; t = (big.height - th) // 2
        img = big.crop((l, t, l + tw, t + th))
if a.out.lower().endswith('.jpg') or a.out.lower().endswith('.jpeg'): img.convert('RGB').save(a.out, quality=88)
else: img.save(a.out)
print('저장', img.size, '→', a.out)
