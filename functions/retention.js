// ─────────────────────────────────────────────────────────────────────────────
// 리텐션 알림 (2026-08-30, 대표: "사람들이 결국 운동을 많이 나오게끔 유도해줘야 해 …
//   리텐션 알림 붙일 수 있는 건 다 붙여 버리자")
//
// 원칙
//  · 새 발송 경로를 만들지 않는다. **notifications 문서를 만들면** 기존 sendNotifPush 가 푸시한다.
//  · 푸시 토큰이 있는 사람에게만 만든다 — 알림함만 채우는 문서는 읽기 비용만 든다.
//  · 문서 id 를 **결정적으로** 만들어 같은 알림이 두 번 안 간다(create 는 있으면 실패 → 무시).
//  · 하루 상한: 같은 종류는 사람당 하루 1건. 쪼아대는 것과 스팸은 한 끗 차이다.
//
// 종류
//  friend_workout  범프한 친구가 운동 인증을 올렸다        (feed 생성)
//  bamboo_nearby   우리 동네 대숲에 글이 올라왔다            (bamboo 생성)
//  gym_now         내 헬스장에 누가 지금 체크인했다           (checkins 생성)
//  squad_again     전에 같이 했던 스쿼드장이 또 열었다         (squads 생성)
//  squad_nearby    내 헬스장에서 스쿼드가 열렸다              (squads 생성)
//  nag             마지막 운동 인증이 7일 넘었다               (매일 19:00 KST)
// ─────────────────────────────────────────────────────────────────────────────
const { onDocumentCreated } = require("firebase-functions/v2/firestore");
const { onSchedule } = require("firebase-functions/v2/scheduler");
const { getFirestore, FieldValue } = require("firebase-admin/firestore");

const REGION = "asia-northeast3";
const db = () => getFirestore();

const kstDay = (d) => {
  const t = new Date((d ? d.getTime() : Date.now()) + 9 * 3600 * 1000);
  return t.toISOString().slice(0, 10);
};
const dayKey = () => kstDay().replace(/-/g, "");

// 결정적 id 로 만든다. 이미 있으면 create 가 던지고, 그건 '이미 보냈다'는 뜻이다.
async function notifyOnce(id, payload) {
  try {
    await db().collection("notifications").doc(id).create({
      read: false, createdAt: FieldValue.serverTimestamp(), ...payload,
    });
    return true;
  } catch (e) {
    if (e && e.code === 6) return false;              // ALREADY_EXISTS
    console.warn("notifyOnce", id, e && e.message);
    return false;
  }
}

// 푸시 토큰이 있는 사람만. 130명 규모라 전부 읽어도 싸다 — 늘면 여기만 바꾼다.
async function pushableUsers() {
  const qs = await db().collection("users").where("fcmTokens", "!=", []).get();
  const out = [];
  qs.forEach((d) => {
    const u = d.data() || {};
    if (u.deleted || !Array.isArray(u.fcmTokens) || !u.fcmTokens.length) return;
    out.push({ uid: d.id, ...u });
  });
  return out;
}
const nickOf = (u) => (u && u.nickname) || "머피";

// ── 1) 범퍼가 운동 인증을 올렸다 ───────────────────────────────────────────
exports.friendWorkout = onDocumentCreated({ region: REGION, document: "feed/{id}" }, async (ev) => {
  const p = ev.data && ev.data.data(); if (!p || !p.userId) return;
  const me = await db().doc("users/" + p.userId).get();
  const bumpers = (me.exists && me.data().bumpers) || {};
  const friends = Object.keys(bumpers).filter((k) => k && k !== p.userId);
  if (!friends.length) return;
  const day = dayKey();
  let sent = 0;
  for (const f of friends) {
    // 친구 한 명에게 같은 사람 소식은 하루 한 번
    const ok = await notifyOnce(`fw_${f}_${p.userId}_${day}`, {
      toUid: f, fromUid: p.userId, fromNickname: p.userName || "친구",
      type: "friend_workout", postId: ev.params.id, postText: p.text || "",
    });
    if (ok) sent++;
  }
  console.log(`friend_workout by=${p.userId} friends=${friends.length} sent=${sent}`);
});

// ── 2) 우리 동네 대숲 ──────────────────────────────────────────────────────
exports.bambooNearby = onDocumentCreated({ region: REGION, document: "bamboo/{id}" }, async (ev) => {
  const p = ev.data && ev.data.data(); if (!p || !p.userId) return;
  const me = await db().doc("users/" + p.userId).get();
  const district = String((me.exists && me.data().district) || "").trim();
  if (!district) return;
  const users = await pushableUsers();
  const day = dayKey();
  let sent = 0;
  for (const u of users) {
    if (u.uid === p.userId) continue;
    if (String(u.district || "").trim() !== district) continue;
    // 동네 대숲 소식은 하루 한 번 — 첫 글이 그날의 알림이 된다
    const ok = await notifyOnce(`bn_${u.uid}_${day}`, {
      toUid: u.uid, fromUid: p.userId, fromNickname: "익명",
      type: "bamboo_nearby", postId: ev.params.id, postText: p.text || "", text: district,
    });
    if (ok) sent++;
  }
  console.log(`bamboo_nearby district=${district} sent=${sent}`);
});

