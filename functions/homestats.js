// ───────────────────────────────────────────────────────────
// ★10-20 렉 근본 수정 a — 홈 "오늘 n명이 운동 인증했어요" 하루 집계.
//   예전: 앱이 켤 때마다 feed 를 오늘·최근 7일 두 번 limit 400 으로 읽어 직접 셌다.
//   지금: 글이 생기거나 지워질 때 그날(자정 KST) 집계 문서 stats/day_YYYYMMDD 를 다시 센다.
//     앱은 오늘 문서 1개(모자라면 최근 7일 문서)만 읽는다. 규칙 = stats 읽기 공개·쓰기 서버만.
//   매시 정각: 오늘을 다시 세고(동시 글로 어긋난 것 바로잡기), 최근 7일 중 문서가 없는 날을 채운다(첫 배포 백필).
// ───────────────────────────────────────────────────────────
const { onDocumentCreated, onDocumentDeleted } = require("firebase-functions/v2/firestore");
const { onSchedule } = require("firebase-functions/v2/scheduler");
const { getFirestore, Timestamp, FieldValue } = require("firebase-admin/firestore");
const H = require("./homestats_logic.js");

const REGION = "asia-northeast3";
const db = () => getFirestore();
const ref = (key) => db().collection("stats").doc("day_" + key);
const msOf = (v) => (v && typeof v.toMillis === "function" ? v.toMillis() : Number(v || 0));

async function recount(key) {
  const [a, b] = H.dayRange(key);
  const snap = await db().collection("feed")
    .where("createdAt", ">=", Timestamp.fromMillis(a)).where("createdAt", "<", Timestamp.fromMillis(b))
    .orderBy("createdAt", "desc").select("userId", "userPhoto").get();
  const r = H.aggregate(snap.docs.map((d) => d.data()));
  await ref(key).set({ key, n: r.n, uids: r.uids.slice(0, 3000), recent: r.recent, posts: snap.size, at: FieldValue.serverTimestamp() });
  return r.n;
}

async function onPost(data) {
  const ms = msOf(data && data.createdAt);
  if (ms) await recount(H.dayKey(ms));
}

exports.homeStatsOnPost = onDocumentCreated({ region: REGION, document: "feed/{id}" }, (ev) => onPost(ev.data && ev.data.data()));
exports.homeStatsOnDelete = onDocumentDeleted({ region: REGION, document: "feed/{id}" }, (ev) => onPost(ev.data && ev.data.data()));

exports.homeStatsHourly = onSchedule({ region: REGION, schedule: "every 60 minutes" }, async () => {
  const keys = H.lastKeys(Date.now(), 7);
  await recount(keys[0]);
  for (const k of keys.slice(1)) {
    if (!(await ref(k).get()).exists) await recount(k);
  }
});

