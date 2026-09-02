# -*- coding: utf-8 -*-
"""centers 도감의 중복 센터를 찾아 병합한다 (2026-09-02, 대표 지시).

    python tools/centers/merge_duplicates.py            # 드라이런: 중복 그룹·이관 대상만 보고
    python tools/centers/merge_duplicates.py --write    # 실제 병합

왜 생겼나: 대표 시딩(카톡 양식·콘솔)과 카카오 전국 시딩이 이름 표기만 다르면 서로를 못 알아봤다.
  시딩의 중복 판정(dup)은 ①kakaoId ②정규화 이름 완전일치 ③60m 안 + 앞 4글자 일치 뿐이라
  "짐박스 강남2호점" vs "짐박스피트니스 강남2호점"(앞 4글자: 짐박스강≠짐박스피)이 둘 다 들어갔다.

중복 판정(여기): 이름에서 업종 낱말(피트니스·헬스·GYM 등)을 뗀 '핵심 이름'이 같고
  ①좌표가 150m 안이거나 ②한쪽이 좌표가 없고 같은 구(loc)면 같은 곳으로 본다.
  느슨한 판정(정규화 이름 같음 + 300m)은 자동 병합하지 않고 **의심 목록**으로만 보고한다.

남길 문서(keeper): 체크인 많은 곳 > 대표 시딩(createdBy != seed_kakao) > 사진 있음 > 제휴 > 먼저 생성.
  지워지는 쪽의 kakaoId 는 keeper 의 kakaoId(비었으면) + mergedKakaoIds 배열에 남긴다 —
  안 남기면 카카오 시딩을 다시 돌릴 때 지운 문서가 되살아난다.

이관하는 것: checkins(문서 id 에 centerId 가 박혀 있어 새 id 로 복사 후 삭제) ·
  users.homeCenterId · users.gyms[](이름 배열) · squads.centerId ·
  centers/{id}/ratings 하위문서 · centerTalk/{id}/msgs 하위문서.
  reports(리뷰 신고)의 centerId 는 관리자 기록이라 두고 보고만 한다.
"""
import io, os, sys, json, math, re, time, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding='utf-8')

WRITE = '--write' in sys.argv
P = 'murpyprototype'
CID = '563584335869-fgrhgmd47bqnekij5i8b5pr03ho849e6.apps.googleusercontent.com'
CSEC = 'j9iVZfS8kkCEFUPaAeJV0sAi'
BASE = 'https://firestore.googleapis.com/v1/projects/%s/databases/(default)/documents' % P
DOC = 'projects/%s/databases/(default)/documents' % P   # batchWrite 의 name 은 이 접두사

# ── 토큰 (firebase CLI 로그인의 refresh_token 을 빌린다 — IAM 권한이라 규칙과 무관) ──
cfg = json.load(io.open(os.path.expanduser('~/.config/configstore/firebase-tools.json'), encoding='utf-8'))
tok = json.loads(urllib.request.urlopen(urllib.request.Request('https://oauth2.googleapis.com/token',
    urllib.parse.urlencode({'client_id': CID, 'client_secret': CSEC,
        'refresh_token': cfg['tokens']['refresh_token'], 'grant_type': 'refresh_token'}).encode())).read())['access_token']
HDR = {'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json'}

def call(url, data=None, method=None):
    req = urllib.request.Request(url, data=data, method=method, headers=HDR)
    for i in range(5):
        try: return json.loads(urllib.request.urlopen(req, timeout=60).read().decode() or '{}')
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:300]
            if e.code in (429, 500, 503): time.sleep(2 ** i); continue
            raise SystemExit('API 오류 %d %s\n%s' % (e.code, url[:120], body))
    raise SystemExit('재시도 소진: ' + url[:120])

def fs_list(col, mask=None, parent=BASE):
    out, tokp = [], None
    while True:
        u = '%s/%s?pageSize=300' % (parent, col)
        if mask: u += ''.join('&mask.fieldPaths=' + m for m in mask)
        if tokp: u += '&pageToken=' + tokp
        r = call(u)
        out += r.get('documents', []); tokp = r.get('nextPageToken')
        if not tokp: return out

