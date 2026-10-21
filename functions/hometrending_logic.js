// 홈 "지금 인기" 서버 집계 — 순수 계산(테스트 test/hometrending_logic.test.js).
//   ★앱 index.html loadHomeTrending 의 계산식을 그대로 옮겼다(대표 10-21). 한쪽만 고치면 순위가 어긋난다 —
//     앱 쪽은 이 문서가 없거나 2시간 넘게 오래됐을 때만 예전 방식(전원 읽기)으로 같은 계산을 한다.
//   ★CHAR_DEFAULT·EXCLUDE_UID 는 앱의 window.CHAR_DEFAULT·window.HOF_EXCLUDE_UID 와 같은 값이어야 한다.
const CHAR_DEFAULT = { skin: "#F0C9A0", hair: "hair_m_basic", hairColor: "#2B2B2B", top: "top_basic_tee", topColor: "#3D7EFF", bottom: "bottom_basic_shorts", shoes: null, acc: null, hat: null, mask: null, body: "human" };
const EXCLUDE_UID = ["3ojRNNyRutYE4IDQn2GrJDcXz0Q2"];   // 관리자 패수현(명예의 전당과 같은 목록)
const DRESS_SLOTS = ["bottom", "shoes", "top", "hair", "hat", "acc", "mask"];
const CAND = 20, CHAR_ROTATE_POOL = 5, KST_MS = 9 * 3600e3;

const msOf = (v) => (v && typeof v.toMillis === "function" ? v.toMillis() : Number(v || 0));
const kstDayKey = (ms) => new Date(ms + KST_MS).toISOString().slice(0, 10).replace(/-/g, "");

const dressedN = (c) => (c ? DRESS_SLOTS.filter((k) => c[k] && c[k] !== CHAR_DEFAULT[k]).length : 0);
const nFurn = (r) => (r && Array.isArray(r.f) ? r.f.length : 0);

function freshBonus(u, now) {
  const at = msOf(u && u.characterUpdatedAt), span = 14 * 864e5;
  if (!at) return 0;
  const age = Math.max(0, now - at);
  return age < span ? 2 * (1 - age / span) : 0;
}
const cScore = (u, like, now) => Math.sqrt(Math.max(0, like || 0)) * 3 + dressedN(u.character) * 1.2 + freshBonus(u, now);
const rScore = (x) => x.like * 3 + x.vis * 1 + nFurn(x.u.room) * 1.0;

// users = [{uid, ...문서}] — 앱의 usersSnap.docs 순서(문서 id 순)와 같게 uid 로 정렬해서 쓴다
const baseUsers = (users) => users.slice().sort((a, b) => (a.uid < b.uid ? -1 : a.uid > b.uid ? 1 : 0))
  .filter((u) => u.nickname && !u.deleted && EXCLUDE_UID.indexOf(u.uid) < 0);

const charCandidates = (all, now) => all.filter((u) => u.character && dressedN(u.character) > 0)
  .sort((a, b) => cScore(b, 0, now) - cScore(a, 0, now)).slice(0, CAND);

function charPool(cands, likes, now, n) {
  const d = cands.map((u) => ({ u, like: likes[u.uid] || 0 }));
  d.sort((a, b) => cScore(b.u, b.like, now) - cScore(a.u, a.like, now) || String(a.u.uid).localeCompare(String(b.u.uid)));
  return d.slice(0, n || CHAR_ROTATE_POOL);
}

function pickFeatured(pool, dayKey) {
  let h = 0;
  for (let i = 0; i < dayKey.length; i++) h = ((h * 31) + dayKey.charCodeAt(i)) >>> 0;
  return pool.length ? pool[h % pool.length] : null;
}

const roomCandidates = (all) => all.filter((u) => nFurn(u.room) > 0).sort((a, b) => nFurn(b.room) - nFurn(a.room)).slice(0, CAND);

function roomTop(cands, likes, visits) {
  const r = cands.map((u) => ({ u, like: likes[u.uid] || 0, vis: visits[u.uid] || 0 }));
  r.sort((a, b) => rScore(b) - rScore(a));
  return r[0] || null;
}

// 앱은 여기서 본인을 빼고 2명을 쓴다 → 서버는 3명을 넘긴다
const runners = (all, n) => all.filter((u) => (u.photoURL || u.firestorePhotoURL) && (u.streak || 0) >= 2)
  .sort((a, b) => (b.streak || 0) - (a.streak || 0)).slice(0, n);

module.exports = { CHAR_DEFAULT, EXCLUDE_UID, CAND, CHAR_ROTATE_POOL, kstDayKey, dressedN, nFurn, freshBonus, cScore, rScore, baseUsers, charCandidates, charPool, pickFeatured, roomCandidates, roomTop, runners };
