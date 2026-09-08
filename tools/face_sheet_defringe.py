"""얼굴커마 시트 후광 재처리 (2026-09-08 대표 승인: "너가 하도록")

증상: 명예의 전당·필드에서 커마 캐릭터 머리 외곽에 마젠타/보라 후광. 시트 자체에 반투명 가장자리 + 보라끼 외곽선이 박혀 있다.
하는 일: users 중 characterSheet 가 있는 전원 →
  1) 원본 다운로드 → scratchpad/face_backup/<uid>.png 백업
  2) 수술: 알파 128 이진화 + 불투명 보라끼 어두운 픽셀(r>g+10 & b>g+10 & r+g+b<330) 무채색화
  3) Storage 에 같은 폴더 sheet_v2.png 로 업로드(원본은 그대로 둔다) → 새 다운로드 토큰 URL
  4) users/{uid}.characterSheet 와 users/{uid}/faceChars/{fid}.sheetUrl 을 새 URL 로 PATCH
사용: python tools/face_sheet_defringe.py [--dry]   (--dry 는 업로드·PATCH 없이 수술 결과만 저장)
"""
import sys, json, urllib.request, urllib.parse, io, os, re
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__)); import rv_picks
DRY = '--dry' in sys.argv
S = os.environ.get('MW_SCRATCH', 'C:/Users/dyrhl/AppData/Local/Temp/claude/C--Users-dyrhl/20a4c87e-2d13-4b49-900a-95f6f86b3aa2/scratchpad/')
os.makedirs(S + 'face_backup', exist_ok=True); os.makedirs(S + 'face_clean', exist_ok=True)
tok = rv_picks.token(); P = 'murpyprototype'; BK = 'murpyprototype.firebasestorage.app'
H = {'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json'}

def run_query(body):
    req = urllib.request.Request('https://firestore.googleapis.com/v1/projects/%s/databases/(default)/documents:runQuery' % P, data=json.dumps(body).encode(), headers=H)
    return json.loads(urllib.request.urlopen(req).read())

def sv(v): return v.get('stringValue')

def defringe(a):
    a = a.astype(int); r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    purple = (r > g + 10) & (b > g + 10) & (r + g + b < 330) & (al > 0)
    out = a.copy(); out[..., 3] = np.where(al >= 128, 255, 0)
    inner = purple & (out[..., 3] == 255); lum = (r + g + b) // 3
    out[inner, 0] = lum[inner]; out[inner, 1] = lum[inner]; out[inner, 2] = np.minimum(255, lum[inner] + 2)
    return out.astype(np.uint8), int(purple.sum()), int(((al > 0) & (al < 128)).sum())

def upload(path, data):
    req = urllib.request.Request('https://firebasestorage.googleapis.com/v0/b/%s/o?uploadType=media&name=%s' % (BK, urllib.parse.quote(path, safe='')), data=data, headers={'Authorization': 'Bearer ' + tok, 'Content-Type': 'image/png'})
    j = json.loads(urllib.request.urlopen(req).read()); t = j.get('downloadTokens', '').split(',')[0]
    return 'https://firebasestorage.googleapis.com/v0/b/%s/o/%s?alt=media&token=%s' % (BK, urllib.parse.quote(path, safe=''), t)

def patch(docpath, fields):
    body = {'fields': {k: {'stringValue': v} for k, v in fields.items()}}
    url = 'https://firestore.googleapis.com/v1/projects/%s/databases/(default)/documents/%s?%s' % (P, docpath, '&'.join('updateMask.fieldPaths=%s' % k for k in fields))
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=H, method='PATCH'); urllib.request.urlopen(req).read()

res = run_query({"structuredQuery": {"from": [{"collectionId": "users"}], "where": {"fieldFilter": {"field": {"fieldPath": "characterSheet"}, "op": "GREATER_THAN", "value": {"stringValue": ""}}}, "limit": 500}})
users = [(d['document']['name'].split('/')[-1], sv(d['document']['fields'].get('characterSheet', {})), sv(d['document']['fields'].get('nickname', {}))) for d in res if d.get('document')]
print('커마 유저', len(users), 'DRY' if DRY else 'WRITE')
report = []
for uid, url, nick in users:
    if not url or 'faces%2F' not in url: report.append((nick, uid, 'skip(외부 주소)')); continue
    objpath = urllib.parse.unquote(re.search(r'/o/(faces%2F[^?]+)\?', url).group(1))
    if objpath.endswith('_v2.png'): report.append((nick, uid, '이미 v2')); continue
    data = urllib.request.urlopen(url).read(); open(S + 'face_backup/%s.png' % uid, 'wb').write(data)
    o, npx, semi = defringe(np.array(Image.open(io.BytesIO(data)).convert('RGBA')))
    Image.fromarray(o).save(S + 'face_clean/%s.png' % uid)
    if npx < 50 and semi < 50: report.append((nick, uid, '깨끗함(건너뜀)')); continue
    if DRY: report.append((nick, uid, 'dry purple=%d semi=%d' % (npx, semi))); continue
    buf = io.BytesIO(); Image.fromarray(o).save(buf, 'PNG')
    newurl = upload(objpath.rsplit('.', 1)[0] + '_v2.png', buf.getvalue())
    patch('users/%s' % uid, {'characterSheet': newurl})
    parts = objpath.split('/')   # faces/<uid>/<fid>/sheet.png
    if len(parts) >= 4:
        try: patch('users/%s/faceChars/%s' % (uid, parts[2]), {'sheetUrl': newurl})
        except Exception as e: report.append((nick, uid, 'faceChars PATCH 실패 %s' % e))
    report.append((nick, uid, '교체 purple=%d semi=%d' % (npx, semi)))
for r in report: print(*r)
