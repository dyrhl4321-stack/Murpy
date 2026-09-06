# -*- coding: utf-8 -*-
"""관리자 OAuth 토큰 — 한 번 로그인하면 refresh token 을 저장해 **다음부터는 클릭 없이** 액세스 토큰을 받는다.

    from gcloud_oauth import get_token
    tok = get_token()          # 저장된 refresh 가 있으면 조용히 갱신, 없으면 브라우저 로그인 1회

★왜 (2026-09-07): 규칙 게시·비공개 재료 업로드마다 대표가 브라우저 로그인을 눌러야 했다(하루 4번).
  Google OAuth 는 access_type=offline 로 받은 refresh_token 을 다시 쓸 수 있다.
저장 위치 = ~/.config/murpy/gcloud_refresh.json (이 PC 만, 저장소 밖). 지우면 다시 로그인.
클라이언트 id/secret 은 firebase CLI 의 공개 installed-app 클라이언트(deploy_firestore_rules.py 와 같은 값).
"""
import io, os, json, secrets, urllib.request, urllib.parse, http.server
CID = '563584335869-fgrhgmd47bqnekij5i8b5pr03ho849e6.apps.googleusercontent.com'
CSEC = 'j9iVZfS8kkCEFUPaAeJV0sAi'
REDIRECT = 'http://localhost:9005'
SCOPE = 'email openid https://www.googleapis.com/auth/cloud-platform'
CACHE = os.path.join(os.path.expanduser('~'), '.config', 'murpy', 'gcloud_refresh.json')

def _post(url, form):
    req = urllib.request.Request(url, urllib.parse.urlencode(form).encode())
    return json.loads(urllib.request.urlopen(req).read().decode())

def _refresh(rt):
    r = _post('https://oauth2.googleapis.com/token', {'refresh_token': rt, 'client_id': CID, 'client_secret': CSEC, 'grant_type': 'refresh_token'})
    return r.get('access_token')

def _browser_login():
    state = secrets.token_urlsafe(12)
    url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode({
        'client_id': CID, 'redirect_uri': REDIRECT, 'response_type': 'code', 'scope': SCOPE,
        'state': state, 'access_type': 'offline', 'prompt': 'consent'})
    print('아래 링크를 브라우저에서 열 것 (관리자 계정으로 로그인):', flush=True); print(url, flush=True)
    got = {}
    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            ok = q.get('state', [''])[0] == state and q.get('code', [''])[0]
            if ok: got['code'] = q['code'][0]
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers()
            self.wfile.write(('<h2>%s</h2>' % ('완료 — 창을 닫아도 됩니다' if ok else '실패')).encode('utf-8'))
    srv = http.server.HTTPServer(('127.0.0.1', 9005), H)
    while 'code' not in got: srv.handle_request()
    r = _post('https://oauth2.googleapis.com/token', {'code': got['code'], 'client_id': CID, 'client_secret': CSEC,
                                                      'redirect_uri': REDIRECT, 'grant_type': 'authorization_code'})
    if r.get('refresh_token'):
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        io.open(CACHE, 'w', encoding='utf-8').write(json.dumps({'refresh_token': r['refresh_token']}))
        print('토큰 저장됨 — 다음부터는 로그인 없이 진행', flush=True)
    return r['access_token']

def get_token():
    try:
        rt = json.loads(io.open(CACHE, encoding='utf-8').read()).get('refresh_token')
        if rt:
            tok = _refresh(rt)
            if tok: print('저장된 토큰으로 진행', flush=True); return tok
    except Exception:
        pass
    return _browser_login()