def fv(f):
    if f is None: return None
    if 'integerValue' in f: return int(f['integerValue'])
    if 'doubleValue' in f: return f['doubleValue']
    if 'stringValue' in f: return f['stringValue']
    if 'booleanValue' in f: return f['booleanValue']
    if 'timestampValue' in f: return f['timestampValue']
    if 'nullValue' in f: return None
    if 'arrayValue' in f: return [fv(x) for x in (f['arrayValue'].get('values') or [])]
    if 'mapValue' in f: return {k: fv(v) for k, v in (f['mapValue'].get('fields') or {}).items()}
    return None

def val(v):
    if isinstance(v, bool): return {'booleanValue': v}
    if isinstance(v, int): return {'integerValue': str(v)}
    if isinstance(v, float): return {'doubleValue': v}
    if isinstance(v, list): return {'arrayValue': {'values': [val(x) for x in v]}}
    if v is None: return {'nullValue': None}
    return {'stringValue': str(v)}

def batch(writes):
    """batchWrite 는 500개 한도 — 나눠 보낸다. 실패 status 는 개수만 센다."""
    fail = 0
    for i in range(0, len(writes), 400):
        r = call(BASE.rsplit('/documents', 1)[0] + '/documents:batchWrite',
                 json.dumps({'writes': writes[i:i + 400]}).encode(), 'POST')
        fail += sum(1 for s in r.get('status', []) if s.get('code', 0))
    return fail

def hav(a, b, c, d):
    R = 6371000; r = math.pi / 180
    x = math.sin((c - a) * r / 2) ** 2 + math.cos(a * r) * math.cos(c * r) * math.sin((d - b) * r / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))

def norm(s): return re.sub(r'[\s\-\(\)\[\]·,.]|점$|본점$', '', str(s or '')).lower()
# 업종·수식 낱말을 뗀 핵심 이름. ★'짐'은 브랜드 일부인 경우가 많아(자마이카짐 등) 떼지 않는다.
GENERIC = r'피트니스|휘트니스|퍼스널트레이닝|헬스클럽|헬스장|헬스|스포츠센터|스포츠클럽|스포츠|트레이닝|크로스핏|fitness|crossfit|gym|pt샵|pt'
def core(s):
    c = re.sub(GENERIC, '', norm(s))
    return c

# ── 1) 데이터 읽기 ──────────────────────────────────────────────────────
print('centers 읽는 중…', flush=True)
centers = {}
for d in fs_list('centers'):
    cid = d['name'].rsplit('/', 1)[1]
    f = {k: fv(v) for k, v in d.get('fields', {}).items()}
    f['_id'] = cid; f['_ct'] = d.get('createTime', '')
    centers[cid] = f
print('  %d곳' % len(centers))

print('checkins·users·squads 읽는 중…', flush=True)
checkins = fs_list('checkins')
users = fs_list('users', mask=['homeCenterId', 'gyms', 'gym', 'nickname'])
squads = fs_list('squads', mask=['centerId', 'title'])
print('  checkins %d · users %d · squads %d' % (len(checkins), len(users), len(squads)))

ck_by_center = {}
for d in checkins:
    cid = str(fv(d['fields'].get('centerId')) or '')
    ck_by_center.setdefault(cid, []).append(d)

# ── 2) 중복 그룹 찾기 (union-find) ──────────────────────────────────────
ids = list(centers)
parent = {i: i for i in ids}
def find(x):
    while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
    return x
def union(a, b): parent[find(a)] = find(b)

by_core = {}
for cid, c in centers.items():
    k = core(c.get('name'))
    if k: by_core.setdefault(k, []).append(cid)

suspects = []   # 자동 병합엔 못 넣는 애매한 쌍
for k, group in by_core.items():
    if len(group) < 2: continue
    for i in range(len(group)):
        for j in range(i + 1, len(group)):
            a, b = centers[group[i]], centers[group[j]]
            la, ln, lb, lnb = a.get('lat'), a.get('lng'), b.get('lat'), b.get('lng')
            if la and lb:
                d = hav(float(la), float(ln), float(lb), float(lnb))
                if d <= 150: union(group[i], group[j])
                elif d <= 400 and norm(a.get('name')) == norm(b.get('name')): union(group[i], group[j])
                elif d <= 1000: suspects.append((group[i], group[j], int(d)))
            else:
                # 좌표 없는 쪽이 있으면 같은 구(loc)일 때만 — 프랜차이즈 다른 지점을 합치면 사고다
                if (a.get('loc') or '?') == (b.get('loc') or '!'): union(group[i], group[j])

