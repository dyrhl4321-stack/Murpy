# -*- coding: utf-8 -*-
"""머피 적립 장부(ledger) 조회 — C2 잠금 전 '서버 판정이 앱과 맞는가' 확인용.

    python tools/read_ledger.py            # 최근 3일
    python tools/read_ledger.py 7          # 최근 7일

찍히는 링크를 브라우저에서 열고 관리자 계정으로 로그인하면 나머지는 자동이다.
(deploy_firestore_rules.py 와 **같은 OAuth 흐름**이다 — 이 PC 엔 firebase CLI 가 없다.)

★이게 왜 필요한가.
  functions/index.js 의 earn 은 EARN_LIVE=true 라 이미 서버가 직접 지급하고,
  지급할 때마다 ledger 에 {claimed(앱이 요구한 값), allowed(서버가 인정한 값), why} 를 남긴다.
  규칙에서 클라이언트 credits 증가를 막기 **전에** 확인해야 하는 것은 딱 하나다:
    claimed 와 allowed 가 어긋나는 건이 얼마나 되는가.
  어긋남이 많으면 = 서버 상한표(EARN_CAPS)가 앱(CREDIT_*)과 다르다는 뜻이고,
  그 상태로 잠그면 **정상 적립이 조용히 사라진다.**

★why 값 읽는 법
  ''(빈값)   정상 — claimed 를 그대로 인정
  over_max   앱이 상한보다 크게 요구 → EARN_CAPS[reason].max 가 앱 CREDIT_* 보다 작다
  day_cap    하루 횟수 초과 → perDay 가 앱보다 빡빡하다
  dup_key    같은 key 재요청(중복 방지가 일한 것). 정상일 수 있다

★백그라운드로 돌리지 말 것 — stdout 이 끝날 때까지 안 보여서 눌러야 할 링크를 못 본다.
"""
import io, os, sys, json, secrets, http.server, urllib.parse, urllib.request, urllib.error
import datetime, collections

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

CID = '563584335869-fgrhgmd47bqnekij5i8b5pr03ho849e6.apps.googleusercontent.com'
CSEC = 'j9iVZfS8kkCEFUPaAeJV0sAi'
PROJECT = 'murpyprototype'
REDIRECT = 'http://localhost:9005'
HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = ('https://firestore.googleapis.com/v1/projects/' + PROJECT
        + '/databases/(default)/documents')

DAYS = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 3

# ★날짜 경계는 functions/index.js 의 dayKey 와 **같은 식**이어야 한다.
#   KST(+9) 기준 새벽 5시에 날이 바뀐다 → UTC 에 +9h -5h.
_now = datetime.datetime.utcnow() + datetime.timedelta(hours=9) - datetime.timedelta(hours=5)
DAY_KEYS = [(_now - datetime.timedelta(days=i)).strftime('%Y-%m-%d') for i in range(DAYS)]
print('장부 조회 대상 %d일: %s' % (DAYS, ', '.join(DAY_KEYS)), flush=True)

# ───────────────────────── OAuth (deploy_firestore_rules.py 와 동일) ─────────────────────────
# ★★scope 는 반드시 cloud-platform 이다. datastore 로 두면 **로그인 화면에서 막힌다**
#   (대표 9-02 화면: "액세스 차단됨: 승인 오류"). 이 CID/CSEC 는 firebase-tools 의 공개 상수인데,
#   그 OAuth 클라이언트에 datastore 범위가 승인돼 있지 않기 때문이다.
#   같은 폴더의 deploy_firestore_rules.py · deploy_rtdb_rules.py · enable_storage.py 는
#   처음부터 cloud-platform 이었다 — 이 파일만 달라서 **한 번도 돌아본 적이 없었다.**
#   cloud-platform 은 datastore 를 포함하므로 Firestore 읽기에 부족하지 않다.
STATE = secrets.token_urlsafe(12)
AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode({
    'client_id': CID, 'redirect_uri': REDIRECT, 'response_type': 'code',
    'scope': 'email openid https://www.googleapis.com/auth/cloud-platform',
    'state': STATE, 'access_type': 'offline', 'prompt': 'consent'})
print('아래 링크를 브라우저에서 열 것 (관리자 계정으로 로그인):', flush=True)
print(AUTH_URL, flush=True)
try:
    io.open(os.path.join(HERE, '_oauth_url.txt'), 'w', encoding='utf-8').write(AUTH_URL)
except Exception:
    pass

got = {}


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        ok = q.get('state', [''])[0] == STATE and q.get('code', [''])[0]
        if ok:
            got['code'] = q['code'][0]
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        msg = '확인됐어요. 이 창을 닫으셔도 됩니다.' if ok else '실패했어요. 터미널을 봐주세요.'
        self.wfile.write(('<meta charset=utf-8><body style="font-family:sans-serif;'
                          'padding:40px;text-align:center"><h2>' + msg + '</h2>').encode('utf-8'))


srv = http.server.HTTPServer(('127.0.0.1', 9005), H)
srv.timeout = 300
while 'code' not in got:
    srv.handle_request()

tok = json.loads(urllib.request.urlopen(urllib.request.Request(
    'https://oauth2.googleapis.com/token',
    urllib.parse.urlencode({'code': got['code'], 'client_id': CID, 'client_secret': CSEC,
                            'redirect_uri': REDIRECT,
                            'grant_type': 'authorization_code'}).encode())).read())['access_token']
