// ───────────────────────────────────────────────────────────
// ★10-28 속도 — 명예의 전당 서버 집계 stats/hof (홈 '이번 달 인증 1위 · 내 순위' 한 줄 · 월요일 1위 팝업).
//   예전: 홈에 들어올 때마다 앱이 users 를 통째로(회원 수만큼, 251명 수백 KB) 읽어 순위를 셌다.
//   지금: 매시 정각 여기서 한 번 계산해 stats/hof 1개에 써 둔다. 앱은 그 문서만 읽고 '내 줄'만 내 지금 수로 고친다.
//   계산식은 hof_logic.js(앱 window._hofRank 와 같은 식). 문서가 없거나 2시간 넘게 오래됐거나 달이 다르면
//   앱이 예전 방식(전원 읽기)으로 직접 계산한다. 명예의 전당 패널은 늘 전원을 읽는다(정확한 값).
// ───────────────────────────────────────────────────────────
const { onSchedule } = require("firebase-functions/v2/scheduler");
const { getFirestore, FieldValue } = require("firebase-admin/firestore");
const H = require("./hof_logic.js");

const REGION = "asia-northeast3";
const db = () => getFirestore();
const FIELDS = ["nickname", "deleted", "isAnonymous", "monthly", "hostStats", "character", "hofMsg", "characterSheet", "characterHair", "gender"];

async function computeHof(now) {
  const snap = await db().collection("users").select(...FIELDS).get();
  return H.computeHofFrom(snap.docs.map((d) => Object.assign({ uid: d.id }, d.data())), now);
}

exports.hofHourly = onSchedule({ region: REGION, schedule: "every 60 minutes" }, async () => {
  const r = await computeHof(Date.now());
  await db().collection("stats").doc("hof").set(Object.assign(r, { at: FieldValue.serverTimestamp() }));
});
exports._computeHof = computeHof;
