# -*- coding: utf-8 -*-
"""얼굴 커스터마이징 서버의 비공개 재료를 Storage private/face/ 에 올린다 (1회, 관리자 OAuth 클릭 필요).

    PYTHONIOENCODING=utf-8 python tools/face_upload_private.py

올리는 것 (Murpy_private/제작노하우/얼굴커마-생성설정.txt 에서 읽는다):
    private/face/prompt.txt   [프롬프트] 절 전문
    private/face/base_m.png   [시트] 남 = 생성용 base 시트
    private/face/base_f.png   [시트] 여
★이 저장소는 공개라 프롬프트·생성용 시트를 코드에 못 넣는다. Storage 규칙이 private/ 를 전부 막고 있고,
  서버(Admin SDK)만 읽는다. 프롬프트를 고치면 이 스크립트를 다시 돌리면 된다(재배포 불필요).
OAuth 는 tools/deploy_firestore_rules.py 와 같은 흐름(브라우저 로그인 → localhost:9005).
"""
import io, os, sys, json, secrets, urllib.request, urllib.parse, http.server, threading, webbrowser
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__)); M = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from face_pipeline import load_cfg, PRIV
BUCKET = 'murpyprototype.firebasestorage.app'

# deploy_firestore_rules.py 의 클라이언트 정보를 그대로 쓴다(같은 파일에서 읽는다 — 두 곳에 두지 않는다)
_src = io.open(os.path.join(HERE, 'deploy_firestore_rules.py'), encoding='utf-8').read()
def _const(name):
    import re
    m = re.search(r"^%s\s*=\s*'([^']+)'" % name, _src, re.M); return m.group(1) if m else None
CID, CSEC, REDIRECT = _const('CID'), _const('CSEC'), _const('REDIRECT') or 'http://localhost:9005'
if not CID or not CSEC: raise SystemExit('deploy_firestore_rules.py 에서 CID/CSEC 를 못 읽었다')

def oauth_token():
    state = secrets.token_urlsafe(12)
    url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode({
        'client_id': CID, 'redirect_uri': REDIRECT, 'response_type': 'code',
        'scope': 'email openid https://www.googleapis.com/auth/cloud-platform', 'state': state, 'access_type': 'offline', 'prompt': 'consent'})
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
    tok = json.loads(urllib.request.urlopen(urllib.request.Request('https://oauth2.googleapis.com/token',
        urllib.parse.urlencode({'code': got['code'], 'client_id': CID, 'client_secret': CSEC, 'redirect_uri': REDIRECT,
                                'grant_type': 'authorization_code'}).encode())).read())['access_token']
    print('토큰 받음', flush=True); return tok

def upload(tok, path, data, ctype):
    url = 'https://storage.googleapis.com/upload/storage/v1/b/%s/o?uploadType=media&name=%s' % (BUCKET, urllib.parse.quote(path, safe=''))
    req = urllib.request.Request(url, data=data, method='POST', headers={'Authorization': 'Bearer ' + tok, 'Content-Type': ctype})
    r = json.loads(urllib.request.urlopen(req).read().decode()); print('  올림', path, r.get('size'), 'bytes')

if __name__ == '__main__':
    cfg = load_cfg()
    items = [('private/face/prompt.txt', cfg['prompt'].encode('utf-8'), 'text/plain; charset=utf-8'),
             ('private/face/base_m.png', open(cfg['남'], 'rb').read(), 'image/png'),
             ('private/face/base_f.png', open(cfg['여'], 'rb').read(), 'image/png')]
    print('프롬프트 %d자 · base 남 %dKB · 여 %dKB' % (len(cfg['prompt']), len(items[1][1]) // 1024, len(items[2][1]) // 1024))
    tok = oauth_token()
    for p, d, c in items: upload(tok, p, d, c)
    print('완료 — 서버는 다음 신청부터 이 재료를 읽는다')