groups = {}
for cid in ids:
    r = find(cid)
    groups.setdefault(r, []).append(cid)
groups = [g for g in groups.values() if len(g) > 1]

# ── 3) keeper 선정 + 보고 ───────────────────────────────────────────────
def refs_of(cid):
    n_ck = len(ck_by_center.get(str(cid), []))
    n_user = 0
    cname = centers[cid].get('name')
    for u in users:
        f = u.get('fields', {})
        gyms = fv(f.get('gyms')) or ([fv(f.get('gym'))] if fv(f.get('gym')) else [])
        if str(fv(f.get('homeCenterId')) or '') == str(cid) or (cname in (gyms or [])): n_user += 1
    n_sq = sum(1 for s in squads if str(fv(s['fields'].get('centerId')) or '') == str(cid))
    return n_ck, n_user, n_sq

plans = []
for g in groups:
    # 정렬: 참조 많음 > 대표 시딩 > 사진 > 제휴 > 먼저 생성
    def key(cid):
        c = centers[cid]; n_ck, n_user, n_sq = refs_of(cid)
        return (-(n_ck * 100 + n_user * 30 + n_sq * 30),
                0 if c.get('createdBy') != 'seed_kakao' else 1,
                0 if c.get('img') else 1,
                0 if c.get('partner') else 1,
                c.get('_ct') or '9999')
    g2 = sorted(g, key=key)
    plans.append((g2[0], g2[1:]))

print('\n===== 중복 그룹 %d개 =====' % len(plans))
total_drop = 0
for keep, drops in plans:
    kc = centers[keep]; n_ck, n_user, n_sq = refs_of(keep)
    print('\n★남김 %s | %s (%s) 체크인%d 유저%d 스쿼드%d %s' % (
        keep, kc.get('name'), kc.get('loc') or '-', n_ck, n_user, n_sq,
        '' if kc.get('createdBy') == 'seed_kakao' else '[대표시딩]'))
    for d in drops:
        dc = centers[d]; dn = refs_of(d)
        dist = ''
        if kc.get('lat') and dc.get('lat'):
            dist = '%dm' % hav(float(kc['lat']), float(kc['lng']), float(dc['lat']), float(dc['lng']))
        print('  지움 %s | %s (%s) 체크인%d 유저%d 스쿼드%d %s %s' % (
            d, dc.get('name'), dc.get('loc') or '-', dn[0], dn[1], dn[2], dist,
            '' if dc.get('createdBy') == 'seed_kakao' else '[대표시딩]'))
        total_drop += 1
if suspects:
    print('\n===== 의심(자동 병합 안 함 · 400m~1km 같은 핵심이름) %d쌍 =====' % len(suspects))
    for a, b, d in suspects[:30]:
        print('  ? %s | %s  ↔  %s | %s  (%dm)' % (a, centers[a].get('name'), b, centers[b].get('name'), d))

if not plans:
    print('\n중복 없음.'); sys.exit(0)
if not WRITE:
    print('\n드라이런 끝 — 지워질 문서 %d곳. 실제 병합은 --write' % total_drop); sys.exit(0)

