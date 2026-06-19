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

messaging.onBackgroundMessage(payload => {
  const n = (payload && (payload.data || payload.notification)) || {};
  self.registration.showNotification(n.title || '머피', {
    body: n.body || '',
    icon: './icon.svg',
    badge: './icon.svg',
    data: n,
    tag: n.type || 'murpy'
  });
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
    for (const c of list) { if ('focus' in c) return c.focus(); }
    if (clients.openWindow) return clients.openWindow('./');
  }));
});
