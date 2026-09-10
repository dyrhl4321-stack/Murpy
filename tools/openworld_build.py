"""오픈월드 맵 조립 워크플로우 (9-07 대표: "설계 디테일하게 잡고 워크플로우 만들고 생성해야 버그 안 난다")

입력(생성물, 전부 Pro 모델 · 원본은 char/fields/work/):
  park_v4.png      광장 편집본(운동존 → 잔디+오른쪽 출구 길, 윗길 오른쪽 끝까지) — 원본과 합성
  walkway_v4.png   산책로(위·아래 나무로 닫힘, 왼쪽 입구 1개, 오른쪽 강+계단+데크)
  gym_v1.png       야외 헬스장(위·아래·오른쪽 닫힘, 왼쪽 입구 1개)
하는 일:
  1. 광장: 편집본을 원본에 정렬한 뒤 **바뀐 영역만** 페더 마스크로 합성(분수·연못·나머지 = 원본 픽셀 그대로)
  2. 세 맵 256색 양자화 저장(용량 1/3) + ?v 올림
  3. 충돌맵: 바닥색(잔디·길·고무·데크) 유사도 → 48×48, 입구 칸 강제 개방, 물 차단
  4. 게이트: 입구 행은 그림에서 실측(왼쪽 가장자리 길 색 행). 광장 출구 = 오른쪽 끝 (46~47열)
  5. NPC/엑스트라 필드 배치, 비둘기 수, 워밍 목록, 물 애니(위상 루프) 재생성
검증: scratchpad 에 충돌맵 오버레이 3장 저장 → 눈으로 본 뒤 배포.
"""
import io, re, os, sys, json, numpy as np
from PIL import Image, ImageFilter
S = os.environ.get('MW_SCRATCH', 'C:/Users/dyrhl/AppData/Local/Temp/claude/C--Users-dyrhl/20a4c87e-2d13-4b49-900a-95f6f86b3aa2/scratchpad/')
T = 2048 / 48
WORK = 'char/fields/work/'

def quant_save(im, out):
    im.convert('RGB').quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(out, optimize=True)
    return os.path.getsize(out)

