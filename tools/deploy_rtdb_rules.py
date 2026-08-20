# -*- coding: utf-8 -*-
"""RTDB(실시간 DB) 규칙 배포 — 이 PC 에는 firebase CLI 가 없다. 대표 클릭 1회로 끝난다.

    python tools/deploy_rtdb_rules.py

찍히는 링크를 브라우저에서 열고 관리자 계정으로 로그인하면 나머지는 자동이다.

★Firestore 와 **엔드포인트가 다르다.** firebaserules.googleapis.com 이 아니라
  데이터베이스 자신에게 `.settings/rules.json` 으로 직접 PUT 한다. 여기서 헤매기 쉽다.
★올리기 전에 json.loads 로 검사한다 — 깨진 JSON 을 올리면 DB 가 잠긴다.
★"status:ok" 응답만 믿지 말 것. 되읽어서 실제 값을 확인한다.
※CID/CSEC 는 firebase-tools npm 패키지에 그대로 들어 있는 공개 상수다. 비밀이 아니다.
"""
import io, os, json, secrets, http.server, urllib.parse, urllib.request

CID = '563584335869-fgrhgmd47bqnekij5i8b5pr03ho849e6.apps.googleusercontent.com'
CSEC = 'j9iVZfS8kkCEFUPaAeJV0sAi'
DB = 'https://murpyprototype-default-rtdb.asia-southeast1.firebasedatabase.app'
REDIRECT = 'http://localhost:9005'
HERE = os.path.dirname(os.path.abspath(__file__))
RULES = io.open(os.path.join(HERE, '..', 'database.rules.json'), encoding='utf-8').read()

json.loads(RULES)                       # 깨진 걸 올리면 DB 가 잠긴다. 반드시 먼저.
STATE = secrets.token_urlsafe(12)
print('아래 링크를 브라우저에서 열 것:', flush=True)
print('https://accounts.google.com/o/oauth2/auth?' + urllib.parse.urlencode({
    'client_id': CID, 'redirect_uri': REDIRECT, 'response_type': 'code',
    'scope': 'email openid https://www.googleapis.com/auth/cloud-platform',
    'state': STATE, 'access_type': 'offline', 'prompt': 'consent'}), flush=True)

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

put = urllib.request.Request(DB + '/.settings/rules.json', data=RULES.encode('utf-8'), method='PUT',
                             headers={'Authorization': 'Bearer ' + tok,
                                      'Content-Type': 'application/json'})
print('PUT 응답:', urllib.request.urlopen(put).read().decode(), flush=True)

back = json.loads(urllib.request.urlopen(urllib.request.Request(
    DB + '/.settings/rules.json', headers={'Authorization': 'Bearer ' + tok})).read().decode())
print('되읽음:', json.dumps(back['rules'].get('roomLive', {}), ensure_ascii=False)[:300], flush=True)
