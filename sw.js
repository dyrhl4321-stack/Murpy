const CACHE_NAME = 'murpy-v9';
const STATIC_CACHE = 'murpy-static-v9';
const CDN_CACHE = 'murpy-cdn-v9';

// 앱 시작 시 즉시 캐시할 로컬 파일
const STATIC_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './icon.svg',
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
          .filter(k => ![CACHE_NAME, STATIC_CACHE, CDN_CACHE].includes(k))
          .map(k => caches.delete(k))
      )
    ).then(() => clients.claim())
  );
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;

  const url = new URL(e.request.url);

  // Firestore / Firebase Auth API → 네트워크만 (실시간 데이터)
  if (url.hostname.includes('firestore.googleapis.com') ||
      url.hostname.includes('identitytoolkit.googleapis.com') ||
      url.hostname.includes('securetoken.googleapis.com') ||
      url.hostname.includes('firebase.googleapis.com') ||
      url.pathname.includes('/v2/user/me')) {
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
  if (url.origin === self.location.origin && (url.pathname.endsWith('.html') || url.pathname.endsWith('/') || url.pathname === '/Murpy' || url.pathname === '/Murpy/')) {
    e.respondWith(
      fetch(e.request).then(res => {
        const clone = res.clone();
        caches.open(STATIC_CACHE).then(c => c.put(e.request, clone));
        return res;
      }).catch(() => caches.match(e.request))
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
