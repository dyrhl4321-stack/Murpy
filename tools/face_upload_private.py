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

from gcloud_oauth import get_token as oauth_token   # 저장된 refresh 토큰이 있으면 클릭 없이

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
