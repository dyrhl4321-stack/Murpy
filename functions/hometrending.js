// ───────────────────────────────────────────────────────────
// ★10-21 렉 근본 수정 b-7 — 홈 "지금 인기"(인기 캐릭터·인기 룸·운동 열정러) 서버 집계.
//   예전: 앱이 켤 때마다 users 를 통째로(회원 수만큼) 읽고 후보 좋아요·방문 문서 수십 개를 낱개로 읽었다.
//   지금: 매시 정각 여기서 한 번 계산해 stats/home_trending 문서 1개에 써 둔다. 앱은 그 문서만 읽는다.
//   계산식은 hometrending_logic.js(앱과 같은 식). 하루 한 명 고정(날짜 해시)은 앱이 후보 5명 중에서 고른다.
//   문서가 없거나 2시간 넘게 오래되면 앱이 예전 방식으로 직접 계산한다(화면이 깨지지 않게).
// ───────────────────────────────────────────────────────────
const { onSchedule } = require("firebase-functions/v2/scheduler");
const { getFirestore, FieldValue } = require("firebase-admin/firestore");
const T = require("./hometrending_logic.js");

const REGION = "asia-northeast3";
const db = () => getFirestore();
const FIELDS = ["nickname", "deleted", "character", "characterUpdatedAt", "room", "photoURL", "firestorePhotoURL", "streak", "age", "characterSheet", "characterHair", "gender"];

async function countOf(uid, sub, id) {
  try {
    const s = await db().collection("users").doc(uid).collection(sub).doc(id).get();
    return Math.max(0, (s.exists && s.data().count) || 0);
  } catch (e) { return 0; }
}

// 남의 커마 몸통을 앱이 그리려면 characterSheet·characterHair·gender 가 같이 있어야 한다(_charEnsureFaceBody)
const face = (u) => ({ characterSheet: u.characterSheet || null, characterHair: u.characterHair || null, gender: u.gender || null });

async function computeHomeTrending(now) {
  const snap = await db().collection("users").select(...FIELDS).get();
  const all = T.baseUsers(snap.docs.map((d) => Object.assign({ uid: d.id }, d.data())));
  const day = T.kstDayKey(now);

  const cc = T.charCandidates(all, now), likesC = {};
  await Promise.all(cc.map(async (u) => { likesC[u.uid] = await countOf(u.uid, "likestat", "char"); }));
  const pool = T.charPool(cc, likesC, now).map(({ u, like }) => Object.assign({ uid: u.uid, like, nickname: u.nickname || "", character: u.character }, face(u)));

  const rc = T.roomCandidates(all), likesR = {}, vis = {};
  await Promise.all(rc.map(async (u) => { likesR[u.uid] = await countOf(u.uid, "likestat", "room"); vis[u.uid] = await countOf(u.uid, "roomstat", day); }));
  const top = T.roomTop(rc, likesR, vis);
  const room = top ? Object.assign({ uid: top.u.uid, like: top.like, vis: top.vis, nickname: top.u.nickname || "", character: top.u.character || null, room: top.u.room }, face(top.u)) : null;

  const runners = T.runners(all, 3).map((u) => ({ uid: u.uid, nickname: u.nickname || "", age: u.age || null, photoURL: u.photoURL || "", firestorePhotoURL: u.firestorePhotoURL || "", streak: u.streak || 0 }));
  return { day, atMs: now, charPool: pool, room, runners, users: all.length };
}

exports.homeTrendingHourly = onSchedule({ region: REGION, schedule: "every 60 minutes" }, async () => {
  const r = await computeHomeTrending(Date.now());
  await db().collection("stats").doc("home_trending").set(Object.assign(r, { at: FieldValue.serverTimestamp() }));
});
exports._computeHomeTrending = computeHomeTrending;
