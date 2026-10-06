// ─────────────────────────────────────────────────────────────────────────────
// ★10-07 머피 계정 ↔ 근방단 실명 짝 — 관리자 손 없이.
//   대표: "확실한 건 미리 등록해 놓고, 애매한 사람들은 근방단 실제 이름이랑 연결하게 — 내가 하는 게 아니라 지들이".
//   ① gbdLinkHourly: 확실한 짝(이름 정확히 + 출생년도 같음 + 스쿼드에 나온 정식 계정 + 서로 하나뿐)은 바로 등록.
//   ② 나머지 중 **근방단 스쿼드에 나온 적 있는** 정식 계정만 gbdAsk/{uid} 에 "물어볼 사람"으로 적는다.
//      앱이 켜질 때 gbdAsk 로 묻고(짐작 이름이 있으면 "○○○님 맞으세요?", 없으면 실명 입력칸),
//      gbdClaim 이 근방단 명단·출생년도·이미 연결됐는지 확인한 뒤 연결한다.
//   ★일반 유저에겐 아무것도 안 뜬다(근방단 특별대우로 보이면 안 된다 — 대표 10-06).
//   근방단 스쿼드 = 2026-10-07 전 스쿼드 전부(대표: "지금까지 연 스쿼드는 전부 근방단") + 그 뒤엔 근방단 사람·관리자가 연 것.
//   gbdAsk 컬렉션은 규칙에 없어서 앱이 직접 못 읽고 못 쓴다 — 서버만.
// ─────────────────────────────────────────────────────────────────────────────
const { onSchedule } = require("firebase-functions/v2/scheduler");
const { onCall, HttpsError } = require("firebase-functions/v2/https");
const { getFirestore } = require("firebase-admin/firestore");
const { getAuth } = require("firebase-admin/auth");
const S = require("./gbdsync.js");
const L = require("./gbdsync_logic.js");

const REGION = "asia-northeast3";
const ALL_GBD_BEFORE = Date.parse("2026-10-07T00:00:00+09:00");
const ASK_GAP = 20 * 3600 * 1000;   // 하루에 한 번만 묻는다
const MAX_TRIES = 5;                 // 하루에 이름 틀리게 적기 — 남의 이름 떠보기 막기
// 절대 묻지 않을 계정 — 애플 심사 데모 계정 화면에 '근방단 실명'이 뜨면 안 된다
const NEVER_ASK_EMAILS = ["applereview@murpy.app"];
async function neverAskUids() {
  const out = new Set();
  for (const e of NEVER_ASK_EMAILS) { try { out.add((await getAuth().getUserByEmail(e)).uid); } catch (err) { /* 없으면 그만 */ } }
  return out;
}

// 최근 1년 스쿼드에서: 실명 메모(스쿼드장이 붙인 진짜 이름), 근방단 스쿼드 참여 횟수·참여한 계정
async function squadScan(active) {
  const db = getFirestore();
  const q = await db.collection("squads").where("scheduledAt", ">=", Date.now() - 365 * 86400000).get();
  const alias = {}, act = {}, inGbd = new Set();
  const docs = q.docs;
  for (let i = 0; i < docs.length; i += 15) {
    const chunk = docs.slice(i, i + 15);
    const ms = await Promise.all(chunk.map((d) => d.ref.collection("members").get()));
    const adm = await Promise.all(chunk.map((d) => S.isAdminUid((d.data() || {}).hostUid)));
    chunk.forEach((d, k) => {
      const s = d.data() || {};
      const isGbd = (Number(s.scheduledAt) || 0) < ALL_GBD_BEFORE || !!active[s.hostUid] || adm[k];
      ms[k].forEach((md) => {
        const m = md.data() || {};
        if (m.alias && !alias[md.id]) alias[md.id] = m.alias;
        if (!L.isLive(m) || !isGbd) return;
        // 참여 횟수는 **근방단 스쿼드만** — 이름·생년이 같아도 근방단 모임에 안 나온 사람을 자동으로 잇지 않는다
        const a = act[md.id] = act[md.id] || { sq: 0, att: 0, posts: 0 };
        a.sq++;
        if (m.checkedIn || m.checkinType === "present" || m.checkinType === "late") a.att++;
        inGbd.add(md.id);
      });
    });
  }
  // 피드 글(최근 1000개) — 중복 계정 중 메인을 고를 때 보조 점수
  try {
    const fs = await db.collection("feed").orderBy("createdAt", "desc").limit(1000).select("userId").get();
    fs.forEach((d) => { const u = (d.data() || {}).userId; if (u && act[u]) act[u].posts++; });
  } catch (e) { console.warn("gbd feed act", e.message); }
  return { alias, act, inGbd };
}