print('토큰 받음', flush=True)
HDR = {'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json'}


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'),
                                 method='POST', headers=HDR)
    try:
        return json.loads(urllib.request.urlopen(req).read().decode())
    except urllib.error.HTTPError as e:
        raise SystemExit('POST %s 실패 %d%s%s' % (url, e.code, chr(10), e.read().decode()[:800]))


def val(v):
    """Firestore REST 의 타입 봉투를 벗긴다."""
    if v is None:
        return None
    for k in ('stringValue', 'booleanValue', 'timestampValue'):
        if k in v:
            return v[k]
    if 'integerValue' in v:
        return int(v['integerValue'])
    if 'doubleValue' in v:
        return float(v['doubleValue'])
    if 'nullValue' in v:
        return None
    return v


# ───────────────────────── 조회 ─────────────────────────
# day IN [...] 단일 필드 필터 — orderBy 를 안 붙여야 복합 색인이 필요 없다.
# (색인 없으면 400 이 나고, 그걸 만들려면 또 배포가 필요하다.)
q = {'structuredQuery': {
    'from': [{'collectionId': 'ledger'}],
    'where': {'fieldFilter': {
        'field': {'fieldPath': 'day'},
        'op': 'IN',
        'value': {'arrayValue': {'values': [{'stringValue': d} for d in DAY_KEYS]}}}},
    'limit': 5000}}

rows = []
for item in post(DOCS + ':runQuery', q):
    f = (item.get('document') or {}).get('fields')
    if not f:
        continue
    rows.append({k: val(f.get(k)) for k in
                 ('uid', 'reason', 'key', 'day', 'claimed', 'allowed', 'why', 'mode')})

print('', flush=True)
print('=' * 72, flush=True)
if not rows:
    print('장부에 이 기간 기록이 없습니다.', flush=True)
    print('  → 앱이 earn 을 안 부르고 있거나(배포 확인), 이 기간에 적립이 없었습니다.', flush=True)
    raise SystemExit(0)

live = [r for r in rows if r.get('mode') == 'live']
shadow = [r for r in rows if r.get('mode') != 'live']
print('총 %d건 (live %d · shadow %d) · 사용자 %d명'
      % (len(rows), len(live), len(shadow), len(set(r.get('uid') for r in rows))), flush=True)

# ① why 분포 — 이게 이번 확인의 본론이다
print('', flush=True)
print('── why 분포 (live 기준) ──', flush=True)
whys = collections.Counter((r.get('why') or '(정상)') for r in live)
for w, n in whys.most_common():
    print('  %-10s %5d건  (%4.1f%%)' % (w, n, 100.0 * n / max(1, len(live))), flush=True)

# ② 사유별로 claimed 와 allowed 가 어긋난 것 — 상한표가 앱과 다른 지점
print('', flush=True)
print('── 사유별 claimed vs allowed (live) ──', flush=True)
by = collections.defaultdict(lambda: {'n': 0, 'c': 0, 'a': 0, 'bad': 0, 'maxc': 0, 'whys': collections.Counter()})
for r in live:
    b = by[r.get('reason') or '?']
    c, a = int(r.get('claimed') or 0), int(r.get('allowed') or 0)
    b['n'] += 1
    b['c'] += c
    b['a'] += a
    b['maxc'] = max(b['maxc'], c)
    if c != a:
        b['bad'] += 1
        b['whys'][r.get('why') or '(빈값)'] += 1
print('  %-14s %5s %8s %8s %7s %6s  %s' % ('사유', '건수', '요구합', '지급합', '어긋남', '최대요구', 'why'), flush=True)
for reason, b in sorted(by.items(), key=lambda kv: -kv[1]['bad']):
    mark = '  ← 확인' if b['bad'] else ''
    print('  %-14s %5d %8d %8d %7d %6d  %s%s'
          % (reason, b['n'], b['c'], b['a'], b['bad'], b['maxc'],
             ', '.join('%s×%d' % (w, n) for w, n in b['whys'].most_common()) or '-', mark), flush=True)

# ③ 판정
print('', flush=True)
print('=' * 72, flush=True)
bad = sum(b['bad'] for b in by.values())
dup = sum(1 for r in live if (r.get('why') or '') == 'dup_key')
real_bad = bad - dup                      # dup_key 는 중복방지가 일한 것 → 어긋남으로 안 센다
if not live:
    print('판정: live 기록이 0건 — EARN_LIVE 가 켜졌는데도 안 들어왔다면 배포부터 확인할 것.', flush=True)
elif real_bad == 0:
    print('판정: ★잠가도 됩니다. dup_key 를 뺀 어긋남 0건 — 서버 상한표가 앱과 일치합니다.', flush=True)
else:
    print('판정: ★아직 잠그면 안 됩니다. dup_key 를 뺀 어긋남 %d건.' % real_bad, flush=True)
    print('       위 표에서 "← 확인" 붙은 사유의 EARN_CAPS(functions/index.js) 를', flush=True)
    print('       앱의 CREDIT_*(index.html) 와 맞춘 뒤 다시 재보세요.', flush=True)
print('=' * 72, flush=True)
