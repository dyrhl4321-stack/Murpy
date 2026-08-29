# -*- coding: utf-8 -*-
"""centers 문서에 격자 칸 g(= floor(lat*50)_floor(lng*50), ≈2.2km) 와 nameKey 가 없으면 채운다.

    python tools/centers/backfill_geo.py

앱 loadCentersNear 가 `where('g','in',[...])` 로 주변을 읽는다(8-29). g 가 없는 문서는 주변 검색에 안 잡힌다.
쓰기는 firebase CLI 로그인의 refresh_token 을 빌린 cloud-platform 토큰(IAM)으로 한다.
"""
import io, os, sys, json, math, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding='utf-8')
P = 'murpyprototype'; APIKEY = 'AIzaSyBvMB4T-ApzHDsfmBx4f5HpPmgkqlcZ7VQ'
CID = '563584335869-fgrhgmd47bqnekij5i8b5pr03ho849e6.apps.googleusercontent.com'
CSEC = 'j9iVZfS8kkCEFUPaAeJV0sAi'

def fv(f):
    if not f: return None
    for k, v in f.items():
        if k == 'integerValue': return int(v)
        return v
docs = []; tok = None
while True:
    u = 'https://firestore.googleapis.com/v1/projects/%s/databases/(default)/documents/centers?pageSize=300&key=%s' % (P, APIKEY)
    if tok: u += '&pageToken=' + tok
    r = json.loads(urllib.request.urlopen(u).read().decode())
    docs += r.get('documents', []); tok = r.get('nextPageToken')
    if not tok: break
todo = []
for d in docs:
    f = d.get('fields', {})
    lat, lng = fv(f.get('lat')), fv(f.get('lng'))
    fields = {}; mask = []
    if isinstance(lat, (int, float)) and isinstance(lng, (int, float)) and lat and not fv(f.get('g')):
        fields['g'] = {'stringValue': '%d_%d' % (math.floor(lat * 50), math.floor(lng * 50))}; mask.append('g')
    if not fv(f.get('nameKey')) and fv(f.get('name')):
        fields['nameKey'] = {'stringValue': str(fv(f.get('name'))).lower().replace(' ', '')}; mask.append('nameKey')
    if mask: todo.append({'update': {'name': d['name'], 'fields': fields}, 'updateMask': {'fieldPaths': mask}})
print('전체 %d · 채울 것 %d' % (len(docs), len(todo)))
if not todo: sys.exit(0)
cfg = json.load(io.open(os.path.expanduser('~/.config/configstore/firebase-tools.json'), encoding='utf-8'))
tok = json.loads(urllib.request.urlopen(urllib.request.Request('https://oauth2.googleapis.com/token',
    urllib.parse.urlencode({'client_id': CID, 'client_secret': CSEC, 'refresh_token': cfg['tokens']['refresh_token'],
                            'grant_type': 'refresh_token'}).encode())).read())['access_token']
done = 0
for i in range(0, len(todo), 400):
    req = urllib.request.Request('https://firestore.googleapis.com/v1/projects/%s/databases/(default)/documents:batchWrite' % P,
                                 data=json.dumps({'writes': todo[i:i + 400]}).encode(), method='POST',
                                 headers={'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json'})
    r = json.loads(urllib.request.urlopen(req).read().decode())
    done += sum(1 for s in r.get('status', []) if not s.get('code'))
    print('\r채움 %d' % done, end='', flush=True)
print('\n완료')
