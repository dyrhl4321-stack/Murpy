# -*- coding: utf-8 -*-
"""서울 헬스장을 카카오 로컬 API 로 긁어 centers 도감에 넣는다 (2026-08-29, 대표 지시).

    python tools/centers/seed_kakao_seoul.py            # 드라이런(서울): 몇 곳 새로 들어갈지만 센다
    python tools/centers/seed_kakao_seoul.py --all      # 전국 드라이런(적응 격자)
    python tools/centers/seed_kakao_seoul.py --write    # 실제로 Firestore 에 쓴다

준비물
  · 카카오 REST API 키: C:\\Users\\allys\\.config\\murpy\\kakao_rest.txt (저장소 밖) 또는 환경변수 KAKAO_REST_KEY
  · Firestore 쓰기: firebase CLI 로그인 상태(~/.config/configstore/firebase-tools.json 의 refresh_token 을 빌려
    cloud-platform 액세스 토큰으로 바꾼다 — IAM 권한이라 보안규칙과 무관하게 쓴다)

방법
  카카오 키워드 검색은 한 질의당 45건이 상한이라 서울을 격자(약 1.2km)로 쪼개 rect 로 묻는다.
  헬스클럽·크로스핏·피트니스 카테고리만 남긴다(요가·필라테스·수영은 제외 — 헬스장 B2B 가 목적).
  이미 있는 곳(이름 정규화 같음, 또는 60m 안에 비슷한 이름)은 건너뛴다.

문서 모양 = 기존 센터와 같다: name·type·loc(구, '구' 뗌)·addr·lat·lng·img·rating·reviews·members·partner·partnerPosts·reviewList·createdAt·createdBy
  + kakaoId·phone·source:'kakao'  (다음에 다시 돌려도 kakaoId 로 중복이 안 생긴다)
"""
import io, os, sys, json, math, time, re, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding='utf-8')

WRITE = '--write' in sys.argv
KEY = os.environ.get('KAKAO_REST_KEY', '').strip()
if not KEY:
    try: KEY = io.open(os.path.expanduser('~/.config/murpy/kakao_rest.txt'), encoding='utf-8').read().strip()
    except Exception: pass
if not KEY: raise SystemExit('카카오 REST 키가 없다 (~/.config/murpy/kakao_rest.txt)')
P = 'murpyprototype'; APIKEY = 'AIzaSyBvMB4T-ApzHDsfmBx4f5HpPmgkqlcZ7VQ'
CID = '563584335869-fgrhgmd47bqnekij5i8b5pr03ho849e6.apps.googleusercontent.com'
CSEC = 'j9iVZfS8kkCEFUPaAeJV0sAi'

# 서울 대략 경계 (좌하 → 우상)
LNG0, LNG1, LAT0, LAT1 = 126.76, 127.19, 37.42, 37.71
CELL_KM = 1.2
KEYWORDS = ['헬스장', '크로스핏']
KEEP = ('헬스클럽', '크로스핏', '피트니스', 'PT')

def kakao(q, rect, page):
    url = ('https://dapi.kakao.com/v2/local/search/keyword.json?' + urllib.parse.urlencode(
        {'query': q, 'rect': rect, 'size': 15, 'page': page}))
    req = urllib.request.Request(url, headers={'Authorization': 'KakaoAK ' + KEY})
    for i in range(3):
        try: return json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
        except Exception as e:
            time.sleep(1 + i); last = e
    raise last

def norm(s): return re.sub(r'[\s\-\(\)\[\]·,.]|점$|본점$', '', str(s or '')).lower()
def hav(a, b, c, d):
    R = 6371000; r = math.pi / 180
    x = math.sin((c - a) * r / 2) ** 2 + math.cos(a * r) * math.cos(c * r) * math.sin((d - b) * r / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))

