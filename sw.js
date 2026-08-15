// 諛고룷留덈떎 ??踰꾩쟾???щ젮???먮룞 ?덈쾭???곸슜(?덈줈怨좎묠)???숈옉??const CACHE_NAME = 'murpy-v604';
const STATIC_CACHE = 'murpy-static-v604';
const CDN_CACHE = 'murpy-cdn-v604';
// ?대?吏 罹먯떆??踰꾩쟾 ??遺숈엫 ??肄붾뱶/HTML 諛고룷?대룄 ?좎?(URL??怨?踰꾩쟾)
const IMG_CACHE = 'murpy-img';

// ???쒖옉 ??利됱떆 罹먯떆??濡쒖뺄 ?뚯씪
const STATIC_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './favicon-32.png',
  './icon-192.png',
  './icon-512.png',
  './logo-nukki.png',
];

// CDN ?ㅽ겕由쏀듃 (踰꾩쟾 怨좎젙 ???곴뎄 罹먯떆)
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
    ).then(() => clients.claim())
  );
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;

  const url = new URL(e.request.url);

  // Firestore / Firebase Auth API ???ㅽ듃?뚰겕留?(?ㅼ떆媛??곗씠??
  if (url.hostname.includes('firestore.googleapis.com') ||
      url.hostname.includes('identitytoolkit.googleapis.com') ||
      url.hostname.includes('securetoken.googleapis.com') ||
      url.hostname.includes('firebase.googleapis.com') ||
      url.pathname.includes('/v2/user/me')) {
    return;
  }

  // ?꾨줈???쇰뱶 ?대?吏 (weserv 由ъ궗?댁쫰, imgBB) ??罹먯떆 ?곗꽑 (URL??怨?踰꾩쟾)
  if (url.hostname.includes('images.weserv.nl') || url.hostname.includes('ibb.co')) {
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

  // CDN ?ㅽ겕由쏀듃 ??罹먯떆 ?곗꽑 (踰꾩쟾 怨좎젙 ?뚯씪)
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

  // HTML ?뚯씪 ???ㅽ듃?뚰겕 ?곗꽑 (??긽 理쒖떊 踰꾩쟾)
  // ?꿤ache:'no-store' 濡?諛쏅뒗?? 洹몃깷 fetch ?섎㈃ 釉뚮씪?곗? HTTP 罹먯떆? GitHub Pages CDN ??  //   ??index.html ??洹몃?濡?二쇨린 ?뚮Ц?? sw 踰꾩쟾???щ젮???붾㈃????쾶 諛붾뚯뿀??  //   (??? "?몄떆??寃?怨꾩냽 ??쾶 諛섏쁺?쒕떎"). no-store 硫?留ㅻ쾲 ?먮낯源뚯? 媛꾨떎.
  if (url.origin === self.location.origin && (url.pathname.endsWith('.html') || url.pathname.endsWith('/') || url.pathname === '/Murpy' || url.pathname === '/Murpy/')) {
    e.respondWith(
      fetch(e.request, { cache: 'no-store' }).then(res => {
        const clone = res.clone();
        caches.open(STATIC_CACHE).then(c => c.put(e.request, clone));
        return res;
      }).catch(() => fetch(e.request).catch(() => caches.match(e.request)))
    );
    return;
  }

  // 湲고? 濡쒖뺄 ?뺤쟻 ?뚯씪 ??罹먯떆 ?곗꽑
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