async function murpyUsers() {
  const snap = await getFirestore().collection("users").select("nickname", "birth", "guest", "mergedInto", "deleted").get();
  const out = [], merged = {};
  snap.forEach((d) => {
    const u = d.data() || {};
    if (u.mergedInto) { merged[d.id] = u.mergedInto; return; }
    if (u.deleted || !u.nickname) return;
    out.push({ uid: d.id, nickname: u.nickname, birth: u.birth || "", guest: !!u.guest });
  });
  out.merged = merged;
  return out;
}
const sameList = (a, b) => JSON.stringify((a || []).slice().sort()) === JSON.stringify((b || []).slice().sort());

async function linkRun() {
  const db = getFirestore();
  const members = await S.gbdMembers();
  const users = await murpyUsers(), merged = users.merged || {};
  const byUid = {}; users.forEach((u) => { byUid[u.uid] = u; });
  const owner = () => {   // 이미 어느 근방단 멤버에 걸린 계정(메인·보조) → 그 멤버 이름
    const t = {};
    members.forEach((m) => { if (m.murpyUid) [m.murpyUid].concat(m.murpyAlts || []).forEach((u) => { if (u && !t[u]) t[u] = m.name; }); });
    return t;
  };
  const active = {};
  members.forEach((m) => { if (m.murpyUid && m.status !== "removed") active[m.murpyUid] = m.name; });
  const scan = await squadScan(active);
  const touched = [];
  const save = async (m, f, uids) => {
    try { await S.patchMember(m, f); Object.assign(m, f); uids.forEach((u) => u && touched.push(u)); return true; }
    catch (e) { console.warn("gbd link save", m.name, e.message); return false; }
  };
  const stamp = () => new Date().toISOString();
  let moved = 0, auto = 0, alts = 0;

  // ⓪ 합쳐진 임시계정에 걸린 짝 → 본계정으로 (대표 10-06: 본계정이 제일 중요)
  for (const m of members) {
    let to = m.murpyUid && merged[m.murpyUid];
    for (let i = 0; to && merged[to] && i < 5; i++) to = merged[to];
    if (!to || owner()[to]) continue;
    if (await save(m, { murpyUid: to, murpyNick: (byUid[to] || {}).nickname || "", murpyAuto: stamp() }, [m.murpyUid, to])) moved++;
  }
  // ⓪-2 메인 바로잡기 — 걸린 계정은 근방단 스쿼드 활동이 0인데 같은 사람 다른 계정이 활동 중이면 그쪽으로.
  //   본인이 직접 고른 짝(murpySelf)은 건드리지 않는다.
  for (const m of members) {
    if (!m.murpyUid || m.murpySelf || m.status === "removed") continue;
    if (((scan.act[m.murpyUid] || {}).sq || 0) > 0) continue;
    const p = L.pickMain(m, users, scan.alias, scan.act, owner(), m.murpyUid);
    if (!p || p.u.uid === m.murpyUid) continue;
    if (await save(m, { murpyUid: p.u.uid, murpyNick: p.u.nickname, murpyAuto: stamp() }, [m.murpyUid, p.u.uid])) moved++;
  }
  // ① 확실한 짝은 바로 등록(중복 계정이면 활동 많은 쪽이 메인, 나머지는 보조)
  for (const p of L.surePairs(members, users, scan.alias, scan.act, owner())) {
    const m = members.find((x) => x.name === p.name);
    if (await save(m, { murpyUid: p.u.uid, murpyNick: p.u.nickname, murpyNone: false, murpyAlts: p.alts, murpyAuto: stamp() }, [p.u.uid].concat(p.alts))) auto++;
  }
  // ①-2 보조 계정 정리 — 연결된 멤버마다 지금 메인 기준으로 다시 계산(짝이 풀린 멤버는 비움)
  for (const m of members) {
    let want = [];
    if (m.murpyUid && m.status !== "removed") {
      const t = owner(); [m.murpyUid].concat(m.murpyAlts || []).forEach((u) => { if (t[u] === m.name) delete t[u]; });
      want = users.filter((u) => !u.guest && u.uid !== m.murpyUid && !t[u.uid] && ((scan.act[u.uid] || {}).sq || 0) > 0
        && L.nameHit(m, u, scan.alias[u.uid]) && L.yearCmp(m, u, scan.alias[u.uid]) === "same").map((u) => u.uid);
    } else if (m.status === "removed") want = m.murpyAlts || [];   // 나간 사람은 그대로 둔다(지난 기록용)
    if (!sameList(want, m.murpyAlts)) { if (await save(m, { murpyAlts: want }, want.concat(m.murpyAlts || []))) alts++; }
  }

  // ② 물어볼 사람 갱신(바뀐 것만 쓴다)
  const taken = owner();
  const never = await neverAskUids();
  const linkedActive = members.filter((m) => m.murpyUid && m.status !== "removed");
  const cur = {};
  (await db.collection("gbdAsk").get()).forEach((d) => { cur[d.id] = d.data() || {}; });
  let asks = 0;
  let batch = db.batch(), nb = 0, nw = 0;
  const flush = async () => { if (nb) { await batch.commit(); batch = db.batch(); nb = 0; } };
  for (const u of users) {
    if (nb >= 400) await flush();
    const c = cur[u.uid];
    // 이미 연결된 근방단 멤버와 이름이 같고 생년이 안 부딪히면 = 그 사람의 중복 계정일 가능성 → 묻지 않는다
    const dupOfLinked = linkedActive.some((m) => L.nameHit(m, u, scan.alias[u.uid]) && L.yearCmp(m, u, scan.alias[u.uid]) !== "diff");
    const want = !u.guest && !taken[u.uid] && scan.inGbd.has(u.uid) && !dupOfLinked && !never.has(u.uid);
    if (want) {
      asks++;
      const guess = L.guessFor(u, members, scan.alias[u.uid]);
      if (!c || c.eligible !== true || (c.guess || "") !== guess) { batch.set(db.collection("gbdAsk").doc(u.uid), { eligible: true, guess, at: Date.now() }, { merge: true }); nb++; nw++; }
    } else if (c && c.eligible) { batch.set(db.collection("gbdAsk").doc(u.uid), { eligible: false, at: Date.now() }, { merge: true }); nb++; nw++; }
  }
  await flush();
  if (touched.length) await S.resyncUid(touched);
  return { moved, auto, alts, asks, writes: nw };
}

