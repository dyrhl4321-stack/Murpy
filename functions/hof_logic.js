// 명예의 전당 서버 집계 — 순수 계산(테스트 test/hof_logic.test.js).
//   ★앱 index.html 의 window.HOF_KINDS(feed·checkin·host·attend)·window._hofRank 식을 그대로 옮겼다(10-28 속도).
//     한쪽만 고치면 홈 한 줄·월요일 팝업의 순위가 명예의 전당 패널(앱이 전원 읽어 직접 계산)과 어긋난다.
//   ★EXCLUDE_UID 는 앱의 window.HOF_EXCLUDE_UID 와 같은 값이어야 한다(hometrending_logic.js 와도 같음).
//   게임 종목(dodge·golf·tennis·run)은 넣지 않는다 — 패널을 열 때만 쓰고, 패널은 지금처럼 전원을 읽는다.
const { EXCLUDE_UID } = require("./hometrending_logic.js");

const KST_MS = 9 * 3600e3;
// 앱 mwSeasonKey 는 폰 시각(한국) 기준 'YYYY-MM'
const kstMonthKey = (ms) => new Date(ms + KST_MS).toISOString().slice(0, 7);

const mo = (u, m) => (u.monthly || {})[m] || {};
const KINDS = {
  feed:    { get: (u, m) => mo(u, m).feed || 0 },
  checkin: { get: (u, m) => mo(u, m).checkin || 0 },
  host:    { get: (u) => (u.hostStats || {}).hosted || 0,
             sub: (u) => { const c = (u.hostStats || {}).completed || 0; return c ? "완료 " + c + "회" : ""; } },
  attend:  { get: (u, m) => mo(u, m).squad || 0 },
};

// 앱 _hofRank 와 같다: 0회·탈퇴·익명·닉네임 없음·제외 uid 빼고, 많은 순 → 동점은 닉네임 가나다순
function rank(users, kind, month) {
  const def = KINDS[kind]; if (!def) return [];
  return (users || [])
    .filter((u) => u && u.nickname && !u.deleted && !u.isAnonymous && EXCLUDE_UID.indexOf(u.uid) < 0 && def.get(u, month) > 0)
    .map((u) => ({ uid: u.uid, nick: u.nickname, n: def.get(u, month), sub: def.sub ? def.sub(u) : "" }))
    .sort((a, b) => (b.n - a.n) || String(a.nick).localeCompare(String(b.nick), "ko"))
    .map((r, i) => Object.assign(r, { rank: i + 1 }));
}

// 1위가 팝업에 그려진다 — 그 사람의 커마·한마디·커마 몸통 재료만 같이 담는다(전원 스냅샷이 없으니)
const topInfo = (u) => ({
  character: u.character || null, hofMsg: u.hofMsg || "",
  characterSheet: u.characterSheet || null, characterHair: u.characterHair || null, gender: u.gender || null,
});

function computeHofFrom(users, now) {
  const month = kstMonthKey(now), rows = {}, top = {}, byUid = {};
  (users || []).forEach((u) => { byUid[u.uid] = u; });
  Object.keys(KINDS).forEach((k) => {
    rows[k] = rank(users, k, month);
    const t = rows[k][0];
    if (t && byUid[t.uid]) top[t.uid] = topInfo(byUid[t.uid]);
  });
  return { month, atMs: now, rows, top, users: (users || []).length };
}

module.exports = { KINDS, kstMonthKey, rank, topInfo, computeHofFrom };
