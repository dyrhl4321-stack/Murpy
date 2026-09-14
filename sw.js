// 배포마다 이 버전을 올려야 자동 새버전 적용(새로고침)이 동작함
const CACHE_NAME = 'murpy-v1203';
const STATIC_CACHE = 'murpy-static-v1203';
const CDN_CACHE = 'murpy-cdn-v1203';
// 이미지 캐시는 버전 안 붙임 → 코드/HTML 배포해도 유지(URL이 곧 버전)
const IMG_CACHE = 'murpy-img-v2';   // ★9-09 대표 폰에서 골프 에셋 전부 안 뜸 — 버전 없는 캐시에 깨진 항목이 박제되면 배포로도 안 지워진다 → 이름을 바꿔 한 번 전부 다시 받게

// 앱 시작 시 즉시 캐시할 로컬 파일 (HTML 은 아래 precacheHtml 이 버전 확인 후 따로 넣는다)
const STATIC_ASSETS = [
  './manifest.json',
  './favicon-32.png',
  './icon-192.png',
  './icon-512.png',
  './ob/logo-nukki-480.png',
];

// CDN 스크립트 (버전 고정 → 영구 캐시)
const CDN_HOSTS = [
  'www.gstatic.com',
  't1.kakaocdn.net',
];

// ===== HTML 캐시 (9-14 부팅 속도) =====
// 이 워커 버전과 같은 index.html 만 STATIC_CACHE 의 HTML_KEY 에 둔다. 버전이 다른 HTML 은 절대 안 넣는다 —
//   GitHub Pages CDN 이 10분쯤 옛 파일을 주는데, 그걸 새 워커가 캐시하면 새 워커 + 옛 화면 조합으로 굳는다.
const HTML_KEY = './index.html';
const SW_VER = CACHE_NAME.replace(/^murpy-v/, '');
async function htmlMatchesThisWorker(res) {
  try {
    const t = await res.text();
    const m = t.match(/window\._SW_V = '(\d+)'/);
    return !!(m && m[1] === SW_VER);
  } catch (e) { return false; }
}
async function fetchAndStoreHtml(req) {
  const res = await fetch(req, { cache: 'no-cache' });
  if (res && res.ok && await htmlMatchesThisWorker(res.clone())) {
    const c = await caches.open(STATIC_CACHE);
    await c.put(HTML_KEY, res.clone());
  }
  return res;
}
async function precacheHtml() {
  try { await fetchAndStoreHtml(new Request('./index.html', { cache: 'no-cache' })); } catch (e) {}
}

self.addEventListener('install', e => {
  self.skipWaiting();
  e.waitUntil(
    caches.open(STATIC_CACHE).then(cache =>
      cache.addAll(STATIC_ASSETS).catch(() => {})
    ).then(precacheHtml)
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => ![CACHE_NAME, STATIC_CACHE, CDN_CACHE, IMG_CACHE].includes(k))
          .map(k => caches.delete(k))
      )
    ).then(() => clients.claim()).then(() =>
      clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list =>
        // 버전은 CACHE_NAME 에서 뽑는다 — 예전엔 '731' 이 하드코딩돼 배포마다 안 올라갔다(8-29 발견)
        Promise.all(list.map(client => client.postMessage({ type: 'MURPY_SW_ACTIVATED', version: CACHE_NAME.replace(/^murpy-v/, '') })))
      )
    )
  );
});