exports.gbdLinkHourly = onSchedule({ region: REGION, schedule: "every 60 minutes" }, async () => {
  const r = await linkRun();
  console.log("gbd link hourly", JSON.stringify(r));
});

const notAnon = (req) => !!(req.auth && req.auth.token && (req.auth.token.firebase || {}).sign_in_provider !== "anonymous");

// 앱이 켜질 때 — 물어볼 게 있으면 { ask: true, guess } (하루 한 번)
exports.gbdAsk = onCall({ region: REGION }, async (req) => {
  if (!notAnon(req)) return {};
  const ref = getFirestore().collection("gbdAsk").doc(req.auth.uid);
  const snap = await ref.get();
  const a = snap.exists ? snap.data() : null;
  if (!a || a.eligible !== true || a.no) return {};
  if ((Number(a.shownAt) || 0) > Date.now() - ASK_GAP) return {};
  await ref.set({ shownAt: Date.now() }, { merge: true });
  return { ask: true, guess: a.guess || "" };
});

// 답 — { no: true } = 근방단 아님(다시 안 묻는다) / { name } = 이 이름으로 연결
exports.gbdClaim = onCall({ region: REGION }, async (req) => {
  if (!notAnon(req)) throw new HttpsError("unauthenticated", "login");
  const uid = req.auth.uid;
  const db = getFirestore();
  const ref = db.collection("gbdAsk").doc(uid);
  const snap = await ref.get();
  const a = snap.exists ? snap.data() : null;
  if (!a || a.eligible !== true) throw new HttpsError("permission-denied", "not asked");
  const d = req.data || {};
  if (d.no === true) { await ref.set({ no: true }, { merge: true }); return { ok: true }; }

  const day = L.kstDate(Date.now());
  const tries = a.triesDay === day ? (Number(a.tries) || 0) : 0;
  if (tries >= MAX_TRIES) return { ok: false, reason: "limit" };
  const fail = async (reason) => { await ref.set({ triesDay: day, tries: tries + 1 }, { merge: true }); return { ok: false, reason }; };

  const name = L.nrm(d.name);
  if (!name || name.length > 20) return fail("not-found");
  const uSnap = await db.collection("users").doc(uid).get();
  const ud = uSnap.exists ? uSnap.data() : {};
  const u = { uid, nickname: ud.nickname || "", birth: ud.birth || "" };
  for (let i = 0; i < 3; i++) {
    const members = await S.gbdMembers();
    const mine = members.find((m) => m.murpyUid === uid || (m.murpyAlts || []).includes(uid));
    if (mine) { await ref.set({ eligible: false }, { merge: true }); return { ok: true, name: mine.name }; }
    const gm = members.find((m) => L.nrm(m.name) === name);
    const why = L.claimCheck(gm, u);
    if (why) return fail(why);
    try {
      await S.linkMember(gm, uid, u.nickname, "murpySelf");
    } catch (e) {
      if (e instanceof S.Conflict) continue;   // 그 사이 누가 고쳤다 — 다시 읽고 확인
      throw e;
    }
    await ref.set({ eligible: false, linkedName: gm.name }, { merge: true });
    try { await S.resyncUid([uid]); } catch (e) { console.warn("gbd claim resync", e.message); }
    console.log("gbd self link", uid, gm.name);
    return { ok: true, name: gm.name };
  }
  return { ok: false, reason: "retry" };
});

exports._linkRun = linkRun;   // 테스트용