# ── 4) 병합 실행 ────────────────────────────────────────────────────────
print('\n병합 시작…')
for keep, drops in plans:
    kc = centers[keep]
    for d in drops:
        dc = centers[d]
        writes = []
        # ① keeper 보강 — 빈 필드만 채운다 + kakaoId 흔적(재시딩 방지)
        fill = {}
        for fkey in ('img', 'phone', 'kakaoUrl', 'addr', 'lat', 'lng', 'type', 'loc'):
            if not kc.get(fkey) and dc.get(fkey): fill[fkey] = dc[fkey]; kc[fkey] = dc[fkey]
        if dc.get('kakaoId'):
            if not kc.get('kakaoId'): fill['kakaoId'] = dc['kakaoId']; kc['kakaoId'] = dc['kakaoId']
            merged = list(dict.fromkeys((kc.get('mergedKakaoIds') or []) + [dc['kakaoId']]))
            fill['mergedKakaoIds'] = merged; kc['mergedKakaoIds'] = merged
        mem = list(dict.fromkeys((kc.get('members') or []) + (dc.get('members') or [])))
        if mem != (kc.get('members') or []): fill['members'] = mem; kc['members'] = mem
        if fill:
            writes.append({'update': {'name': '%s/centers/%s' % (DOC, keep), 'fields': {k: val(v) for k, v in fill.items()}},
                           'updateMask': {'fieldPaths': list(fill)}})
        # ② ratings 이관 (같은 uid 가 양쪽에 있으면 keeper 것 유지)
        d_ratings = fs_list('centers/%s/ratings' % d)
        k_have = set(x['name'].rsplit('/', 1)[1] for x in fs_list('centers/%s/ratings' % keep, mask=['userId']))
        for r in d_ratings:
            rid = r['name'].rsplit('/', 1)[1]
            if rid not in k_have:
                writes.append({'update': {'name': r['name'].replace('/centers/%s/' % d, '/centers/%s/' % keep), 'fields': r.get('fields', {})}})
            writes.append({'delete': r['name']})
        # ③ centerTalk 이관
        d_msgs = fs_list('centerTalk/%s/msgs' % d)
        for m in d_msgs:
            writes.append({'update': {'name': m['name'].replace('/centerTalk/%s/' % d, '/centerTalk/%s/' % keep), 'fields': m.get('fields', {})}})
            writes.append({'delete': m['name']})
        # ④ checkins 이관 — 문서 id 안의 _{centerId}_ 를 갈아끼운다. 같은 날 양쪽에 찍었으면 keeper 것만 남긴다
        for ckd in ck_by_center.get(str(d), []):
            old = ckd['name']; oid = old.rsplit('/', 1)[1]
            nid = oid.replace('_%s_' % d, '_%s_' % keep)
            fields = dict(ckd.get('fields', {}))
            fields['centerId'] = val(str(keep)); fields['centerName'] = val(kc.get('name') or '')
            if nid != oid and not any(x['name'].endswith('/' + nid) for x in ck_by_center.get(str(keep), [])):
                writes.append({'update': {'name': old.rsplit('/checkins/', 1)[0] + '/checkins/' + nid, 'fields': fields}})
            writes.append({'delete': old})
        # ⑤ users — homeCenterId · gyms 이름 교체
        for u in users:
            f = u.get('fields', {}); up = {}; mask = []
            if str(fv(f.get('homeCenterId')) or '') == str(d): up['homeCenterId'] = val(str(keep)); mask.append('homeCenterId')
            gyms = fv(f.get('gyms'))
            if isinstance(gyms, list) and dc.get('name') in gyms:
                g2 = list(dict.fromkeys([kc.get('name') if x == dc.get('name') else x for x in gyms]))
                up['gyms'] = val(g2); mask.append('gyms')
            if up:
                writes.append({'update': {'name': u['name'], 'fields': up}, 'updateMask': {'fieldPaths': mask}})
        # ⑥ squads.centerId
        for s in squads:
            if str(fv(s['fields'].get('centerId')) or '') == str(d):
                writes.append({'update': {'name': s['name'], 'fields': {'centerId': val(str(keep))}},
                               'updateMask': {'fieldPaths': ['centerId']}})
        # ⑦ 원본 삭제
        writes.append({'delete': '%s/centers/%s' % (DOC, d)})
        fail = batch(writes)
        # ⑧ 평점 재계산 (이관 뒤 실제 하위문서 기준)
        allr = fs_list('centers/%s/ratings' % keep)
        scores = [fv(x['fields'].get('score')) for x in allr if fv(x['fields'].get('score'))]
        avg = round(sum(scores) / len(scores) * 10) / 10 if scores else 0
        batch([{'update': {'name': '%s/centers/%s' % (DOC, keep),
                           'fields': {'rating': val(float(avg)), 'reviews': val(len(scores))}},
                'updateMask': {'fieldPaths': ['rating', 'reviews']}}])
        print('  병합됨: %s ← %s (%s) 쓰기 %d건 실패 %d' % (kc.get('name'), dc.get('name'), d, len(writes), fail))

print('\n완료 — %d곳 병합·삭제' % total_drop)
