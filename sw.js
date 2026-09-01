// 배포마다 이 버전을 올려야 자동 새버전 적용(새로고침)이 동작함
const CACHE_NAME = 'murpy-v878';
const STATIC_CACHE = 'murpy-static-v878';
const CDN_CACHE = 'murpy-cdn-v878';
// 이미지 캐시는 버전 안 붙임 → 코드/HTML 배포해도 유지(URL이 곧 버전)
const IMG_CACHE = 'murpy-img';

// 앱 시작 시 즉시 캐시할 로컬 파일
const STATIC_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './favicon-32.png',
  './icon-192.png',
  './icon-512.png',
  './logo-nukki.png',
];

// CDN 스크립트 (버전 고정 → 영구 캐시)
const CDN_HOSTS = [
  'www.gstatic.com',
  't1.kakaocdn.net',
];

self.addEventListener('install', e => {
  self.skipWaiting();
  e.waitUntil(
    caches.open(STATIC_CACHE).then(cache =>
      cache.addAll(STATIC_ASSETS).catch(() => {})
    )
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
        if (cached) return cached;
        const res = await fetch(e.request);
        if (res && res.ok) cache.put(e.request, res.clone());
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
        cache.put(e.request, res.clone());
        return res;
      })
    );
    return;
  }

  // HTML 파일 → 네트워크 우선 (항상 최신 버전)
  // ★cache:'no-store' 로 받는다. 그냥 fetch 하면 브라우저 HTTP 캐시와 GitHub Pages CDN 이
  //   옛 index.html 을 그대로 주기 때문에, sw 버전을 올려도 화면이 늦게 바뀌었다
  //   (대표: "푸시한 게 계속 늦게 반영된다"). no-store 면 매번 원본까지 간다.
  if (url.origin === self.location.origin && (url.pathname.endsWith('.html') || url.pathname.endsWith('/') || url.pathname === '/Murpy' || url.pathname === '/Murpy/')) {
    e.respondWith(
      // ★8-29: no-store → **no-cache**. 매번 원본에 물어보는 건 같지만(ETag 재검증) 안 바뀌었으면 304 로
      //   본문(gzip 740KB)을 안 받는다. 1,000명이면 월 66GB → 수 GB. 최신성은 그대로다.
      fetch(e.request, { cache: 'no-cache' }).then(res => {
        const clone = res.clone();
        caches.open(STATIC_CACHE).then(c => c.put(e.request, clone));
        return res;
      }).catch(() => fetch(e.request).catch(() => caches.match(e.request)))
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
        cache.put(e.request, res.clone());
        return res;
      })
    );
  }
});