self.addEventListener('message', e => {
  if (e.data && e.data.type === 'SKIP_WAITING') self.skipWaiting();
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;

  const url = new URL(e.request.url);

  // 버전 표식과 서비스워커 본체는 어떤 캐시에도 넣지 않는다. 구형 폰이 이 둘을 캐시하면
  // 새 배포를 알아차릴 단서까지 함께 얼어붙어 영원히 옛 화면에 남는다.
  if (url.origin === self.location.origin &&
      (url.pathname.endsWith('/version.txt') || url.pathname.endsWith('/sw.js'))) {
    e.respondWith(fetch(e.request, { cache: 'no-store' }));
    return;
  }

  // Firestore / Firebase Auth API → 네트워크만 (실시간 데이터)
  if (url.hostname.includes('firestore.googleapis.com') ||
      url.hostname.includes('identitytoolkit.googleapis.com') ||
      url.hostname.includes('securetoken.googleapis.com') ||
      url.hostname.includes('firebase.googleapis.com') ||
      url.pathname.includes('/v2/user/me')) {
    return;
  }

  // 프로필/피드 이미지 → 캐시 우선 (URL이 곧 버전)
  // ★파이어베이스 스토리지도 여기 넣는다 (2026-08-25). 다운로드 주소에 **토큰**이 붙어 있어서
  //   파일이 바뀌면 주소도 바뀐다 → 캐시 우선이 안전하고, 두 번째부터는 네트워크를 안 탄다.
  if (url.hostname.includes('images.weserv.nl') || url.hostname.includes('ibb.co')
      || url.hostname.includes('firebasestorage.googleapis.com')
      || url.hostname.includes('storage.googleapis.com')) {
    e.respondWith(
      caches.open(IMG_CACHE).then(async cache => {
        const cached = await cache.match(e.request);
        // ★9-09: 캐시된 게 진짜 이미지/오디오가 아니면(빈 응답·HTML 등) 버리고 다시 받는다 — 자가 치유(대표 폰 골프 에셋 실종)
        const ct = cached ? (cached.headers.get('content-type') || '') : '';
        if (cached && cached.status === 200 && /^(image|audio|video)\//.test(ct)) return cached;
        if (cached) { try { await cache.delete(e.request); } catch (err) {} }
        const res = await fetch(e.request);
        if (res && res.ok && /^(image|audio|video)\//.test(res.headers.get('content-type') || '')) cache.put(e.request, res.clone());
        return res;
      }).catch(() => fetch(e.request))
    );
    return;
  }

  // CDN 스크립트 → 캐시 우선 (버전 고정 파일)
  if (CDN_HOSTS.some(h => url.hostname.includes(h))) {
    e.respondWith(
      caches.open(CDN_CACHE).then(async cache => {
        const cached = await cache.match(e.request);
        if (cached) return cached;
        const res = await fetch(e.request);
        // ★9-07: 404/5xx 를 캐시하면 배포 직후 잠깐 없던 파일이 영원히 깨진 채 남는다(NPC 시트 실종) — 정상 응답만 넣는다
        if (res && res.ok) cache.put(e.request, res.clone());
        return res;
      })
    );
    return;
  }

  // 앱 HTML → **캐시 우선 + 뒤에서 갱신** (9-14 부팅 속도)
  // ★그 전(8-29~9-13)은 네트워크 우선이라 재방문마다 원본(gzip 1MB)을 다시 받았다 — 폰 4G 에서 4~11초,
  //   실측 부팅 시간의 최대 단일 항목이었다. 이제는 이 워커 버전과 같은 HTML 이 캐시에 있으면 즉시 주고,
  //   뒤에서 no-cache 로 한 번 더 받아 캐시를 갱신한다(버전이 같을 때만 저장 — 위 htmlMatchesThisWorker).
  //   새 배포는 sw.js?v= 가 바뀌어 새 워커가 설치되고(install 이 새 HTML 을 미리 받음) controllerchange →
  //   한 번 다시 들어가는 기존 흐름 그대로 반영된다. 워커 감지가 막혀도 _mwSelfHeal(version.txt) 이 있다.
  //   privacy/terms/guide 같은 다른 .html 은 예전처럼 네트워크 우선.
  const isAppHtml = url.origin === self.location.origin &&
    (url.pathname.endsWith('/index.html') || url.pathname.endsWith('/') || url.pathname === '/Murpy' || url.pathname === '/Murpy/');
  if (isAppHtml) {
    e.respondWith((async () => {
      let cached = null;
      try { cached = await (await caches.open(STATIC_CACHE)).match(HTML_KEY); } catch (err) {}
      const net = fetchAndStoreHtml(e.request);
      if (cached) {
        try { e.waitUntil(net.catch(() => {})); } catch (err) {}   // 워커 수명 연장이 안 되더라도 응답은 준다
        return cached;
      }
      try { return await net; }
      catch (err) { return fetch(e.request).catch(() => caches.match(HTML_KEY)); }
    })());
    return;
  }
  if (url.origin === self.location.origin && url.pathname.endsWith('.html')) {
    e.respondWith(
      fetch(e.request, { cache: 'no-cache' }).then(res => {
        const clone = res.clone();
        caches.open(STATIC_CACHE).then(c => c.put(e.request, clone));
        return res;
      }).catch(() => fetch(e.request).catch(() => caches.match(e.request)))
    );
    return;
  }

  // ★9-07 로컬 이미지(char/**·아이콘)는 버전 없는 IMG_CACHE 로 — STATIC_CACHE 는 이름에 버전이 박혀 있어
  //   **배포마다 공원 2.8MB 포함 이미지 전부가 지워지고 다시 받았다**(머피월드·필드이동 느림의 최대 원인).
  //   파일이 바뀌면 ?v= 가 바뀌어 주소가 달라지니 캐시 우선이 안전하다(스토리지와 같은 논리).
  if (url.origin === self.location.origin && /\.(png|jpe?g|webp|gif|mp3|wav)$/i.test(url.pathname)) {
    e.respondWith(
      caches.open(IMG_CACHE).then(async cache => {
        const cached = await cache.match(e.request);
        // ★9-09: 캐시된 게 진짜 이미지/오디오가 아니면(빈 응답·HTML 등) 버리고 다시 받는다 — 자가 치유(대표 폰 골프 에셋 실종)
        const ct = cached ? (cached.headers.get('content-type') || '') : '';
        if (cached && cached.status === 200 && /^(image|audio|video)\//.test(ct)) return cached;
        if (cached) { try { await cache.delete(e.request); } catch (err) {} }
        const res = await fetch(e.request);
        if (res && res.ok && /^(image|audio|video)\//.test(res.headers.get('content-type') || '')) cache.put(e.request, res.clone());
        return res;
      }).catch(() => fetch(e.request))
    );
    return;
  }

  // 기타 로컬 정적 파일 → 캐시 우선
  if (url.origin === self.location.origin) {
    e.respondWith(
      caches.open(STATIC_CACHE).then(async cache => {
        const cached = await cache.match(e.request);
        if (cached) return cached;
        const res = await fetch(e.request);
        // ★9-07: 404/5xx 를 캐시하면 배포 직후 잠깐 없던 파일이 영원히 깨진 채 남는다(NPC 시트 실종) — 정상 응답만 넣는다
        if (res && res.ok) cache.put(e.request, res.clone());
        return res;
      })
    );
  }
});
