# -*- coding: utf-8 -*-
"""Firebase Storage 기본 버킷 만들기 — 콘솔에 안 들어가고 API 로 켠다.

    python tools/enable_storage.py

대표 클릭 1회(OAuth)면 나머지는 자동이다.

★왜 필요했나 (2026-08-25)
  사진 업로드를 imgBB 에서 Firebase Storage 로 옮겼는데 계속 실패했다.
  찔러보니 **버킷이 아예 없었다** — 이 프로젝트는 Storage 를 한 번도 켠 적이 없다.
  firebasestorage.googleapis.com/v0/b/{bucket}/o 가 두 이름 모두 404 였다.
  ★규칙 배포가 "완료"로 떴던 건 Rules API 가 **버킷 존재를 검사하지 않기** 때문이다.
    "배포됐다"는 "된다"는 뜻이 아니다. 여기서 한나절을 헤맸다.

★결제(Blaze)가 필요할 수 있다. 무료(Spark) 플랜이면 버킷 생성이 거부된다 —
  그 경우 이 스크립트가 그 사실을 그대로 알려 준다. 추측하지 말고 응답을 볼 것.
"""
import io, os, json, secrets, http.server, urllib.parse, urllib.request, urllib.error

CID = '563584335869-fgrhgmd47bqnekij5i8b5pr03ho849e6.apps.googleusercontent.com'
CSEC = 'j9iVZfS8kkCEFUPaAeJV0sAi'
PROJECT = 'murpyprototype'
REDIRECT = 'http://localhost:9005'
HERE = os.path.dirname(os.path.abspath(__file__))

STATE = secrets.token_urlsafe(12)
AUTH_URL = 'https://accounts.google.com/o/oauth2/auth?' + urllib.parse.urlencode({
    'client_id': CID, 'redirect_uri': REDIRECT, 'response_type': 'code',
    'scope': 'email openid https://www.googleapis.com/auth/cloud-platform',
    'state': STATE, 'access_type': 'offline', 'prompt': 'consent'})
print('아래 링크를 브라우저에서 열 것 (관리자 계정):', flush=True)
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
        self.wfile.write(('<meta charset=utf-8><body style="font-family:sans-serif;padding:40px;'
                          'text-align:center"><h2>' + msg + '</h2>').encode('utf-8'))


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


def call(url, body=None, method='GET'):
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=HDR)
    try:
        return True, json.loads(urllib.request.urlopen(req).read().decode() or '{}')
    except urllib.error.HTTPError as e:
        try:
            return False, json.loads(e.read().decode())
        except Exception:
            return False, {'error': {'code': e.code, 'message': str(e)}}


# ① 결제 상태 — Spark 면 버킷 생성이 막힌다. 추측 대신 먼저 확인한다.
ok, bi = call('https://cloudbilling.googleapis.com/v1/projects/%s/billingInfo' % PROJECT)
print('결제: %s' % ('사용 중(Blaze)' if ok and bi.get('billingEnabled')
                    else ('무료(Spark) — 버킷 생성이 막힐 수 있다' if ok else bi)), flush=True)

# ②-0 API 켜기 — 이 프로젝트는 Cloud Storage for Firebase API 가 **꺼져 있었다**(2026-08-25).
#    결제(Blaze)는 이미 켜져 있었는데도 403 SERVICE_DISABLED 가 났다. 둘은 별개다.
#    콘솔에서 켜는 대신 Service Usage API 로 켠다.
import time
for svc in ['firebasestorage.googleapis.com', 'storage.googleapis.com']:
    ok, out = call('https://serviceusage.googleapis.com/v1/projects/%s/services/%s:enable'
                   % (PROJECT, svc), {}, 'POST')
    print('API 켜기 %-34s %s' % (svc, '요청됨' if ok else json.dumps(out, ensure_ascii=False)[:200]),
          flush=True)

# ★켜자마자 바로 쓰면 아직 전파가 안 돼 또 403 이 난다(구글 안내문에도 적혀 있다).
#   기다렸다가 여러 번 시도한다 — 여기서 성급하게 포기하면 "안 된다"고 잘못 결론 낸다.
print('전파 대기…', flush=True)
time.sleep(10)

# ★`.firebasestorage.app` / `.appspot.com` 은 **구글 소유 도메인**이라 우리가 직접 못 만든다
#   ("Another user owns the domain ..." 403). 그건 Firebase 가 콘솔에서 대신 만들어 주는 이름이다.
#   그래서 **평범한 이름**으로 만들고 Firebase 에 연결한다. 앱의 storageBucket 도 이 이름으로 바꾼다.
BUCKET = PROJECT + '-photos'
LOC = 'asia-northeast3'          # 서울. 유저가 전부 한국이라 가까운 데가 빠르다.
created = False

# ★defaultBucket 엔드포인트는 인자 형태가 문서마다 다르다. 400(INVALID_ARGUMENT)이 계속 났다.
#   그래서 **확실한 경로**로 간다: GCS 버킷을 직접 만들고 → Firebase 에 연결한다.
#   (defaultBucket 은 이 둘을 한 번에 해주는 편의 API 일 뿐이다.)
print('1) GCS 버킷 만들기: %s (%s)' % (BUCKET, LOC), flush=True)
ok, out = call('https://storage.googleapis.com/storage/v1/b?project=' + PROJECT,
               {'name': BUCKET, 'location': LOC, 'storageClass': 'STANDARD',
                'iamConfiguration': {'uniformBucketLevelAccess': {'enabled': True}}}, 'POST')
msg = json.dumps(out, ensure_ascii=False)
if ok:
    print('   만들었다', flush=True)
elif 'You already own this bucket' in msg or 'CONFLICT' in msg or '409' in msg:
    print('   이미 있다 — 통과', flush=True)
    ok = True
else:
    print('   실패: ' + msg[:400], flush=True)

# 2) Firebase 에 연결 — 이걸 해야 Firebase SDK 가 쓸 수 있는 버킷이 된다
if ok:
    print('2) Firebase 에 연결', flush=True)
    for attempt in range(4):
        ok2, out2 = call('https://firebasestorage.googleapis.com/v1beta/projects/%s/buckets/%s:addFirebase'
                         % (PROJECT, BUCKET), {}, 'POST')
        m2 = json.dumps(out2, ensure_ascii=False)
        if ok2 or 'ALREADY_EXISTS' in m2 or 'already' in m2.lower():
            print('   연결됨', flush=True)
            created = True
            break
        print('   시도 %d 실패: %s' % (attempt + 1, m2[:220]), flush=True)
        time.sleep(10)

# ② 기본 버킷 만들기 (위에서 이미 시도했다)
print('버킷 생성 결과: %s' % ('완료' if created else '실패'), flush=True)
# ③ 실제로 생겼는지 되읽어 확인 — "만들었다"는 응답만 믿지 않는다
ok2, lst = call('https://firebasestorage.googleapis.com/v1beta/projects/%s/buckets' % PROJECT)
if ok2:
    names = [b.get('name', '') for b in (lst.get('buckets') or [])]
    print('현재 버킷: %s' % (names or '(없음)'), flush=True)
else:
    print('버킷 목록 조회 실패: %s' % json.dumps(lst, ensure_ascii=False)[:400], flush=True)
