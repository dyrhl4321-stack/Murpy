// 11-24 보안 점검(바이브코딩 해킹 14가지) 규칙 검사. Local demo emulator only — 운영 서버·키를 받지 않는다.
// 실행: firebase emulators:exec --only firestore --project demo-murpyface "node tools/tests/security-1124-rules.emulator.mjs"
//       (firestore 에뮬레이터 포트 8793 — 다른 *.emulator.mjs 와 같다)
import assert from 'node:assert/strict';
const project = 'demo-murpyface', prefix = `projects/${project}/databases/(default)/documents`, root = `http://127.0.0.1:8793/v1/${prefix}`;
const ADMIN = 'dyrhl4321@gmail.com';
const enc = v => v === null ? { nullValue: null } : typeof v === 'boolean' ? { booleanValue: v } : Number.isInteger(v) ? { integerValue: String(v) }
  : typeof v === 'number' ? { doubleValue: v } : typeof v === 'string' ? { stringValue: v } : Array.isArray(v) ? { arrayValue: { values: v.map(enc) } }
  : { mapValue: { fields: Object.fromEntries(Object.entries(v).map(([k, x]) => [k, enc(x)])) } };
function jwt(uid, extra) {
  const now = Math.floor(Date.now() / 1000), part = v => Buffer.from(JSON.stringify(v)).toString('base64url');
  return part({ alg: 'none', typ: 'JWT' }) + '.' + part(Object.assign({ sub: uid, user_id: uid, aud: project, iss: `https://securetoken.google.com/${project}`,
    iat: now, exp: now + 3600, firebase: { sign_in_provider: 'custom' } }, extra || {})) + '.';
}
const tok = u => u === 'owner' ? 'owner' : u === 'admin' ? jwt('adminUid', { email: ADMIN, email_verified: true })
  : u === 'fakeadmin' ? jwt('fakeUid', { email: ADMIN, email_verified: false }) : jwt(u);
const H = u => ({ 'Content-Type': 'application/json', Authorization: 'Bearer ' + tok(u) });
let checks = 0;
async function put(path, data, user = 'owner', code = 200) {
  const r = await fetch(root + ':commit', { method: 'POST', headers: H(user), body: JSON.stringify({ writes: [{ update: { name: `${prefix}/${path}`, fields: enc(data).mapValue.fields } }] }) });
  assert.equal(r.status, code, `put ${path} as ${user}: ` + await r.text()); checks++;
}
async function patch(path, data, user, code) {
  const r = await fetch(root + ':commit', { method: 'POST', headers: H(user), body: JSON.stringify({ writes: [{ update: { name: `${prefix}/${path}`, fields: enc(data).mapValue.fields },
    updateMask: { fieldPaths: Object.keys(data) }, currentDocument: { exists: true } }] }) });
  assert.equal(r.status, code, `patch ${path} as ${user}: ` + await r.text()); checks++;
}
async function create(path, data, user, code) {
  const r = await fetch(root + ':commit', { method: 'POST', headers: H(user), body: JSON.stringify({ writes: [{ update: { name: `${prefix}/${path}`, fields: enc(data).mapValue.fields },
    currentDocument: { exists: false } }] }) });
  assert.equal(r.status, code, `create ${path} as ${user}: ` + await r.text()); checks++;
}
async function get(path, user, code) {
  const r = await fetch(root + '/' + path, { headers: H(user) });
  assert.equal(r.status, code, `get ${path} as ${user}: ` + await r.text()); checks++;
}
const eq = (f, v) => ({ fieldFilter: { field: { fieldPath: f }, op: 'EQUAL', value: enc(v) } });
const has = (f, v) => ({ fieldFilter: { field: { fieldPath: f }, op: 'ARRAY_CONTAINS', value: enc(v) } });
async function q(coll, filters, user, code) {
  const where = !filters.length ? undefined : filters.length === 1 ? filters[0] : { compositeFilter: { op: 'AND', filters } };
  const r = await fetch(root + ':runQuery', { method: 'POST', headers: H(user), body: JSON.stringify({ structuredQuery: Object.assign({ from: [{ collectionId: coll }] }, where ? { where } : {}) }) });
  assert.equal(r.status, code, `query ${coll} ${JSON.stringify(filters)} as ${user}: ` + await r.text()); checks++;
}