# ── 1. 광장 합성 ────────────────────────────────────────────────
def merge_park():
    base = Image.open(WORK + 'park_base.png').convert('RGB')          # 편집 전 원본(9-07 v2 아트)
    ed = Image.open(WORK + 'park_v4.png').convert('RGB').resize(base.size, Image.NEAREST)
    a = np.array(base).astype(int); b = np.array(ed).astype(int)
    # 정렬 확인: 바뀌지 않아야 할 왼쪽 절반의 차이
    off = np.abs(a[:, :1000] - b[:, :1000]).mean()
    print('left-half mean diff', round(off, 2), '(작을수록 정렬 OK, 8 이상이면 편집본이 통째로 흔들린 것)')
    diff = np.abs(a - b).sum(axis=2) > 60
    # 바뀐 영역 = 오른쪽 운동존 + 윗길 끝. 잡음 제거(블러 후 임계) 뒤 페더
    m = Image.fromarray((diff * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(6))
    mk = (np.array(m).astype(float) / 255.0)
    mk[:, :1300] = 0.0   # 왼쪽 2/3 는 절대 손대지 않는다(분수·연못·놀이터)
    out = (a * (1 - mk[..., None]) + b * mk[..., None]).round().astype(np.uint8)
    Image.fromarray(out).save(WORK + 'park_merged.png')
    Image.fromarray((mk * 255).astype(np.uint8)).save(S + 'park_merge_mask.png')
    return Image.fromarray(out), mk

# ── 3. 충돌맵 ──────────────────────────────────────────────────
def classify(im, samples, thr=42, frac=0.62):
    a = np.array(im.convert('RGB')).astype(int); W, H = im.size; t = W / 48
    def med(px, py):
        x, y = int(W * px), int(H * py); return np.median(a[y - 10:y + 10, x - 10:x + 10].reshape(-1, 3), axis=0)
    G = np.stack([med(*s) for s in samples]); flat = a.reshape(-1, 3)
    dist = np.min(np.linalg.norm(flat[:, None, :] - G[None, :, :], axis=2), axis=1).reshape(H, W); ground = dist < thr
    water = (a[..., 2] > 140) & (a[..., 2] > a[..., 0] + 40)
    rows = []
    for tr in range(48):
        row = ''
        for tc in range(48):
            c = (slice(int(tr * t), int((tr + 1) * t)), slice(int(tc * t), int((tc + 1) * t)))
            row += '.' if (ground[c].mean() > frac and water[c].mean() < 0.2) else '#'
        rows.append(row)
    return rows

def beige_color(im):   # 길 색 = 베이지 픽셀 전체의 중앙값(점 찍기보다 안전)
    a = np.array(im.convert('RGB')).astype(int); r, g, b = a[..., 0], a[..., 1], a[..., 2]
    m = (r > 150) & (g > 130) & (b > 90) & (r - b > 25) & (r - b < 95) & (r >= g)
    return np.median(a[m].reshape(-1, 3), axis=0)
def walk_img():
    return Image.open(WORK + 'walkway_v4.png')
def road_color(im, pt):
    a = np.array(im.convert('RGB')).astype(int); W, H = im.size; x, y = int(W * pt[0]), int(H * pt[1])
    return np.median(a[y - 10:y + 10, x - 10:x + 10].reshape(-1, 3), axis=0)
def classify_with(im, samples, extra_colors=(), thr=42, frac=0.62):
    a = np.array(im.convert('RGB')).astype(int); W, H = im.size; t = W / 48
    def med(px, py):
        x, y = int(W * px), int(H * py); return np.median(a[y - 10:y + 10, x - 10:x + 10].reshape(-1, 3), axis=0)
    G = np.stack([med(*s) for s in samples] + [np.asarray(c) for c in extra_colors]); flat = a.reshape(-1, 3)
    dist = np.min(np.linalg.norm(flat[:, None, :] - G[None, :, :], axis=2), axis=1).reshape(H, W); ground = dist < thr
    water = (a[..., 2] > 140) & (a[..., 2] > a[..., 0] + 40)
    rows = []
    for tr in range(48):
        row = ''
        for tc in range(48):
            c = (slice(int(tr * t), int((tr + 1) * t)), slice(int(tc * t), int((tc + 1) * t)))
            row += '.' if (ground[c].mean() > frac and water[c].mean() < 0.2) else '#'
        rows.append(row)
    return rows

def edge_road_rows(im, side):
    """가장자리(왼쪽 x=5~30 / 오른쪽) 에서 길(베이지) 색인 행 → 타일 행 범위"""
    a = np.array(im.convert('RGB')).astype(int)
    bands = [(5, 30), (40, 90), (100, 150)] if side == 'L' else [(-30, -5), (-90, -40), (-150, -100)]
    for b0, b1 in bands:   # 가장자리 나무가 길 끝을 덮었으면 조금 안쪽 띠로
        col = a[:, b0:b1].mean(axis=1)
        road = (col[:, 0] > 170) & (col[:, 1] > 150) & (col[:, 2] > 110) & (col[:, 0] - col[:, 2] > 30) & (col[:, 0] - col[:, 2] < 90)
        ys = np.where(road)[0]
        if len(ys) > 40: return int(ys.min() // T), int(ys.max() // T)
    return None

def force(rows, cells, ch='.'):
    for tc, tr in cells:
        if 0 <= tr < 48 and 0 <= tc < 48: rows[tr] = rows[tr][:tc] + ch + rows[tr][tc + 1:]

def setmap(s, name, rows):
    k = s.index(name); a = s.index("map: [", k) + 6; b = s.index("]", a)
    return s[:a] + "\n" + ",\n".join("    '%s'" % r for r in rows) + "\n  " + s[b:]

def overlay(im, rows, out, npcs=()):
    im = im.convert('RGBA'); W, H = im.size; t = W / 48
    ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
    from PIL import ImageDraw; d = ImageDraw.Draw(ov)
    for tr, row in enumerate(rows):
        for tc, c in enumerate(row):
            if c == '#': d.rectangle([tc * t, tr * t, (tc + 1) * t - 1, (tr + 1) * t - 1], fill=(255, 0, 0, 70))
    for u, x, y, h in npcs:
        sp = Image.open(u).convert('RGBA'); fw = sp.width // 3 if sp.height > sp.width / 3 else sp.width // 8
        fh = sp.height // 4 if sp.height > sp.width / 3 else sp.height
        fr = sp.crop((0, 0, fw, fh)); hh = int(t * h); fr = fr.resize((max(1, int(fw * hh / fh)), hh), Image.NEAREST)
        im.alpha_composite(fr, (int(W * x / 100 - fr.width / 2), int(H * y / 100 - fr.height)))
    o = Image.alpha_composite(im, ov); o.thumbnail((1100, 1100)); o.save(out)

def water_boxes(park):
    """분수(중앙 근처 파랑 덩어리)·연못(왼쪽 위 큰 파랑 덩어리) bbox 실측"""
    from scipy import ndimage
    a = np.array(park.convert('RGB')).astype(int)
    blue = (a[..., 2] > 130) & (a[..., 2] > a[..., 0] + 40) & (a[..., 2] > a[..., 1] + 10)
    lab, n = ndimage.label(ndimage.binary_dilation(blue, iterations=6))
    objs = ndimage.find_objects(lab); sizes = ndimage.sum(blue, lab, range(1, n + 1))
    boxes = []
    for i, o in enumerate(objs):
        if sizes[i] < 800: continue
        y0, y1, x0, x1 = o[0].start, o[0].stop, o[1].start, o[1].stop
        boxes.append((sizes[i], x0, y0, x1, y1))
    boxes.sort(reverse=True)
    pond = boxes[0]; fount = None
    for b in boxes[1:]:
        cx, cy = (b[1] + b[3]) / 2 / 2048, (b[2] + b[4]) / 2 / 2048
        if 0.35 < cx < 0.65 and 0.3 < cy < 0.6: fount = b; break
    pad = 14
    f = (max(0, fount[1] - pad), max(0, fount[2] - 40), fount[3] + pad, fount[4] + pad)     # 물줄기 위쪽 여유
    q = (max(0, pond[1] - pad), max(0, pond[2] - pad), pond[3] + pad, pond[4] + pad)
    print('fount box', f, 'pond box', q)
    return f, q

def put_spots(s, key, im, rows):
    """강아지 킁킁 스팟(sniff: [[tc,tr,kind]]) + 오리 물칸(duck: [[tc,tr]]) 을 _FIELDS.<key> 에 박는다. kind 'd'=꽃·흙(파기) 's'=덤불·벤치(냄새)"""
    a = np.array(im.convert('RGB')).astype(int); W, H = im.size; t = W / 48
    def cell(tc, tr): return a[int(tr * t):int((tr + 1) * t), int(tc * t):int((tc + 1) * t)]
    def kind(tc, tr):
        c = cell(tc, tr); med = np.median(c.reshape(-1, 3), axis=0); r, g, b = med
        sat = (c.max(axis=2) - c.min(axis=2)).mean()
        if g > r + 25 and g > b + 25 and g < 150: return 's'
        if r > g + 15 and g > b and r - b > 50 and r < 190: return 's'
        if sat > 90 and (r > 150 or (r > 120 and b > 120)): return 'd'
        return None
    sn = []
    for tr in range(1, 47):
        for tc in range(1, 47):
            if rows[tr][tc] != '.': continue
            ks = [kind(tc + dc, tr + dr) for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)) if rows[tr + dr][tc + dc] == '#']
            ks = [k for k in ks if k]
            if ks: sn.append([tc, tr, 'd' if 'd' in ks else 's'])
    dk = []
    if key == 'park':
        for tr in range(24):
            for tc in range(48):
                c = cell(tc, tr); water = ((c[..., 2] > 130) & (c[..., 2] > c[..., 0] + 40)).mean()
                if water > 0.75: dk.append([tc, tr])
    import random; random.seed(7); random.shuffle(sn); sn = sn[:70]
    k0 = s.index("%s: { name: '" % key); a0 = s.index("start: {", k0); a1 = s.index("}", a0) + 1
    tail = s[a1:]
    # road(조깅 길)·low(데크 칸)는 보존하고 sniff/duck 만 갈아끼운다
    tail = re.sub(r"^(, road: \[.*?\]\])?(, low: \[.*?\]\])?, sniff: \[.*?\]\](, duck: \[.*?\]\])?(?=, map: \[)", lambda m: (m.group(1) or '') + (m.group(2) or ''), tail, count=1, flags=re.S)
    ins = ", sniff: %s" % json.dumps(sn, separators=(',', ':')).replace('"', "'")
    if key == 'park': ins += ", duck: %s" % json.dumps(dk, separators=(',', ':'))
    print('  spots', key, 'sniff', len(sn), 'duck', len(dk))
    return s[:a1] + ins + tail

