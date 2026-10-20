// 홈 "오늘 n명 운동" 하루 집계 — 순수 계산(테스트 test/homestats_logic.test.js).
//   ★날짜 경계 = 자정 KST(대표 10-20 확정). 앱 renderHomeLiveBar 와 같은 기준이어야 한다.
const KST_MS = 9 * 3600e3, DAY_MS = 864e5;

const dayKey = (ms) => new Date(ms + KST_MS).toISOString().slice(0, 10).replace(/-/g, "");

function dayRange(key) {
  const a = Date.UTC(+key.slice(0, 4), +key.slice(4, 6) - 1, +key.slice(6, 8)) - KST_MS;
  return [a, a + DAY_MS];
}

const lastKeys = (ms, n) => Array.from({ length: n }, (_, i) => dayKey(ms - i * DAY_MS));

// posts = 그날 글(최신이 먼저). 고유 인원 + 서로 다른 사람 최근 3명의 사진(없으면 '').
function aggregate(posts) {
  const uids = [], recent = [], seen = new Set();
  (posts || []).forEach((p) => {
    const u = p && p.userId;
    if (!u || seen.has(u)) return;
    seen.add(u); uids.push(u);
    if (recent.length < 3) recent.push({ uid: u, photo: String(p.userPhoto || "") });
  });
  return { n: uids.length, uids, recent };
}

module.exports = { dayKey, dayRange, lastKeys, aggregate };