// ── 좋아요(매칭 신청): 당사자만 ──
await put('likes/alice_bob', { from: 'alice', to: 'bob' });
await get('likes/alice_bob', 'alice', 200);
await get('likes/alice_bob', 'bob', 200);
await get('likes/alice_bob', 'eve', 403);
await get('likes/nobody_none', 'eve', 404);                 // 없는 문서 확인(getDoc.exists)은 그대로
await q('likes', [eq('from', 'alice')], 'alice', 200);
await q('likes', [eq('to', 'bob')], 'bob', 200);
await q('likes', [eq('to', 'bob')], 'eve', 403);
await q('likes', [], 'eve', 403);

// ── 매칭: 당사자만 · 관리자 통계는 전체 ──
await put('matches/alice_bob', { users: ['alice', 'bob'] });
await get('matches/alice_bob', 'bob', 200);
await get('matches/alice_bob', 'eve', 403);
await get('matches/zz_yy', 'eve', 404);
await q('matches', [has('users', 'alice')], 'alice', 200);
await q('matches', [], 'eve', 403);
await q('matches', [], 'admin', 200);
await q('matches', [], 'fakeadmin', 403);                    // 인증 안 된 같은 이메일 = 관리자 아님

// ── 알림: 받는/보낸 사람만 · 경매 입찰만 공개 ──
await put('notifications/n1', { toUid: 'bob', fromUid: 'alice', type: 'match' });
await put('notifications/b1', { toUid: 'alice', fromUid: 'bob', type: 'art_bid', artId: 'art1', amount: 5 });
await put('notifications/s1', { toUid: 'alice', fromUid: 'bob', type: 'art_sold', artId: 'art1' });
await get('notifications/n1', 'bob', 200);
await get('notifications/n1', 'alice', 200);
await get('notifications/n1', 'eve', 403);
await q('notifications', [eq('toUid', 'bob')], 'bob', 200);
await q('notifications', [eq('toUid', 'bob')], 'eve', 403);
await q('notifications', [eq('type', 'art_bid')], 'eve', 200);
await q('notifications', [eq('artId', 'art1'), eq('type', 'art_bid')], 'eve', 200);
await q('notifications', [eq('artId', 'art1')], 'eve', 403);   // 앱은 type 을 같이 건다(index.html mwAucBids)
await q('notifications', [eq('toUid', 'alice'), eq('type', 'bamboo_request')], 'alice', 200);

// ── 가입 문서: 머피 30 이하 · 커마권 0 ──
await create('users/u30', { nickname: 'a', credits: 30 }, 'u30', 200);
await create('users/u31', { nickname: 'a', credits: 31 }, 'u31', 403);
await create('users/u500', { nickname: 'a', credits: 500 }, 'u500', 403);
await create('users/uft', { nickname: 'a', credits: 30, faceTickets: 5 }, 'uft', 403);
await create('users/uft0', { nickname: 'a', credits: 30, faceTickets: 0 }, 'uft0', 200);
await create('users/uother', { nickname: 'a' }, 'eve', 403);

// ── 관리자 판정: 이메일 인증까지 ──
await put('banners/b1', { t: 1 }, 'admin', 200);
await put('banners/b2', { t: 1 }, 'fakeadmin', 403);

// ── 헬스장: 일반 유저는 등록(소개·공지 없이)·별점만 ──
await create('centers/c1', { name: '테스트짐', createdBy: 'alice', rating: 0, reviews: 0 }, 'alice', 200);
await create('centers/c2', { name: '짐', createdBy: 'alice', intro: '<img src=x onerror=alert(1)>' }, 'alice', 403);
await create('centers/c3', { name: '짐', createdBy: 'bob' }, 'alice', 403);
await patch('centers/c1', { name: '<img src=x onerror=alert(1)>' }, 'eve', 403);
await patch('centers/c1', { intro: 'x' }, 'eve', 403);
await patch('centers/c1', { rating: 4.5, reviews: 2 }, 'eve', 200);
await patch('centers/c1', { name: '관리자 수정' }, 'admin', 200);
await create('centers/c4', { name: '관리자 등록', intro: '소개' }, 'admin', 200);