# 1) 카카오 수집 — 적응 격자. 한 칸에서 45건(3쪽)이 다 차면 4등분해서 다시 묻는다.
#    서울: 1.2km 고정 격자 (--seoul) / 전국: 24km 에서 시작 → 최소 0.8km (--all)
ALL = '--all' in sys.argv
if ALL: LNG0, LNG1, LAT0, LAT1 = 124.5, 131.9, 33.0, 38.7
found = {}; calls = 0; cells = 0
def cell(lng, lat, w, h, kw):
    """(lng,lat) 좌하 모서리, 폭 w·높이 h(도). 꽉 차면 쪼갠다."""
    global calls, cells
    rect = '%f,%f,%f,%f' % (lng, lat, lng + w, lat + h)
    cells += 1; full = False
    for page in (1, 2, 3):
        j = kakao(kw, rect, page); calls += 1
        # ★"꽉 찼다"는 total_count 로 본다. is_end 는 3쪽이면 늘 true 라 그걸로는 쪼개기가 한 번도 안 일어났다
        #   (8-29 1차 전국 실행이 3,342곳에 그친 원인).
        if page == 1 and (j.get('meta', {}).get('total_count', 0) or 0) > 45: full = True
        for d in j.get('documents', []):
            if not any(k in d.get('category_name', '') for k in KEEP): continue
            if not ALL and not d.get('address_name', '').startswith('서울'): continue
            found[d['id']] = d
        if j.get('meta', {}).get('is_end', True): break
    if full and min(w * 111 * math.cos(37 * math.pi / 180), h * 111) > 0.8:
        for dx in (0, w / 2):
            for dy in (0, h / 2): cell(lng + dx, lat + dy, w / 2, h / 2, kw)
    if cells % 25 == 0: print('칸 %d · 호출 %d · 후보 %d' % (cells, calls, len(found)), flush=True)
start_km = 24.0 if ALL else 1.2
h0 = start_km / 111.0; w0 = start_km / (111.0 * math.cos(36.5 * math.pi / 180))
lat = LAT0
while lat < LAT1:
    lng = LNG0
    while lng < LNG1:
        for kw in KEYWORDS: cell(lng, lat, min(w0, LNG1 - lng), min(h0, LAT1 - lat), kw)
        lng += w0
    lat += h0
print('수집 끝 — 칸 %d · 호출 %d · 후보 %d' % (cells, calls, len(found)))

# 2) 기존 센터
def fs_list():
    out = []; tok = None
    while True:
        u = 'https://firestore.googleapis.com/v1/projects/%s/databases/(default)/documents/centers?pageSize=300&key=%s' % (P, APIKEY)
        if tok: u += '&pageToken=' + tok
        r = json.loads(urllib.request.urlopen(u).read().decode())
        out += r.get('documents', []); tok = r.get('nextPageToken')
        if not tok: return out
def fv(f):
    if not f: return None
    for k, v in f.items():
        if k == 'integerValue': return int(v)
        if k in ('stringValue', 'doubleValue', 'booleanValue'): return v
        return v
existing = []
legacy_fix = []   # nameKey/createdBy 가 없는 옛 문서 → --write 때 백필(앱 검색·핵심 집합 쿼리가 이 두 필드를 본다)
for d in fs_list():
    f = d.get('fields', {})
    existing.append({'name': fv(f.get('name')), 'lat': fv(f.get('lat')) or 0, 'lng': fv(f.get('lng')) or 0, 'kakaoId': fv(f.get('kakaoId'))})
    if fv(f.get('kakaoId')) is None and (not fv(f.get('nameKey')) or not fv(f.get('createdBy'))):
        legacy_fix.append((d['name'], str(fv(f.get('name')) or ''), fv(f.get('createdBy'))))
have_k = set(x['kakaoId'] for x in existing if x['kakaoId'])
have_n = set(norm(x['name']) for x in existing)

def dup(d):
    if d['id'] in have_k: return 'kakaoId'
    n = norm(d['place_name'])
    if n in have_n: return 'name'
    la, ln = float(d['y']), float(d['x'])
    for x in existing:
        if x['lat'] and hav(la, ln, float(x['lat']), float(x['lng'])) < 60 and (n[:4] == norm(x['name'])[:4]): return 'near'
    return ''

new = []; skipped = {}
for d in found.values():
    why = dup(d)
    if why: skipped[why] = skipped.get(why, 0) + 1; continue
    new.append(d)
print('기존 %d곳 · 카카오 후보 %d · 중복 제외 %s · 새로 넣을 것 %d' % (len(existing), len(found), skipped, len(new)))
by_gu = {}
for d in new:
    gu = (d['address_name'].split(' ') + ['', ''])[1]
    by_gu[gu] = by_gu.get(gu, 0) + 1
