# -*- coding: utf-8 -*-
"""기존 커마 시트 재처리 — finalize.demagenta 를 Storage 의 faces/{uid}/{charId}/* 에 적용해 **같은 주소**로 다시 올린다.

    PYTHONIOENCODING=utf-8 python tools/face_reprocess_demagenta.py            # 전체 훑어 보고만(dry-run)
    PYTHONIOENCODING=utf-8 python tools/face_reprocess_demagenta.py --write    # 실제 재업로드
    PYTHONIOENCODING=utf-8 python tools/face_reprocess_demagenta.py --uid <uid> --write

★같은 객체 이름으로 올리고 firebaseStorageDownloadTokens 메타데이터를 **원래 토큰으로 유지**해서 users.characterSheet /
  faceChars.sheetUrl 을 안 바꿔도 된다(주소 = 경로 + token). 폰은 ?v 가 같아 SW 캐시(IMG_CACHE)에 옛 그림이 남을 수 있으니
  faceChars 문서 sheetUrl 에 `&r=<시각>` 을 덧붙여 캐시 키를 바꾼다(--write 때).
관리자 OAuth 는 tools/gcloud_oauth.py(저장 토큰). 실행 권한은 실행하는 창의 승인 설정을 따른다.
"""
import io, os, sys, json, time, argparse, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, 'functions-py'))
from gcloud_oauth import get_token
from facegen import finalize
BUCKET = 'murpyprototype.firebasestorage.app'
FS = 'https://firestore.googleapis.com/v1/projects/murpyprototype/databases/(default)/documents/'

def api(tok, url, data=None, method='GET', ctype='application/json'):
    req = urllib.request.Request(url, data=data, method=method, headers={'Authorization': 'Bearer ' + tok, 'Content-Type': ctype})
    return json.loads(urllib.request.urlopen(req).read().decode())

def obj_meta(tok, name):
    return api(tok, 'https://storage.googleapis.com/storage/v1/b/%s/o/%s' % (BUCKET, urllib.parse.quote(name, safe='')))

def reupload(tok, name, data, token):
    # 멀티파트: 메타데이터(토큰 유지) + 본문
    boundary = 'murpy' + str(int(time.time()))
    meta = json.dumps({'name': name, 'contentType': 'image/png', 'metadata': {'firebaseStorageDownloadTokens': token}}).encode()
    body = b'--' + boundary.encode() + b'\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n' + meta + b'\r\n--' + boundary.encode() + b'\r\nContent-Type: image/png\r\n\r\n' + data + b'\r\n--' + boundary.encode() + b'--'
    url = 'https://storage.googleapis.com/upload/storage/v1/b/%s/o?uploadType=multipart' % BUCKET
    return api(tok, url, body, 'POST', 'multipart/related; boundary=' + boundary)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--uid'); ap.add_argument('--write', action='store_true'); a = ap.parse_args()
    tok = get_token()
    users = [a.uid] if a.uid else [d['name'].split('/')[-1] for d in api(tok, FS + 'users?pageSize=300&mask.fieldPaths=nickname').get('documents', [])]
    done = 0
    for uid in users:
        docs = api(tok, FS + 'users/%s/faceChars?pageSize=50' % uid).get('documents', [])
        for d in docs:
            cid = d['name'].split('/')[-1]; f = d['fields']
            urls = {'sheet': f.get('sheetUrl', {}).get('stringValue'), 'hair': f.get('hairUrl', {}).get('stringValue')}
            for k, url in urls.items():
                if not url or 'firebasestorage' not in url: continue
                name = urllib.parse.unquote(url.split('/o/')[1].split('?')[0]); token = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get('token', [''])[0]
                tmp = os.path.join(os.environ.get('TEMP', '.'), 'reproc_%s_%s_%s.png' % (uid[:6], cid, k))
                open(tmp, 'wb').write(urllib.request.urlopen(url).read())
                r = finalize.demagenta(tmp, tmp)
                print(uid[:8], cid, k, r, '→ write' if a.write else '(dry)')
                if a.write and (r['semi'] or r['darkPurple'] or r['edgeMagenta']):
                    reupload(tok, name, open(tmp, 'rb').read(), token); done += 1
            if a.write:
                # sheetUrl 에 r= 를 붙여 폰 캐시 키를 바꾼다(faceChars 는 관리자만 update 가능 — 이 스크립트가 관리자 토큰)
                patch = {'fields': {}}
                for k, fld in (('sheet', 'sheetUrl'), ('hair', 'hairUrl')):
                    u = urls[k]
                    if u: patch['fields'][fld] = {'stringValue': u.split('&r=')[0] + '&r=' + str(int(time.time()))}
                if patch['fields']:
                    mask = '&'.join('updateMask.fieldPaths=' + k for k in patch['fields'])
                    api(tok, FS + 'users/%s/faceChars/%s?%s' % (uid, cid, mask), json.dumps(patch).encode(), 'PATCH')
    print('재업로드', done, '개')

if __name__ == '__main__':
    main()