// ── 리뷰: 본인 문서·길이 제한 ──
await put('centers/c1/ratings/alice', { score: 5, text: '좋아요', nickname: 'alice' }, 'alice', 200);
await put('centers/c1/ratings/alice', { score: 5, text: 'x'.repeat(1001), nickname: 'alice' }, 'alice', 403);
await put('centers/c1/ratings/bob', { score: 1, text: 'x', nickname: 'bob' }, 'alice', 403);

// ── XSS 2차 방어: 닉네임·사진 주소 글자 검사 ──
const FB_URL = 'https://firebasestorage.googleapis.com/v0/b/x/o/uploads%2Fa.jpg?alt=media&token=1-2';
await create('users/k1', { nickname: '근손실방지단 민수', credits: 30, photoURL: FB_URL, district: '강남구' }, 'k1', 200);
await create('users/k2', { nickname: '"><img src=x onerror=alert(1)>', credits: 0 }, 'k2', 403);
await create('users/k3', { nickname: 'a&#39;);alert(1)//', credits: 0 }, 'k3', 403);
await create('users/k4', { nickname: 'a\\b', credits: 0 }, 'k4', 403);
await create('users/k5', { nickname: 'ok', credits: 0, photoURL: 'javascript:alert(1)' }, 'k5', 403);
await create('users/k6', { nickname: 'ok', credits: 0, photoURL: 'https://a.com/x"onerror=alert(1)' }, 'k6', 403);
await create('users/k7', { nickname: 'ok', credits: 0, photoURL: 'data:image/jpeg;base64,AAAA' }, 'k7', 200);
await create('users/k8', { nickname: "it's me", credits: 0 }, 'k8', 200);       // 작은따옴표 닉네임은 허용(앱이 _escJs)
await patch('users/k1', { nickname: '<b>x</b>' }, 'k1', 403);
await patch('users/k1', { district: '"' }, 'k1', 403);
await patch('users/k1', { nickname: '새닉네임' }, 'k1', 200);
await put('users/legacy', { nickname: '<옛날값>', credits: 10 });                // 규칙 전 저장된 값
await patch('users/legacy', { bio: '안녕하세요 <3' }, 'legacy', 200);            // 닉네임을 안 바꾸면 다른 칸 저장은 된다
await create('feed/f1', { userId: 'alice', userName: 'alice', photoURL: FB_URL, text: '<3 오운완' }, 'alice', 200);
await create('feed/f2', { userId: 'alice', userName: '"><svg onload=alert(1)>', text: 'x' }, 'alice', 403);
await create('feed/f3', { userId: 'alice', userName: 'a', photoURL: "https://a.com/x');alert(1)//" }, 'alice', 403);
await create('feed/f4', { userId: 'bob', userName: 'bob', text: '남 이름 글' }, 'alice', 403);
await create('feed/f1/comments/c1', { userId: 'alice', userName: 'alice', text: '<3' }, 'alice', 200);
await create('feed/f1/comments/c2', { userId: 'bob', userName: 'bob', text: 'x' }, 'alice', 403);
await create('bamboo/b0', { userId: 'alice', userName: 'a', text: 'x' }, 'alice', 200);
await create('bamboo/b0/comments/c1', { userId: '"x', text: 'x' }, 'alice', 403);
await create('bamboo/b1', { userId: 'alice', userName: 'a', userPhoto: 'https://a.com/"x' }, 'alice', 403);
await create('notifications/x1', { toUid: 'bob', fromUid: 'alice', fromNickname: '<img src=x>', type: 'match' }, 'alice', 403);
await create('notifications/x2', { toUid: 'bob', fromUid: 'alice', fromNickname: '앨리스', type: 'match' }, 'alice', 200);
await put('centers/c1/ratings/alice', { score: 5, text: 'x', nickname: '<img>' }, 'alice', 403);

console.log('OK security-1124 rules emulator', checks, 'checks');
