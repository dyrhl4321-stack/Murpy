// murpy-kakao Cloudflare Worker — 카카오 로그인 → Firebase 커스텀 토큰 (2026-08-29)
//
// 왜 바꾸나: 예전엔 클라이언트가 kakao_{id}@kakao.murpy.app / kp_{id}_mk 로 이메일·비밀번호 계정을
// 만들었다. 비밀번호가 카카오 id 에서 곧바로 나오고, 그 id 는 users 문서(누구나 읽음)에 있어서
// **아무나 남의 카카오 계정으로 로그인할 수 있었다.** 이제 비밀번호를 없애고, 이 Worker 가
// 카카오 토큰을 검증한 뒤 Firebase Admin 권한으로 커스텀 토큰을 발급한다. 클라이언트는 그걸로만 들어간다.
//
// 요청 (POST, JSON)
//   { code, redirect_uri, linkUid? }   ← 인가 코드 (카톡 리다이렉트 / PC 팝업)
//   { access_token, linkUid? }         ← 이미 받은 액세스 토큰 (하위호환 경로)
//   linkUid = 임시(익명) 계정을 이 카카오 계정에 붙일 때 그 uid. 처음 보는 카카오 id 일 때만 붙는다.
// 응답
//   { customToken, uid, kakaoId, nickname, photoURL, linked }   (FIREBASE_SA 가 있을 때)
//   { access_token }                                            (FIREBASE_SA 가 없으면 옛 방식 — 클라이언트가 알아서 처리)
//
// 환경변수 (Cloudflare 대시보드 → Settings → Variables and Secrets)
//   KAKAO_JS_KEY      카카오 JavaScript 키 (토큰 교환 client_id) — 지금도 쓰고 있는 값
//   KAKAO_SECRET      (선택) 카카오 client_secret 을 켜 두었다면
//   FIREBASE_SA       ★Firebase 서비스 계정 JSON 전체 (Secret) — Firebase 콘솔 → 프로젝트 설정 → 서비스 계정 → 새 비공개 키
//   ALLOWED_ORIGINS   쉼표 구분. 예: https://murpy.app,https://dyrhl4321-stack.github.io
//
// Firestore 에 쓰는 것: kakaoLinks/{kakaoId} = { uid, at, legacy, pwRotated }  ← 규칙상 클라이언트는 못 읽는다.

const KAKAO_TOKEN = 'https://kauth.kakao.com/oauth/token';
const KAKAO_ME = 'https://kapi.kakao.com/v2/user/me';
const TOOLKIT = 'https://identitytoolkit.googleapis.com/v1';
const CUSTOM_AUD = 'https://identitytoolkit.googleapis.com/google.identity.identitytoolkit.v1.IdentityToolkit';

export default {
  async fetch(req, env) {
    const origin = req.headers.get('Origin') || '';
    const cors = corsHeaders(origin, env);
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });
    if (req.method !== 'POST') return json({ error: 'method' }, 405, cors);
    if (!originAllowed(origin, env)) return json({ error: 'origin' }, 403, cors);
    let body;
    try { body = await req.json(); } catch (e) { return json({ error: 'bad_json' }, 400, cors); }
    try {
      // 1) 액세스 토큰 확보
      let accessToken = body.access_token;
      if (!accessToken) {
        if (!body.code) return json({ error: 'no_code' }, 400, cors);
        const form = new URLSearchParams({ grant_type: 'authorization_code', client_id: env.KAKAO_JS_KEY, redirect_uri: body.redirect_uri || '', code: body.code });
        if (env.KAKAO_SECRET) form.set('client_secret', env.KAKAO_SECRET);
        const tr = await fetch(KAKAO_TOKEN, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8' }, body: form });
        const tj = await tr.json();
        if (!tj.access_token) return json(tj, 400, cors);
        accessToken = tj.access_token;
      }
      // 2) 서비스 계정이 없으면 옛 방식 (클라이언트가 이메일/비밀번호로 처리) — 전환 전 호환용
      if (!env.FIREBASE_SA) return json({ access_token: accessToken }, 200, cors);

      // 3) 카카오 사용자 확인 — 토큰이 진짜인지는 여기서 카카오가 판정한다
      const me = await (await fetch(KAKAO_ME, { headers: { Authorization: 'Bearer ' + accessToken } })).json();
      if (!me || !me.id) return json({ error: 'kakao_me', detail: me }, 401, cors);
      const kakaoId = String(me.id);
      const profile = (me.kakao_account && me.kakao_account.profile) || {};
      const nickname = profile.nickname || '카카오유저';
      const photoURL = profile.profile_image_url || '';

      // 4) Firebase Admin 토큰
      const sa = JSON.parse(env.FIREBASE_SA);
      const gToken = await googleAccessToken(sa);
      const project = sa.project_id;

      // 5) 카카오 id → uid 매핑 (kakaoLinks/{kakaoId})
      const linkDoc = await fsGet(project, gToken, 'kakaoLinks/' + kakaoId);
      let uid = linkDoc && linkDoc.uid;
      let linked = false, legacy = false;
      if (!uid) {
        const legacyEmail = 'kakao_' + kakaoId + '@kakao.murpy.app';
        const found = await toolkitLookupByEmail(gToken, project, legacyEmail);
        if (found) { uid = found; legacy = true; }
        else if (body.linkUid && /^[A-Za-z0-9]{10,64}$/.test(body.linkUid)) { uid = body.linkUid; linked = true; }
        else uid = 'kakao_' + kakaoId;
        await fsSet(project, gToken, 'kakaoLinks/' + kakaoId, { uid, at: new Date().toISOString(), legacy, pwRotated: false });
      }
      // 6) 옛 이메일/비밀번호 계정이면 비밀번호를 한 번 랜덤으로 갈아 끼운다 — 예측 가능한 pw 를 죽인다
      const needRotate = linkDoc ? (linkDoc.legacy === true && linkDoc.pwRotated !== true) : legacy;
      if (needRotate) {
        try {
          await toolkitUpdate(gToken, project, { localId: uid, password: randomPassword() });
          await fsSet(project, gToken, 'kakaoLinks/' + kakaoId, { uid, pwRotated: true, legacy: true, at: (linkDoc && linkDoc.at) || new Date().toISOString() });
        } catch (e) { /* 계정이 없거나 이미 바뀜 — 로그인은 계속 */ }
      }
      // 7) 커스텀 토큰
      const customToken = await mintCustomToken(sa, uid, { kakao: true });
      return json({ customToken, uid, kakaoId, nickname, photoURL, linked }, 200, cors);
    } catch (e) {
      return json({ error: 'worker', message: String((e && e.message) || e) }, 500, cors);
    }
  }
};