def head_h(path, n=4):
    """엑스트라 h(칸) = base 머리폭(87/224) 기준 — 셀 높이가 아니라 머리 폭으로 크기를 맞춘다(9-09 대표 '캐릭터가 작다')"""
    a = np.array(Image.open(path).convert('RGBA')); H, W = a.shape[:2]; c = a[:, :W // n]
    r, g, b, al = c[..., 0].astype(int), c[..., 1].astype(int), c[..., 2].astype(int), c[..., 3] > 0
    skin = al & (r > 170) & (g > 110) & (b > 80) & (r > g + 20) & (g > b + 10); hw = int(skin[:int(H * 0.6)].sum(axis=1).max()) or 1
    return round(3.3 * (87 / 224) / (hw / H), 2)

def place_free(s, rows, field, prefs):
    """엑스트라 발끝 (x%,y%) 주변(폭 h*ar 칸·몸통 아래 60%·여유 1칸)이 전부 '.' 이어야 통과. 아니면 prefs 후보 중 첫 통과 자리로 옮긴다."""
    def free(x, y, h, ar, margin=1):
        tc = x / 100 * 48; tr = y / 100 * 48; w = h * ar; c0 = int(tc - w / 2) - margin; c1 = int(tc + w / 2) + margin; r0 = int(tr - h * 0.6) - margin; r1 = int(tr) + margin
        return all(0 <= r < 48 and 0 <= c < 48 and rows[r][c] == '.' for r in range(r0, r1 + 1) for c in range(c0, c1 + 1))
    xs = s.index("window._MW_PARK_EXTRAS = ["); xe = s.index("];", xs)
    for img, x, y, h, ar in re.findall(r"field: '%s', img: '([^']+)', strip: \d, x: ([0-9.]+), y: ([0-9.]+), h: ([0-9.]+), ms: \d+, ar: ([0-9.]+)" % field, s[xs:xe]):
        key = img.split('/')[-1].split('.')[0]
        if free(float(x), float(y), float(h), float(ar)): print('  extra', key, 'ok at', x, y); continue
        for cx, cy in prefs.get(key, []):
            if free(cx, cy, float(h), float(ar)):
                s = re.sub(r"(img: '%s', strip: \d, x: )[0-9.]+(, y: )[0-9.]+" % re.escape(img), r"\g<1>%s\g<2>%s" % (float(cx), float(cy)), s); print('  extra', key, 'moved to', cx, cy); break
        else: print('  ★extra', key, 'no free spot')
    return s

def cell_ar(path, n):
    im = Image.open(path); return (im.width / n) / im.height

def main():
    park = Image.open(WORK + 'park_v5.png').convert('RGB')   # v5(9-08): 출구 = 오른쪽 위(→산책로) + 왼쪽 가운데(→야외 헬스장)
    fb, qb = water_boxes(park)
    json.dump({'fount': fb, 'pond': qb, 'src': WORK + 'park_v5.png'}, open('char/fields/anim/water_boxes.json', 'w'))
    mk = np.ones((2048, 2048))   # 전체 재분류
    from PIL import ImageOps
    walk = Image.open(WORK + 'walkway_v4.png'); gym = Image.open(WORK + 'gym_v11.png').convert('RGB')   # v11(9-10 대표 "왼쪽 상단 철봉 그림자 이상·오른쪽 머신 뭔지 모르겠음"): 기구를 하나씩 이름 붙여 다시 생성(gym_v10_3) — 그림자가 원화에 들어 있어 베이크 안 함
    print('park2', quant_save(park, 'char/fields/field_park2.png'), 'walk', quant_save(walk, 'char/fields/field_walk.png'), 'outgym', quant_save(gym, 'char/fields/field_outgym.png'))
    p = 'index.html'; s = io.open(p, encoding='utf-8').read()
    # 광장 충돌맵: 바뀐 영역(마스크>0.5)만 재분류, 나머지는 기존 맵 유지
    k = s.index("park: { name: '공원'"); a = s.index("map: [", k) + 6; b = s.index("]", a)
    pr = [x or y for x, y in re.findall(r"'([^']+)'|\"([^\"]+)\"", s[a:b])]
    # 잔디 3점 + 놀이터 모래 + 길(길은 폭이 좁아 점 찍기 위험 → 산책로 입구 길 색을 그대로 빌린다: 같은 팔레트) (★가장자리 나무를 샘플로 찍지 말 것)
    pnew = classify_with(park, [(0.55, 0.30), (0.30, 0.62), (0.80, 0.85)], extra_colors=[beige_color(park)], thr=34)
    for tr in range(48):
        for tc in range(48):
            c = mk[int(tr * T):int((tr + 1) * T), int(tc * T):int((tc + 1) * T)]
            if c.mean() > 0.5: pr[tr] = pr[tr][:tc] + pnew[tr][tc] + pr[tr][tc + 1:]
    pg = edge_road_rows(park, 'R'); print('park right-edge road rows', pg)
    # 오른쪽 가장자리 길 행 묶음(윗길 6~8 근처 / 출구길 20~26 근처)
    ys = []
    ar = np.array(park.convert('RGB')).astype(int)[:, -30:-5].mean(axis=1)
    road = (ar[:, 0] > 170) & (ar[:, 1] > 150) & (ar[:, 2] > 110) & (ar[:, 0] - ar[:, 2] > 30) & (ar[:, 0] - ar[:, 2] < 90)
    runs = []; y = 0
    while y < 2048:
        if road[y]:
            y0 = y
            while y < 2048 and road[y]: y += 1
            if y - y0 > 40: runs.append((int(y0 // T), int((y - 1) // T)))
        else: y += 1
    print('park right-edge road runs', runs)
    top = [r for r in runs if r[0] < 14]
    topr = top[0] if top else (6, 8)
    lm = edge_road_rows(park, 'L'); midr = lm if lm else (20, 22); print('park LEFT exit rows', midr)
    force(pr, [(c, r) for c in range(44, 48) for r in range(topr[0], topr[1] + 1)])
    force(pr, [(c, r) for c in range(0, 4) for r in range(midr[0], midr[1] + 1)])
    s = setmap(s, "park: { name: '공원'", pr)
    # 분수·연못 CSS 박스(%)
    s = re.sub(r"\.pk-fx-fount\{left:[0-9.]+%;top:[0-9.]+%;width:[0-9.]+%;height:[0-9.]+%\}", ".pk-fx-fount{left:%.2f%%;top:%.2f%%;width:%.2f%%;height:%.2f%%}" % (fb[0]/20.48, fb[1]/20.48, (fb[2]-fb[0])/20.48, (fb[3]-fb[1])/20.48), s)
    s = re.sub(r"\.pk-fx-pond\{left:[0-9.]+%;top:[0-9.]+%;width:[0-9.]+%;height:[0-9.]+%\}", ".pk-fx-pond{left:%.2f%%;top:%.2f%%;width:%.2f%%;height:%.2f%%}" % (qb[0]/20.48, qb[1]/20.48, (qb[2]-qb[0])/20.48, (qb[3]-qb[1])/20.48), s)
    # NPC 자리(새 광장): 관리인 = 분수 오른쪽, 민준이 = 놀이터 왼쪽 잔디
    s = re.sub(r"(\{ k: 'keeper',[^\n]*?x: )[0-9.]+(, y: )[0-9.]+", r"\g<1>%.1f\g<2>%.1f" % ((fb[2]/20.48)+3.0, (fb[3]/20.48)-1.0), s)
    s = re.sub(r"(\{ k: 'kid',[^\n]*?x: )[0-9.]+(, y: )[0-9.]+", r"\g<1>66.0\g<2>82.0", s)
    # 산책로 / 야외 헬스장
    wr = classify(walk, [(0.05, 0.47), (0.5, 0.72), (0.78, 0.50), (0.30, 0.80), (0.5, 0.30)])
    w0, w1 = edge_road_rows(walk, 'L'); print('walk entrance rows', w0, w1)
    gr = classify_with(gym, [(0.95, 0.50), (0.60, 0.60), (0.10, 0.30), (0.50, 0.94), (0.70, 0.30)], extra_colors=[beige_color(gym)], thr=36, frac=0.86)   # v4: 길·고무·잔디·잔디·고무 + 길 베이지. ★기구 칸이 열리지 않게 86%
    g0, g1 = edge_road_rows(gym, 'R'); print('gym entrance rows(right)', g0, g1)
    force(wr, [(c, r) for c in range(0, 4) for r in range(w0, w1 + 1)]); force(gr, [(c, r) for c in range(44, 48) for r in range(g0, g1 + 1)])
    force(wr, [(c, r) for c in range(33, 37) for r in range(22, 26)])   # 강변 데크로 내려가는 계단(v4 실측: x69~75%, y47~55%)
    s = setmap(s, "walk: { name: '산책로'", wr)
    s = s.replace('src: "char/fields/field_park2.png?v=4"', 'src: "char/fields/field_park2.png?v=5"')
    s = s.replace('src: "char/fields/field_walk.png?v=2"', 'src: "char/fields/field_walk.png?v=3"')
    s = re.sub(r'src: "char/fields/field_outgym\.png\?v=\d+"', 'src: "char/fields/field_outgym.png?v=11"', s)
    s = re.sub(r"(walk: \{ name: '산책로'[^\n]*start: \{ tc: 2, tr: )\d+", r"\g<1>%d" % ((w0 + w1) // 2), s)
    s = re.sub(r"(outgym: \{ name: '야외 헬스장'[^\n]*start: \{ tc: )\d+, tr: \d+", r"\g<1>45, tr: %d" % ((g0 + g1) // 2), s)
    if "outgym: { name: '야외 헬스장'" not in s:
        k = s.index("walk: { name: '산책로'"); a = s.index("map: [", k); b = s.index("]", a); end = s.index("}", b) + 1
        s = s[:end] + ",\n  outgym: { name: '야외 헬스장', src: \"char/fields/field_outgym.png?v=1\", grid: 48, start: { tc: 2, tr: %d }, map: [\n%s\n  ] }" % ((g0 + g1) // 2, ",\n".join("    '%s'" % r for r in gr)) + s[end:]
    else:
        s = setmap(s, "outgym: { name: '야외 헬스장'", gr)
    gs = s.index("window._FIELD_GATES = {"); ge = s.index("};", gs)
    s = s[:gs] + """window._FIELD_GATES = {
  // ★9-08 대표 "포탈 중앙으로 가면 이동이 안 된다": 판정은 화살표 자리까지(0~3 / 44~47열), 도착은 상대 맵 판정 밖(5·42열)
  park: [{ tc: [44, 47], tr: [%d, %d], to: 'walk', at: { tc: 5, tr: %d } },
         { tc: [0, 3], tr: [%d, %d], to: 'outgym', at: { tc: 42, tr: %d } }],
  walk: [{ tc: [0, 3], tr: [%d, %d], to: 'park', at: { tc: 42, tr: %d } }],
  outgym: [{ tc: [44, 47], tr: [%d, %d], to: 'park', at: { tc: 5, tr: %d } }]
""" % (topr[0], topr[1], (w0 + w1) // 2, midr[0], midr[1], (g0 + g1) // 2, w0, w1, (topr[0] + topr[1]) // 2, g0, g1, (midr[0] + midr[1]) // 2) + s[ge:]
    s = s.replace("window._MW_OPEN_FIELDS = ['park', 'walk'];", "window._MW_OPEN_FIELDS = ['park', 'walk', 'outgym'];")
    s = s.replace("window._mwPigeons(key === 'park' ? 5 : (key === 'walk' ? 3 : 0))", "window._mwPigeons(key === 'park' ? 5 : (key === 'walk' ? 3 : (key === 'outgym' ? 2 : 0)))")
    s = s.replace("{ k: 'trainer', name: '강 코치'", "{ k: 'trainer', field: 'outgym', name: '강 코치'")
    s = re.sub(r"(\{ k: 'trainer',[^\n]*?x: )[0-9.]+(, y: )[0-9.]+", r"\g<1>80.2\g<2>64.4", s)
    s = re.sub(r"(\{ k: 'grandma',[^\n]*?x: )[0-9.]+(, y: )[0-9.]+", r"\g<1>25.0\g<2>60.0", s)
    GB = cell_ar('char/npc/anim/grandma_bench4.png', 4); KB = cell_ar('char/npc/anim/kid_ball4.png', 4)
    s = re.sub(r"img: 'char/npc/anim/grandma_[a-z0-9]+\.png\?v=\d+', (anim: 3|strip: 4), ms: \d+(, ar: [0-9.]+)?", "img: 'char/npc/anim/grandma_bench4.png?v=2', strip: 4, ms: 4800, ar: %.3f" % GB, s)
    s = re.sub(r"img: 'char/npc/anim/kid_[a-z0-9]+\.png\?v=\d+', strip: \d, ms: \d+(, ar: [0-9.]+)?", "img: 'char/npc/anim/kid_ball4.png?v=1', strip: 4, ms: 1600, ar: %.3f" % KB, s)
    for key_, im_, rows_ in (('park', park, pr), ('walk', walk, wr), ('outgym', gym, gr)):
        s = put_spots(s, key_, im_, rows_)
    xs = s.index("window._MW_PARK_EXTRAS = ["); xe = s.index("];", xs) + 2
    s = s[:xs] + """window._MW_PARK_EXTRAS = [   // ★9-09 대표: 기구 포함 스프라이트는 숨쉬기 없음(전체 끔), 자리는 충돌맵 검증(free). 값은 확정본 — 빌드가 되돌리지 않는다
  { field: 'outgym', img: 'char/npc/anim/extra_pullup4.png?v=14', strip: 4, x: 26.0, y: 43.5, h: 3.82, ms: 2200, ar: 0.703, noBreathe: true },
  { field: 'outgym', img: 'char/npc/anim/extra_stretch4.png?v=2', strip: 4, x: 51.0, y: 68.5, h: 3.06, ms: 3600, ar: 0.657 },
];""" + s[xe:]
    s = s.replace("  (window._curField === 'park' ? (window._MW_PARK_EXTRAS || []) : []).forEach(function (x) {",
                  "  (window._MW_PARK_EXTRAS || []).filter(function (x) { return (x.field || 'park') === window._curField; }).forEach(function (x) {")
    s = s.replace(".pk-fx-fount>i{width:1600%;background-image:url('char/fields/anim/fountain_anim.png?v=3');animation-duration:2.4s;animation-timing-function:steps(16)}",
                  ".pk-fx-fount>i{width:2400%;background-image:url('char/fields/anim/fount_loop.png?v=1');animation-duration:2.4s;animation-timing-function:steps(24)}")
    s = s.replace(".pk-fx-pond>i{width:800%;background-image:url('char/fields/anim/pond_anim.png?v=1');animation-duration:2.4s;animation-timing-function:steps(8)}",
                  ".pk-fx-pond>i{width:2400%;background-image:url('char/fields/anim/pond_loop.png?v=1');animation-duration:3.6s;animation-timing-function:steps(24)}")
    s = s.replace("[F.park && F.park.src, F.walk && F.walk.src, 'char/fields/anim/fountain_anim.png?v=3', 'char/fields/anim/pond_anim.png?v=1', 'char/fields/anim/pigeon6.png?v=1']",
                  "[F.park && F.park.src, F.walk && F.walk.src, F.outgym && F.outgym.src, 'char/fields/anim/fount_loop.png?v=1', 'char/fields/anim/pond_loop.png?v=1', 'char/fields/anim/pigeon6.png?v=1']")
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
    for kk in ("field_outgym.png?v=1", "to: 'outgym'", "fount_loop.png", "pond_loop.png", "field: 'outgym', name: '강 코치'", "'park', 'walk', 'outgym'", "field_park2.png?v=4"):
        print('  check', kk, s.count(kk))
    overlay(park, pr, S + 'chk_park.png', [('char/npc/walk_npc_keeper.png', (fb[2]/20.48)+3.0, (fb[3]/20.48)-1.0, 3.3), ('char/npc/anim/kid_ball4.png', 66.0, 82.0, 2.8)])
    overlay(walk, wr, S + 'chk_walk.png', [('char/npc/anim/grandma_sit.png', 25.0, 60.0, 3.15)])
    overlay(gym, gr, S + 'chk_gym.png', [('char/npc/anim/trainer_coach.png', 74.0, 50.0, 3.3), ('char/npc/anim/extra_pullup4.png', 62.0, 60.0, 3.9), ('char/npc/anim/extra_press4.png', 50.0, 74.0, 3.3), ('char/npc/anim/extra_stretch4.png', 72.0, 74.0, 3.3)])
    json.dump({'walk': (w0, w1), 'gym': (g0, g1), 'top': topr, 'mid': midr}, open(S + 'batch.json', 'w'))

if __name__ == '__main__':
    main()
