// FCM 백그라운드 푸시 (앱/탭이 꺼져 있을 때 시스템 알림 표시)
importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: "AIzaSyBvMB4T-ApzHDsfmBx4f5HpPmgkqlcZ7VQ",
  authDomain: "murpyprototype.firebaseapp.com",
  projectId: "murpyprototype",
  storageBucket: "murpyprototype.firebasestorage.app",
  messagingSenderId: "534058034338",
  appId: "1:534058034338:web:6aee952dfb648a612b23fb"
});

const messaging = firebase.messaging();

// ★★알림이 두 번 뜨던 원인 (대표 8-14: "푸시알람이 두 번씩 계속 뜸").
//   서버가 notification 필드를 함께 보내면 **브라우저가 스스로 하나를 띄운다.**
//   그런데 여기서 onBackgroundMessage 가 또 showNotification 을 불러 **두 번째**가 떴다.
//   → 브라우저가 이미 띄웠으면(=payload.notification 이 있으면) 우리는 손대지 않는다.
//     서버가 data 만 보내는 경우에만 우리가 띄운다. 어느 쪽이든 **정확히 한 번**이다.
messaging.onBackgroundMessage(payload => {
  if (payload && payload.notification) return;      // 브라우저가 이미 띄웠다
  const n = (payload && payload.data) || {};
  self.registration.showNotification(n.title || '머피', {
    body: n.body || '',
    // ★icon = 알림에 크게 뜨는 그림. badge = 상태표시줄의 작은 흑백 실루엣.
    //   둘 다 icon-192 를 쓰면 상태표시줄에 큰 로고가 우겨넣어져 뭉개진다(대표 8-14: "로고가 너무 크다").
    icon: './icon-192.png?v=595',
    badge: './badge-72.png?v=595',
    data: n,
    tag: n.type || 'murpy',
    renotify: true
  });
});

// ★★푸시를 누르면 **그 알림이 가리키는 화면**으로 간다 (대표 8-14: "푸시를 탭하면 항상 홈").
//   예전엔 열려 있는 창을 focus 만 했다 — 그래서 늘 마지막에 보던 화면(대개 홈)이었다.
//   앱이 ?n=<종류> 를 읽어 해당 화면으로 보내주므로, 여기서는 주소만 만들어 주면 된다.
function routeUrl(d) {
  d = d || {};
  // FCM 이 스스로 띄운 알림은 data 가 한 겹 더 싸여 있다
  if (d.FCM_MSG && d.FCM_MSG.data) d = d.FCM_MSG.data;
  const q = new URLSearchParams();
  if (d.type) q.set('n', d.type);
  if (d.fromUid) q.set('f', d.fromUid);
  if (d.postId) q.set('p', d.postId);
  if (d.squadId) q.set('sq', d.squadId);
  const qs = q.toString();
  return 'https://murpy.app/' + (qs ? ('?' + qs) : '');
}

self.addEventListener('notificationclick', e => {
  // ★FCM 이 스스로 띄운 알림(data 에 FCM_MSG 가 들어 있다)은 **클릭 처리도 FCM 이 한다**
  //   (서버의 fcmOptions.link 로 열어준다). 여기서 또 열면 창이 두 개 뜬다. 손대지 않는다.
  const _d = e.notification.data || {};
  if (_d.FCM_MSG) return;
  e.notification.close();
  const url = routeUrl(e.notification.data);
  e.waitUntil(clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
    // 이미 머피가 열려 있으면 그 창을 그 주소로 **돌려준다**(focus 만 하면 홈에 머문다)
    for (const c of list) {
      if (c.url && c.url.indexOf('murpy.app') !== -1) {
        if ('navigate' in c) { return c.navigate(url).then(w => w && w.focus()).catch(() => c.focus()); }
        return c.focus();
      }
    }
    if (clients.openWindow) return clients.openWindow(url);
  }));
});