print('구별:', dict(sorted(by_gu.items(), key=lambda x: -x[1])))
for d in new[:8]: print('  예)', d['place_name'], '|', d['category_name'].split('>')[-1].strip(), '|', d['road_address_name'] or d['address_name'])
if not WRITE: print('\n드라이런 끝. 실제로 넣으려면 --write'); sys.exit(0)

# 3) 토큰 (firebase CLI 로그인의 refresh_token 을 빌린다)
cfg = json.load(io.open(os.path.expanduser('~/.config/configstore/firebase-tools.json'), encoding='utf-8'))
rt = cfg['tokens']['refresh_token']
tok = json.loads(urllib.request.urlopen(urllib.request.Request('https://oauth2.googleapis.com/token',
    urllib.parse.urlencode({'client_id': CID, 'client_secret': CSEC, 'refresh_token': rt, 'grant_type': 'refresh_token'}).encode())).read())['access_token']

def val(v):
    if isinstance(v, bool): return {'booleanValue': v}
    if isinstance(v, int): return {'integerValue': str(v)}
    if isinstance(v, float): return {'doubleValue': v}
    if isinstance(v, list): return {'arrayValue': {'values': [val(x) for x in v]}}
    if v is None: return {'nullValue': None}
    return {'stringValue': str(v)}
def typ(cat):
    if '크로스핏' in cat: return '크로스핏'
    return '헬스'
now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
# 옛 문서 백필 — nameKey(검색) + createdBy(핵심 집합 쿼리 `!= seed_kakao` 는 필드가 없으면 빠진다)
if legacy_fix:
    ws = []
    for path, name, cb in legacy_fix:
        fields = {'nameKey': val(name.lower().replace(' ', ''))}
        mask = ['nameKey']
        if not cb: fields['createdBy'] = val('manual'); mask.append('createdBy')
        ws.append({'update': {'name': path, 'fields': fields}, 'updateMask': {'fieldPaths': mask}})
    req = urllib.request.Request('https://firestore.googleapis.com/v1/projects/%s/databases/(default)/documents:batchWrite' % P,
                                 data=json.dumps({'writes': ws}).encode(), method='POST',
                                 headers={'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json'})
    r = json.loads(urllib.request.urlopen(req).read().decode())
    print('옛 문서 백필 %d곳 (실패 %d)' % (len(ws), sum(1 for s in r.get('status', []) if s.get('code', 0))))
done = 0; fail = 0
for i in range(0, len(new), 100):
    writes = []
    for d in new[i:i + 100]:
        gu = (d['address_name'].split(' ') + ['', ''])[1].replace('구', '')
        fields = {
            'name': d['place_name'], 'type': typ(d['category_name']), 'loc': gu,
            'addr': d.get('road_address_name') or d.get('address_name') or '',
            'lat': float(d['y']), 'lng': float(d['x']),
            'img': '', 'rating': 0, 'reviews': 0, 'members': [], 'partner': False, 'partnerPosts': [], 'reviewList': [],
            'phone': d.get('phone') or '', 'kakaoId': d['id'], 'kakaoUrl': d.get('place_url') or '',
            'nameKey': d['place_name'].lower().replace(' ', ''),   # 앱 searchCenters 가 앞부분 검색하는 키
            'g': '%d_%d' % (math.floor(float(d['y']) * 50), math.floor(float(d['x']) * 50)),   # 앱 loadCentersNear 격자 칸(≈2.2km)
            'source': 'kakao', 'createdBy': 'seed_kakao', 'createdAt': {'timestampValue': now}
        }
        fs = {k: (v if k == 'createdAt' else val(v)) for k, v in fields.items()}
        writes.append({'update': {'name': 'projects/%s/databases/(default)/documents/centers/kk_%s' % (P, d['id']), 'fields': fs},
                       'currentDocument': {'exists': False}})
    req = urllib.request.Request('https://firestore.googleapis.com/v1/projects/%s/databases/(default)/documents:batchWrite' % P,
                                 data=json.dumps({'writes': writes}).encode(), method='POST',
                                 headers={'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json'})
    try:
        r = json.loads(urllib.request.urlopen(req).read().decode())
        for st in r.get('status', []):
            if st.get('code', 0) == 0: done += 1
            else: fail += 1
    except urllib.error.HTTPError as e:
        print('batch 실패', e.code, e.read().decode()[:300]); fail += len(writes)
    print('\r쓴 것 %d · 실패 %d' % (done, fail), end='', flush=True)
print('\n완료. 도감에 %d곳 추가됨' % done)
