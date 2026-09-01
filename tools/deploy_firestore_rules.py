# -*- coding: utf-8 -*-
"""Firestore / Storage 규칙 배포 — 이 PC 에는 firebase CLI 가 없다. 대표 클릭 1회로 끝난다.

    python tools/deploy_firestore_rules.py            # firestore.rules
    python tools/deploy_firestore_rules.py storage    # storage.rules (사진 업로드)

찍히는 링크를 브라우저에서 열고 관리자 계정으로 로그인하면 나머지는 자동이다.

★RTDB 와 **엔드포인트가 다르다.** RTDB 는 DB 자신에게 PUT 하지만,
  Firestore 는 firebaserules.googleapis.com 에 ①ruleset 을 만들고 ②release 를 그리로 옮긴다.
★릴리스 PATCH body 는 **한 겹 감싼다.** Release 가 아니라 UpdateReleaseRequest 다:
  {"release": {"name": ".../releases/cloud.firestore", "rulesetName": ".../rulesets/<id>"}}
  안 감싸면 `Unknown name "rulesetName": Cannot find field` 400 이 난다.
★배포 뒤 **되읽어서 확인**한다. "만들었다"는 응답만 믿지 말 것.
★백그라운드로 돌리면 stdout 이 끝날 때까지 안 보인다(flush 를 줘도). 멈춘 것처럼 보여도
  죽이지 말 것 — 완료되면 로그가 한 번에 나온다.
※CID/CSEC 는 firebase-tools npm 패키지에 그대로 들어 있는 공개 상수다. 비밀이 아니다.

이 스크립트를 스크래치패드에 두지 말 것 — 세션이 끝나면 사라져서 매번 새로 짜게 된다.
(RTDB 쪽에서 실제로 하루에 두 번 새로 짠 적이 있다. 그래서 저장소에 둔다.)
"""
import io, os, json, secrets, http.server, urllib.parse, urllib.request

CID = '563584335869-fgrhgmd47bqnekij5i8b5pr03ho849e6.apps.googleusercontent.com'
CSEC = 'j9iVZfS8kkCEFUPaAeJV0sAi'
PROJECT = 'murpyprototype'
API = 'https://firebaserules.googleapis.com/v1/projects/' + PROJECT
REDIRECT = 'http://localhost:9005'
HERE = os.path.dirname(os.path.abspath(__file__))
import sys
# 대상 = firestore(기본) | storage. Storage 는 릴리스 이름에 **버킷이 들어간다**.
TARGET = (sys.argv[1] if len(sys.argv) > 1 else 'firestore').lower()
BUCKET = 'murpyprototype.firebasestorage.app'
if TARGET == 'storage':
    RULE_FILE, RELEASE, RULE_NAME = 'storage.rules', 'firebase.storage/' + BUCKET, 'storage.rules'
else:
    RULE_FILE, RELEASE, RULE_NAME = 'firestore.rules', 'cloud.firestore', 'firestore.rules'
PATH = os.path.join(HERE, '..', RULE_FILE)
RULES = io.open(PATH, encoding='utf-8').read()

# 최소한의 사전 검사 — 괄호가 안 맞으면 서버가 400 을 주기 전에 여기서 잡는다.
for name, o, c in (('중괄호', '{', '}'), ('괄호', '(', ')'), ('대괄호', '[', ']')):
    if RULES.count(o) != RULES.count(c):
        raise SystemExit('%s 개수가 안 맞습니다 (%d vs %d)' % (name, RULES.count(o), RULES.count(c)))
print('%s %d자 · 규칙 %d줄 · 대상 %s' % (RULE_FILE, len(RULES), RULES.count('allow '), RELEASE), flush=True)

STATE = secrets.token_urlsafe(12)
AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode({
    'client_id': CID, 'redirect_uri': REDIRECT, 'response_type': 'code',
    'scope': 'email openid https://www.googleapis.com/auth/cloud-platform',
    'state': STATE, 'access_type': 'offline', 'prompt': 'consent'})
print('아래 링크를 브라우저에서 열 것 (관리자 계정으로 로그인):', flush=True)
print(AUTH_URL, flush=True)
# ★백그라운드로 돌리면 stdout 이 끝날 때까지 안 보인다. 그래서 링크를 파일로도 남긴다 —
#   안 그러면 대표가 눌러야 할 링크를 아무도 못 본다.
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


def call(url, body=None, method='GET', soft=False):
    """soft=True 면 실패해도 죽지 않고 None 을 준다(릴리스가 없을 때 만들어 보려고)."""
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=HDR)
    try:
        return json.loads(urllib.request.urlopen(req).read().decode())
    except urllib.error.HTTPError as e:
        msg = e.read().decode()[:600].replace(chr(10), ' ')
        if soft:
            print('   (%s %d) %s' % (method, e.code, msg[:140]), flush=True)
            return None
        raise SystemExit('%s %s 실패 %d' % (method, url, e.code) + chr(10) + msg)


# ① ruleset 만들기
rs = call(API + '/rulesets', {'source': {'files': [
    {'name': RULE_NAME, 'content': RULES}]}}, 'POST')
print('ruleset 생성:', rs['name'], flush=True)

# ② release 를 그 ruleset 으로 옮기기. ★body 를 한 겹 감싼다(UpdateReleaseRequest).
# ★Storage 는 **릴리스가 아직 없을 수 있다**(한 번도 안 올린 버킷). 그러면 PATCH 가 404 다 →
#   POST 로 새로 만든다. 버킷 이름도 프로젝트마다 갈린다(.firebasestorage.app / .appspot.com)
#   — 둘 다 시도한다. 2026-08-25 에 여기서 404 로 한 번 실패했다.
cands = [RELEASE]
if TARGET == 'storage':
    cands.append('firebase.storage/' + PROJECT + '.appspot.com')

rel = None
for cand in cands:
    url = API + '/releases/' + cand
    short = url.replace('https://firebaserules.googleapis.com/v1/', '')
    print('시도:', cand, flush=True)
    out = call(url, {'release': {'name': short, 'rulesetName': rs['name']}}, 'PATCH', soft=True)
    if out is None:      # 릴리스가 없다 → 새로 만든다
        out = call(API + '/releases', {'name': short, 'rulesetName': rs['name']}, 'POST', soft=True)
    if out is not None:
        rel = url
        print('release 설정:', out.get('rulesetName'), flush=True)
        break
if rel is None:
    raise SystemExit('릴리스를 만들지도 갱신하지도 못했습니다. 위 응답을 확인할 것.')

# ③ 되읽어 확인 — "만들었다"는 응답만 믿지 않는다
now = call(rel)
ok = now.get('rulesetName') == rs['name']
print('되읽음:', now.get('rulesetName'), '·', '일치' if ok else '★불일치', flush=True)
print('배포 %s' % ('완료' if ok else '실패 — 위 값을 확인할 것'), flush=True)
