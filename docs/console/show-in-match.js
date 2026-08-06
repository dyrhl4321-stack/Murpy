// 매칭 탭에 특정 사람을 다시 띄운다 (홍보용 스크린샷 찍을 때만 쓰는 도구)
//
// 왜 필요한가
//   index.html:9881 이 이미 좋아요/매칭/패스한 사람을 매칭 후보에서 뺀다.
//   예외는 window.TEST_UIDS 인데 2026-08-05 출시 준비로 **비워뒀다**(index.html:7351).
//   그래서 관리자 계정에서도 김현수 같은 이미 처리한 상대가 안 보인다.
//
// 이 스크립트는 DB를 건드리지 않는다. 지금 열려 있는 화면의 후보 목록에만 끼워 넣는다.
// 새로고침하면 원래대로 돌아간다. 좋아요를 실제로 보내지만 않으면 아무것도 안 바뀐다.
//
// 쓰는 법
//   1) https://murpy.app 를 PC 크롬에서 열고 로그인 (스크린샷 찍을 계정으로)
//   2) 매칭 탭을 한 번 눌러 후보를 불러온다
//   3) F12 → Console 에 이 파일 전체를 붙여넣고 Enter
//   4) 아래 NICKNAME 을 바꾸면 다른 사람도 띄울 수 있다
(async () => {
  const NICKNAME = '김현수';          // ← 띄우고 싶은 사람 닉네임

  const { getApps } = await import('https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js');
  const { getFirestore, collection, getDocs, query, where } =
    await import('https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js');

  const app = getApps()[0];
  if (!app) { console.error('Firebase 앱이 없습니다. murpy.app 에서 실행하세요.'); return; }
  const db = getFirestore(app);

  const snap = await getDocs(query(collection(db, 'users'), where('nickname', '==', NICKNAME)));
  if (snap.empty) { console.error(`'${NICKNAME}' 를 못 찾았습니다. 닉네임을 정확히 확인하세요.`); return; }
  if (snap.size > 1) console.warn(`같은 닉네임이 ${snap.size}명입니다. 첫 번째를 씁니다.`);

  const d = snap.docs[0];
  const person = { uid: d.id, ...d.data() };

  if (!Array.isArray(window._matchList)) {
    console.error('매칭 후보가 아직 안 불러와졌습니다. 매칭 탭을 한 번 누른 뒤 다시 실행하세요.');
    return;
  }

  // 이미 목록에 있으면 그 자리로 이동, 없으면 맨 앞에 끼워 넣는다
  const at = window._matchList.findIndex(p => p.uid === person.uid);
  if (at >= 0) {
    window._matchIdx = at;
  } else {
    window._matchList.unshift(person);
    window._matchIdx = 0;
  }
  // 좋아요 보낸 사람 건너뛰기(index.html:5193)에 걸리지 않게 이번 화면에서만 뺀다
  if (window._matchLiked) window._matchLiked.delete(person.uid);

  if (typeof window.renderMatch === 'function') window.renderMatch();
  console.log(`'${NICKNAME}' 카드가 매칭 탭에 떴습니다. 스크린샷 찍으세요.`);
  console.log('※ DB는 안 건드렸습니다. 새로고침하면 원래대로 돌아갑니다.');
})();