// ── 3) 내 헬스장에 지금 누가 체크인했다 ───────────────────────────────────────
exports.gymNow = onDocumentCreated({ region: REGION, document: "checkins/{id}" }, async (ev) => {
  const c = ev.data && ev.data.data(); if (!c || !c.uid || !c.centerId) return;
  const cid = String(c.centerId);
  const me = await db().doc("users/" + c.uid).get();
  const users = await pushableUsers();
  const day = dayKey();
  let sent = 0;
  for (const u of users) {
    if (u.uid === c.uid) continue;
    const mine = (Array.isArray(u.gyms) ? u.gyms.map(String) : []).concat(u.homeCenterId ? [String(u.homeCenterId)] : []);
    if (!mine.includes(cid)) continue;
    // 같은 헬스장 소식은 하루 한 번
    const ok = await notifyOnce(`gn_${u.uid}_${cid}_${day}`, {
      toUid: u.uid, fromUid: c.uid, fromNickname: nickOf(me.exists && me.data()),
      type: "gym_now", text: c.centerName || "", centerId: cid,
    });
    if (ok) sent++;
  }
  console.log(`gym_now center=${cid} sent=${sent}`);
});

// ── 4) 스쿼드가 열렸다 — 전에 같이 한 사람 + 내 헬스장 사람 ───────────────────
exports.squadOpened = onDocumentCreated({ region: REGION, document: "squads/{id}" }, async (ev) => {
  const s = ev.data && ev.data.data(); if (!s || !s.hostUid) return;
  const sid = ev.params.id;
  const host = await db().doc("users/" + s.hostUid).get();
  const hostNick = nickOf(host.exists && host.data());
  const already = new Set([s.hostUid, ...(Array.isArray(s.memberUids) ? s.memberUids : [])]);
  let sent = 0;

  // (a) 이 스쿼드장의 지난 스쿼드에 왔던 사람들 → squad_again  (캐치테이블처럼 '또 열렸어요')
  const prev = await db().collection("squads").where("hostUid", "==", s.hostUid)
    .orderBy("createdAt", "desc").limit(30).get();
  const past = new Set();
  prev.forEach((d) => {
    if (d.id === sid) return;
    const q = d.data() || {};
    (Array.isArray(q.memberUids) ? q.memberUids : []).forEach((u) => { if (!already.has(u)) past.add(u); });
  });
  for (const u of past) {
    const ok = await notifyOnce(`sa_${u}_${sid}`, {
      toUid: u, fromUid: s.hostUid, fromNickname: hostNick,
      type: "squad_again", squadId: sid, postText: s.title || "",
    });
    if (ok) { sent++; already.add(u); }
  }

  // (b) 그 헬스장을 다니는 사람들 → squad_nearby
  if (s.centerId) {
    const cid = String(s.centerId);
    const users = await pushableUsers();
    for (const u of users) {
      if (already.has(u.uid)) continue;
      const mine = (Array.isArray(u.gyms) ? u.gyms.map(String) : []).concat(u.homeCenterId ? [String(u.homeCenterId)] : []);
      if (!mine.includes(cid)) continue;
      const ok = await notifyOnce(`sn_${u.uid}_${sid}`, {
        toUid: u.uid, fromUid: s.hostUid, fromNickname: hostNick,
        type: "squad_nearby", squadId: sid, postText: s.title || "", text: s.location || "",
      });
      if (ok) { sent++; already.add(u.uid); }
    }
  }
  console.log(`squad opened ${sid} past=${past.size} sent=${sent}`);
});

// ── 5) 일주일 넘게 인증이 없다 — 매일 19:00 KST ────────────────────────────────
//   기준 = users.creditsLastEarned (운동 인증으로 머피를 받은 마지막 날). 한 주에 한 번만 쪼은다.
exports.nagInactive = onSchedule({ region: REGION, schedule: "0 10 * * *", timeZone: "UTC" }, async () => {
  const users = await pushableUsers();
  const today = new Date(kstDay() + "T00:00:00Z").getTime();
  const week = Math.floor(today / (7 * 86400000));
  let sent = 0;
  for (const u of users) {
    const raw = String(u.creditsLastEarned || "").replace(/(\d{4})(\d{2})(\d{2})/, "$1-$2-$3");
    if (!raw) continue;                                   // 한 번도 인증 안 한 사람은 온보딩 몫
    const last = new Date(raw + "T00:00:00Z").getTime();
    if (!isFinite(last)) continue;
    const days = Math.round((today - last) / 86400000);
    if (days < 7) continue;
    const ok = await notifyOnce(`nag_${u.uid}_w${week}`, {
      toUid: u.uid, fromUid: "", fromNickname: "", type: "nag", amount: days,
    });
    if (ok) sent++;
  }
  console.log(`nag sent=${sent} of ${users.length}`);
});