// ---------- helpers ----------
function corsHeaders(origin, env) {
  return { 'Access-Control-Allow-Origin': originAllowed(origin, env) ? origin : 'null', 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type', 'Vary': 'Origin' };
}
function originAllowed(origin, env) {
  if (!env.ALLOWED_ORIGINS) return true;
  return env.ALLOWED_ORIGINS.split(',').map(s => s.trim()).includes(origin);
}
function json(obj, status, headers) { return new Response(JSON.stringify(obj), { status, headers: Object.assign({ 'Content-Type': 'application/json' }, headers) }); }
function b64url(buf) {
  const s = typeof buf === 'string' ? btoa(unescape(encodeURIComponent(buf))) : btoa(String.fromCharCode(...new Uint8Array(buf)));
  return s.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function randomPassword() { const a = new Uint8Array(24); crypto.getRandomValues(a); return b64url(a.buffer) + 'Aa1!'; }
async function importKey(pem) {
  const der = Uint8Array.from(atob(pem.replace(/-----[^-]+-----/g, '').replace(/\s+/g, '')), c => c.charCodeAt(0));
  return crypto.subtle.importKey('pkcs8', der, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['sign']);
}
async function signJwt(sa, payload) {
  const key = await importKey(sa.private_key);
  const header = b64url(JSON.stringify({ alg: 'RS256', typ: 'JWT' }));
  const body = b64url(JSON.stringify(payload));
  const sig = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', key, new TextEncoder().encode(header + '.' + body));
  return header + '.' + body + '.' + b64url(sig);
}
async function googleAccessToken(sa) {
  const now = Math.floor(Date.now() / 1000);
  const jwt = await signJwt(sa, { iss: sa.client_email, sub: sa.client_email, aud: 'https://oauth2.googleapis.com/token', iat: now, exp: now + 3600,
    scope: 'https://www.googleapis.com/auth/identitytoolkit https://www.googleapis.com/auth/datastore https://www.googleapis.com/auth/cloud-platform' });
  const r = await fetch('https://oauth2.googleapis.com/token', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer', assertion: jwt }) });
  const j = await r.json();
  if (!j.access_token) throw new Error('google token: ' + JSON.stringify(j));
  return j.access_token;
}
async function mintCustomToken(sa, uid, claims) {
  const now = Math.floor(Date.now() / 1000);
  return signJwt(sa, { iss: sa.client_email, sub: sa.client_email, aud: CUSTOM_AUD, iat: now, exp: now + 3600, uid, claims: claims || {} });
}
async function toolkitLookupByEmail(gToken, project, email) {
  const r = await fetch(TOOLKIT + '/projects/' + project + '/accounts:lookup', { method: 'POST', headers: { Authorization: 'Bearer ' + gToken, 'Content-Type': 'application/json' }, body: JSON.stringify({ email: [email] }) });
  const j = await r.json();
  return (j.users && j.users[0] && j.users[0].localId) || null;
}
async function toolkitUpdate(gToken, project, body) {
  const r = await fetch(TOOLKIT + '/projects/' + project + '/accounts:update', { method: 'POST', headers: { Authorization: 'Bearer ' + gToken, 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error('toolkit update ' + r.status);
}
function fsDoc(project, path) { return 'https://firestore.googleapis.com/v1/projects/' + project + '/databases/(default)/documents/' + path; }
function toFs(v) { if (typeof v === 'string') return { stringValue: v }; if (typeof v === 'boolean') return { booleanValue: v }; if (typeof v === 'number') return { integerValue: String(v) }; return { nullValue: null }; }
function fromFs(f) { if (!f) return undefined; if ('stringValue' in f) return f.stringValue; if ('booleanValue' in f) return f.booleanValue; if ('integerValue' in f) return Number(f.integerValue); return null; }
async function fsGet(project, gToken, path) {
  const r = await fetch(fsDoc(project, path), { headers: { Authorization: 'Bearer ' + gToken } });
  if (r.status === 404) return null;
  const j = await r.json(); if (!j.fields) return null;
  const o = {}; for (const k in j.fields) o[k] = fromFs(j.fields[k]); return o;
}
async function fsSet(project, gToken, path, obj) {
  const fields = {}; for (const k in obj) fields[k] = toFs(obj[k]);
  const r = await fetch(fsDoc(project, path), { method: 'PATCH', headers: { Authorization: 'Bearer ' + gToken, 'Content-Type': 'application/json' }, body: JSON.stringify({ fields }) });
  if (!r.ok) throw new Error('firestore set ' + r.status + ' ' + await r.text());
}
