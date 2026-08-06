// 매칭 탭에 특정 사람을 다시 띄운다 (홍보용 스크린샷 찍을 때만 쓰는 도구)
//
// 왜 안 보이나
//   index.html:9881 이 이미 좋아요/매칭/패스한 상대를 매칭 후보에서 뺀다.
//   그 예외가 window.TEST_UIDS 인데 2026-08-05 출시 준비로 **비워뒀다**(index.html:7351).
//   그래서 관리자 계정에서도 김현수처럼 이미 처리한 상대가 안 뜬다.
//
// 이 스크립트가 하는 일
//   내 uid 를 TEST_UIDS 에 잠깐 넣고 후보를 다시 불러온다(window.loadMatchCandidates).
//   그러면 제외 규칙이 통째로 꺼져서 전원이 다시 뜬다. 그 다음 원하는 사람으로 카드를 넘긴다.
//   ★DB 는 건드리지 않는다. 새로고침하면 원래대로 돌아간다.
//
// 쓰는 법
//   1) https://murpy.app 를 PC 크롬에서 열고 로그인 (스크린샷 찍을 계정으로)
//   2) 매칭 탭을 한 번 누른다
//   3) F12 -> Console 에 이 파일 전체를 붙여넣고 Enter
//   4) 못 찾으면 콘솔에 전체 닉네임이 찍힌다. NICKNAME 을 거기 맞춰 고치고 다시 실행.
(async () => {
  const NICKNAME = '김현수';          // ← 띄우고 싶은 사람 (일부만 적어도 된다)

  if (!window.currentUser) { console.error('로그인부터 하세요.'); return; }
  if (typeof window.loadMatchCandidates !== 'function') {
    console.error('매칭 화면이 아직 안 떴습니다. 매칭 탭을 한 번 누른 뒤 다시 실행하세요.');
    return;
  }

  // 1) 나를 테스터로 등록 -> 제외 규칙(좋아요/매칭/패스) 무효화
  window.TEST_UIDS = [window.currentUser.uid];

  // 2) 후보 다시 불러오기 (_matchLoading 이 걸려 있으면 풀고)
  window._matchLoading = false;
  window._matchPassed = new Set();
  window._matchLiked = new Set();
  await window.loadMatchCandidates();

  const list = window._matchList || [];
  console.log(`후보 ${list.length}명 다시 불러왔습니다.`);
  if (!list.length) { console.error('후보가 0명입니다. 로그인/네트워크를 확인하세요.'); return; }

  // 3) 원하는 사람 찾기 (부분 일치도 허용)
  const key = NICKNAME.replace(/\s/g, '');
  let at = list.findIndex(p => (p.nickname || '').replace(/\s/g, '') === key);
  if (at < 0) at = list.findIndex(p => (p.nickname || '').replace(/\s/g, '').includes(key));

  if (at < 0) {
    console.error(`'${NICKNAME}' 를 못 찾았습니다. 아래 닉네임 중에서 골라 NICKNAME 을 고치세요:`);
    console.log(list.map((p, i) => `${i}: ${p.nickname}`).join('\n'));
    console.log('※ 번호로 바로 띄우려면:  window._matchIdx = 번호; renderMatch();');
    return;
  }

  window._matchIdx = at;
  if (typeof window.renderMatch === 'function') window.renderMatch();
  console.log(`'${list[at].nickname}' 카드가 떴습니다 (${at}번). 스크린샷 찍으세요.`);
  console.log('※ DB 는 안 건드렸습니다. 새로고침하면 원래대로 돌아갑니다.');
  console.log('※ 다른 사람도 보려면:  window._matchIdx = 번호; renderMatch();');
})();
