// ─────────────────────────────────────────────────────────────────────────────
// ★10-19 크루 기록 — 서버 함수(가입·탈퇴, 러닝 인증샷 판정, 체크인 → 크루 출석·성주, 챌린지).
//   설계 = docs/superpowers/specs/2026-10-19-crew-records-design.md · 숫자 계산 = crew_logic.js
//   ★크루 숫자(stats)·러닝 기록(runs)·개인 기록(runStats)은 **서버만** 쓴다(규칙이 클라이언트 쓰기를 막는다).
//   ★인증됨은 건강 앱 원본 대조로만 준다. 1차(웹)는 HEALTH_VERIFY_ON=false — 앱이 원본을 못 보내는 동안
//     클라이언트가 health 를 지어내 보내도 무시한다. 2차(아이폰 1.1.0)에서 켠다.
//   ★휴면 `crews` 컬렉션과는 별개다(새 컬렉션 crewsV2).
// ─────────────────────────────────────────────────────────────────────────────
const { onCall, HttpsError } = require("firebase-functions/v2/https");
const { onDocumentCreated } = require("firebase-functions/v2/firestore");
const { onSchedule } = require("firebase-functions/v2/scheduler");
const { defineSecret } = require("firebase-functions/params");
const { getFirestore, FieldValue } = require("firebase-admin/firestore");
const { getStorage } = require("firebase-admin/storage");
const crypto = require("crypto");
const L = require("./crew_logic.js");

const REGION = "asia-northeast3";
const GEMINI = defineSecret("GEMINI_API_KEY");
const BUCKET = "murpyprototype.firebasestorage.app";
const HEALTH_VERIFY_ON = false;          // 2차에서 true
// ★러닝 카드 올리기는 개인정보 처리방침 개정 시행(10-26) 뒤에 연다(대표 확정 (가)). index.html CREW_CFG.RUN_UPLOAD_ON 과 같이 바꿔 배포.
const RUN_UPLOAD_ON = false;
const OCR_MODEL = "gemini-3.5-flash-lite";   // 10-19 실측: 2.5-flash-lite 는 새 키에 404(단종). 카드 1장 ≈1,300토큰·2초
const TITLE_OF = { 100: "크루 100K", 500: "크루 500K", 1000: "크루 1000K" };

const db = () => getFirestore();
const now = () => Date.now();
function needUser(req) {
  const uid = req.auth && req.auth.uid;
  if (!uid) throw new HttpsError("unauthenticated", "login");
  const prov = req.auth.token && req.auth.token.firebase && req.auth.token.firebase.sign_in_provider;
  if (prov === "anonymous") throw new HttpsError("permission-denied", "member_only");   // 임시계정 = 스쿼드 전용
  return uid;
}

// ── 머피 지급 — functions earn 과 같은 장부 모양(키로 중복 차단) ──────────────
const ledgerRef = (uid, reason, key) => db().collection("ledger").doc(("l_" + uid + "_" + reason + "_" + key).replace(/[^\w-]/g, "_").slice(0, 900));
async function paidKey(uid, reason, key) { return (await ledgerRef(uid, reason, key).get()).exists; }
async function payMurpy(uid, amount, reason, key) {
  if (!(amount > 0)) return 0;
  const d = db();
  const day = L.kstDay(now()).replace(/^(\d{4})(\d{2})(\d{2})$/, "$1-$2-$3");
  const ref = ledgerRef(uid, reason, key);
  try {
    await d.runTransaction(async (tx) => {
      const uRef = d.collection("users").doc(uid);
      const u = await tx.get(uRef);
      const bal = (u.exists && typeof u.data().credits === "number") ? u.data().credits : 0;
      tx.update(uRef, { credits: bal + amount });
      tx.create(ref, { uid, reason, key, day, claimed: amount, allowed: amount, why: "", mode: "live", at: FieldValue.serverTimestamp() });
    });
    return amount;
  } catch (e) { return 0; }   // create 충돌 = 이미 준 키
}
async function paidToday(uid, reason) {
  const day = L.kstDay(now()).replace(/^(\d{4})(\d{2})(\d{2})$/, "$1-$2-$3");
  const q = await db().collection("ledger").where("uid", "==", uid).where("reason", "==", reason).where("day", "==", day).get();
  return q.size;
}

// ── 크루 한 곳에 사건 하나 반영(트랜잭션) ─────────────────────────────────────
//   fn(crewStats, member, crew) → { stats, member, verifiedKm?, attendCounted?, active? } 를 돌려준다.
//   챌린지 진행·마일스톤은 여기서 같이 처리하고, 끝난 뒤 할 일(지급·칭호)을 돌려준다.
async function bumpCrew(crewId, uid, atMs, fn) {
  const d = db();
  const cRef = d.collection("crewsV2").doc(crewId);
  const mRef = cRef.collection("members").doc(uid);
  const after = { applied: false, challengeDone: [], milestones: [] };
  await d.runTransaction(async (tx) => {
    const [c, m, chs] = await Promise.all([
      tx.get(cRef), tx.get(mRef),
      tx.get(cRef.collection("challenges").where("status", "==", "active").limit(5)),
    ]);
    if (!c.exists || !m.exists || m.data().left) return;
    const crew = c.data();
    const prevKm = (crew.stats && crew.stats.km) || 0;
    const r = fn(Object.assign({}, crew.stats || {}), Object.assign({}, m.data()), crew);
    if (!r) return;
    const stats = r.stats;
    const upd = { stats };
    if (r.step) {
      chs.forEach((s) => {
        const out = L.challengeStep(s.data(), Object.assign({ atMs }, r.step));
        if (out.ch.progress !== s.data().progress || out.justDone) {
          tx.update(s.ref, { progress: out.ch.progress, status: out.ch.status, doneAt: out.ch.doneAt || null });
          if (out.justDone) after.challengeDone.push(s.id);
        }
      });
    }
    const ms = L.newMilestones(prevKm, stats.km || 0, crew.milestones || []);
    if (ms.length) { upd.milestones = FieldValue.arrayUnion(...ms); after.milestones = ms; }
    tx.update(cRef, upd);
    tx.set(mRef, r.member, { merge: true });
    after.applied = true;
  });
  for (const chId of after.challengeDone) await finishChallenge(crewId, chId);
  if (after.milestones.length) await grantMilestones(crewId, after.milestones);
  return after;
}

async function activeMembers(crewId) {
  const q = await db().collection("crewsV2").doc(crewId).collection("members").where("left", "==", false).get();
  return q.docs.map((s) => s.id);
}
async function notify(toUid, n) {
  await db().collection("notifications").add(Object.assign({ toUid, fromUid: "murpy", fromNickname: "머피", read: false,
    createdAt: FieldValue.serverTimestamp() }, n));
}
// 달성 지급 — payMurpy 는 (사람, 챌린지) 키라 두 번 불려도 한 번만 준다. 그래서 **다 준 뒤에** rewardPaid 를 찍는다.
//   ★먼저 찍으면 중간에 끊겼을 때 남은 사람이 영영 못 받는다(리뷰 10-19). 못 끝낸 것은 crewHourly 가 다시 돈다.
//   알림은 그 사람에게 처음 지급됐을 때만(다시 돌 때 중복 알림 없게).
async function finishChallenge(crewId, chId) {
  const d = db();
  const cRef = d.collection("crewsV2").doc(crewId);
  const chRef = cRef.collection("challenges").doc(chId);
  const [ch, c] = await Promise.all([chRef.get(), cRef.get()]);
  if (!ch.exists || ch.data().rewardPaid || ch.data().status !== "done") return;
  const crewName = (c.data() || {}).name || "", owner = (c.data() || {}).createdBy || "";
  const uids = await activeMembers(crewId);
  let missed = 0;
  for (const uid of uids) {
    const r = await payMurpy(uid, L.CFG.CHALLENGE_REWARD, "crew_challenge", chId);
    if (r > 0) await notify(uid, { type: "crew_challenge_done", crewId, text: crewName, amount: L.CFG.CHALLENGE_REWARD });
    else if (!(await paidKey(uid, "crew_challenge", chId))) missed++;
  }
  if (missed) { console.warn(`crew challenge payout incomplete crew=${crewId} ch=${chId} missed=${missed} — crewHourly 가 다시 돈다`); return; }
  await chRef.update({ rewardPaid: true });
  if (owner) await notify(owner, { type: "crew_challenge_done", crewId, text: crewName, admin: true });
  console.log(`crew challenge done crew=${crewId} ch=${chId} members=${uids.length}`);
}
async function grantMilestones(crewId, ms) {
  const uids = await activeMembers(crewId);
  const titles = ms.map((m) => TITLE_OF[m]).filter(Boolean);
  if (!titles.length) return;
  const d = db();
  for (let i = 0; i < uids.length; i += 400) {
    const b = d.batch();
    uids.slice(i, i + 400).forEach((u) => b.set(d.collection("users").doc(u), { titles: FieldValue.arrayUnion(...titles) }, { merge: true }));
    await b.commit();
  }
  for (const uid of uids) await notify(uid, { type: "crew_milestone", crewId, text: titles[titles.length - 1] });
  console.log(`crew milestone crew=${crewId} ${ms.join(",")} members=${uids.length}`);
}

// ── 가입 · 탈퇴 ───────────────────────────────────────────────────────────────
exports.crewJoin = onCall({ region: REGION }, async (req) => {
  const uid = needUser(req);
  const crewId = String((req.data || {}).crewId || ""), code = String((req.data || {}).code || "");
  if (!crewId) throw new HttpsError("invalid-argument", "crewId");
  const d = db();
  const cRef = d.collection("crewsV2").doc(crewId);
  const join = await cRef.collection("private").doc("join").get();
  if (!join.exists || !code || join.data().code !== code) throw new HttpsError("permission-denied", "bad_code");
  let name = "";
  await d.runTransaction(async (tx) => {
    const uRef = d.collection("users").doc(uid), mRef = cRef.collection("members").doc(uid);
    const [c, m, u] = await Promise.all([tx.get(cRef), tx.get(mRef), tx.get(uRef)]);
    if (!c.exists) throw new HttpsError("not-found", "crew");
    name = c.data().name || "";
    const nick = (u.exists && u.data().nickname) || "";
    // crewIds 는 이미 멤버여도 다시 맞춘다 — users 문서가 덮어써져 배열이 비면 기록이 크루에 안 쌓인다(리뷰 10-19)
    if (u.exists) tx.update(uRef, { crewIds: FieldValue.arrayUnion(crewId) });
    if (m.exists && !m.data().left) return;
    if (m.exists) tx.update(mRef, { left: false, leftAt: null, nickname: nick });
    else tx.set(mRef, { uid, nickname: nick, joinedAt: now(), left: false });
    tx.update(cRef, { "stats.members": FieldValue.increment(1) });
  });
  return { ok: true, crew: { id: crewId, name } };
});

async function leaveCrew(uid, crewId, anonymize) {
  const d = db();
  const cRef = d.collection("crewsV2").doc(crewId);
  await d.runTransaction(async (tx) => {
    const mRef = cRef.collection("members").doc(uid), uRef = d.collection("users").doc(uid);
    const [m, u] = await Promise.all([tx.get(mRef), tx.get(uRef)]);
    if (m.exists && anonymize && m.data().left) tx.update(mRef, { nickname: "" });   // 이미 나간 크루에도 닉네임이 남아 있다
    if (m.exists && !m.data().left) {
      tx.update(mRef, Object.assign({ left: true, leftAt: now() }, anonymize ? { nickname: "" } : {}));
      tx.update(cRef, { "stats.members": FieldValue.increment(-1) });
    }
    if (u.exists) tx.update(uRef, { crewIds: FieldValue.arrayRemove(crewId) });
  });
}
exports.crewLeave = onCall({ region: REGION }, async (req) => {
  const uid = needUser(req);
  const crewId = String((req.data || {}).crewId || "");
  if (!crewId) throw new HttpsError("invalid-argument", "crewId");
  await leaveCrew(uid, crewId);
  return { ok: true };
});

// ── 러닝 인증샷 ───────────────────────────────────────────────────────────────
const OCR_SCHEMA = {
  type: "OBJECT",
  properties: {
    isRunCard: { type: "BOOLEAN" },
    app: { type: "STRING", enum: ["strava", "nrc", "unknown"] },
    km: { type: "NUMBER", nullable: true },
    sec: { type: "INTEGER", nullable: true },
    paceSec: { type: "INTEGER", nullable: true },
    dateISO: { type: "STRING", nullable: true },
  },
  required: ["isRunCard", "app"],
};
async function ocrCard(key, buf, mime) {
  const today = L.kstDay(now()).replace(/^(\d{4})(\d{2})(\d{2})$/, "$1-$2-$3");
  const prompt = [
    "This image should be a running activity share card or screenshot from Strava or Nike Run Club (Korean or English UI).",
    "Extract: isRunCard (true only if it shows a completed run with a distance), app (strava | nrc | unknown),",
    "km = total distance in kilometers (convert miles to km), sec = total (moving) time in seconds,",
    "paceSec = average pace in seconds per km (convert per-mile pace), dateISO = the run date as YYYY-MM-DD if shown.",
    `Today is ${today} (Korea). If a date has no year, use the most recent past date. Korean words like '오늘' mean today, '어제' yesterday.`,
    "Use null for anything not visible. Never guess numbers that are not printed on the image.",
  ].join(" ");
  const body = {
    contents: [{ parts: [{ inline_data: { mime_type: mime, data: buf.toString("base64") } }, { text: prompt }] }],
    generationConfig: { responseMimeType: "application/json", responseSchema: OCR_SCHEMA, temperature: 0, thinkingConfig: { thinkingLevel: "minimal" } },
  };
  const ac = new AbortController();
  const t = setTimeout(() => ac.abort(), 25000);
  try {
    const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${OCR_MODEL}:generateContent`, {
      method: "POST", headers: { "Content-Type": "application/json", "x-goog-api-key": key }, body: JSON.stringify(body), signal: ac.signal,
    });
    if (!r.ok) { console.warn("ocr http", r.status, (await r.text()).slice(0, 300)); return null; }
    const j = await r.json();
    const text = j && j.candidates && j.candidates[0] && j.candidates[0].content && j.candidates[0].content.parts
      && j.candidates[0].content.parts.map((p) => p.text || "").join("");
    return L.parseOcr(text || "");
  } catch (e) { console.warn("ocr fail", e && e.message); return null; } finally { clearTimeout(t); }
}

async function myCrewIds(uid) {
  const u = await db().collection("users").doc(uid).get();
  return ((u.exists && u.data().crewIds) || []).filter((x) => typeof x === "string" && x && !x.includes("/")).slice(0, 10);
}
// ★users.crewIds 는 본인이 직접 고칠 수 있다 — 기록을 붙일 크루는 members 문서(서버만 씀)로 다시 확인한다.
//   안 그러면 남의 크루 피드에 끼어들고, 지울 때 안 더한 숫자를 빼서 크루 숫자가 음수가 된다(리뷰 10-19).
async function myActiveCrewIds(uid) {
  const ids = await myCrewIds(uid);
  const snaps = await Promise.all(ids.map((id) => db().collection("crewsV2").doc(id).collection("members").doc(uid).get()));
  return ids.filter((id, i) => snaps[i].exists && !snaps[i].data().left);
}

// 개인 기록 + 소속 크루마다 반영. verified 면 챌린지·마일스톤·이번 주 참여까지.
async function applyRunEverywhere(uid, run, verified, atMs) {
  const d = db();
  await d.runTransaction(async (tx) => {
    const ref = d.collection("runStats").doc(uid);
    const s = await tx.get(ref);
    tx.set(ref, L.applyRun(s.exists ? s.data() : {}, run, { verified, personal: true }));
  });
  for (const crewId of run.crewIds || []) {
    await bumpCrew(crewId, uid, atMs, (stats, member) => {
      let st = L.applyRun(stats, run, { verified });
      const mem = L.applyRun(member, run, { verified });
      if (verified) st = L.crewWeekAdd(st, L.weekKey(run.runDay), L.weekActiveDelta(mem, L.weekKey(run.runDay)));
      return { stats: st, member: mem, step: { kind: "run_km", amount: run.km, verified } };
    });
  }
}

exports.runSubmit = onCall({ region: REGION, secrets: [GEMINI], timeoutSeconds: 60, memory: "512MiB" }, async (req) => {
  const uid = needUser(req);
  if (!RUN_UPLOAD_ON) return { ok: false, why: "not_yet" };
  const path = L.storagePathOf((req.data || {}).url, uid, BUCKET);
  // 앱이 올리는 카드 파일(uploads/{uid}/run_…)만 — 지울 때 프로필·피드 사진을 지우지 않게
  if (!path || !/^uploads\/[^/]+\/run_[^/]+$/.test(path)) throw new HttpsError("invalid-argument", "bad_url");
  const d = db();
  // 하루 30번까지(제미나이 호출 비용·장난 방지). 안 넘으면 그대로 진행.
  const qRef = d.collection("runQuota").doc(uid + "_" + L.kstDay(now()));
  const used = await d.runTransaction(async (tx) => {
    const q = await tx.get(qRef); const n = (q.exists && q.data().n) || 0;
    if (n < 30) tx.set(qRef, { n: n + 1, at: now() });
    return n;
  });
  if (used >= 30) return { ok: false, why: "too_many" };
  const file = getStorage().bucket(BUCKET).file(path);
  const reject = async (why) => { await file.delete().catch(() => {}); return { ok: false, why }; };
  const [meta] = await file.getMetadata();
  if (Number(meta.size) > 8 * 1024 * 1024) return reject("too_big");
  const [buf] = await file.download();
  const hash = crypto.createHash("sha256").update(buf).digest("hex");
  const runRef = d.collection("runs").doc("r_" + hash.slice(0, 32));   // 같은 카드 = 같은 문서 → 중복이 저절로 막힌다
  if ((await runRef.get()).exists) return reject("dup_image");

  const ocr = await ocrCard(GEMINI.value(), buf, meta.contentType || "image/jpeg");
  const chk = L.checkCard(ocr, { nowMs: now() });
  if (!chk.ok) return reject(chk.why);
  const run = chk.run;

  const recent = await d.collection("runs").where("uid", "==", uid).orderBy("createdAt", "desc").limit(30).get();
  if (L.isDupRun(run, recent.docs.map((s) => s.data()))) return reject("dup_run");

  let verified = false, source = null;
  const health = (req.data || {}).health;
  if (HEALTH_VERIFY_ON && Array.isArray(health)) {
    const m = L.matchHealth(run, health.slice(0, 30));
    if (m.ok) { verified = true; source = m.source; }
  }
  const crewIds = await myActiveCrewIds(uid);
  const doc = Object.assign({}, run, { uid, img: String(req.data.url), imgPath: path, imgHash: hash,
    status: verified ? "verified" : "unverified", source, crewIds, createdAt: now() });
  try { await runRef.create(doc); } catch (e) { return { ok: false, why: "dup_image" }; }
  await applyRunEverywhere(uid, doc, verified, L.runAtMs(run.runDay));   // 챌린지 기간은 '뛴 날' 기준(올린 시각 아님)

  let reward = 0;
  if (verified && (await paidToday(uid, "run_verified")) < L.CFG.RUN_REWARD_PER_DAY) {
    reward = await payMurpy(uid, L.CFG.RUN_REWARD, "run_verified", runRef.id);
  }
  console.log(`runSubmit uid=${uid} km=${run.km} sec=${run.sec} app=${run.app} status=${doc.status} crews=${crewIds.length}`);
  return { ok: true, reward, run: { id: runRef.id, km: run.km, sec: run.sec, paceSec: run.paceSec, runDay: run.runDay,
    dayFromCard: run.dayFromCard, app: run.app, status: doc.status } };
});

async function deleteRun(uid, snap) {
  const d = db();
  // ★트랜잭션 안에서 다시 읽는다 — 동시에 두 번 지우면 두 번 빼던 것을 막는다(리뷰 10-19)
  const r = await d.runTransaction(async (tx) => {
    const ref = d.collection("runStats").doc(uid);
    const [cur, s] = await Promise.all([tx.get(snap.ref), tx.get(ref)]);
    if (!cur.exists) return null;
    const x = cur.data();
    if (s.exists) tx.set(ref, L.revertRun(s.data(), x, { verified: x.status === "verified", personal: true }));
    tx.delete(snap.ref);
    return x;
  });
  if (!r) return;
  const verified = r.status === "verified";
  for (const crewId of r.crewIds || []) {
    const cRef = d.collection("crewsV2").doc(crewId), mRef = cRef.collection("members").doc(uid);
    await d.runTransaction(async (tx) => {
      const [c, m] = await Promise.all([tx.get(cRef), tx.get(mRef)]);
      if (c.exists) tx.update(cRef, { stats: L.revertRun(c.data().stats || {}, r, { verified }) });
      if (m.exists) tx.set(mRef, L.revertRun(m.data(), r, { verified }), { merge: true });
    });
  }
  if (r.imgPath && /^uploads\/[^/]+\/run_[^/]+$/.test(r.imgPath)) await getStorage().bucket(BUCKET).file(r.imgPath).delete().catch(() => {});
}
exports.runDelete = onCall({ region: REGION }, async (req) => {
  const uid = needUser(req);
  const snap = await db().collection("runs").doc(String((req.data || {}).runId || "")).get();
  if (!snap.exists || snap.data().uid !== uid) throw new HttpsError("permission-denied", "not_mine");
  await deleteRun(uid, snap);
  return { ok: true };
});
// 탈퇴할 때 앱(deleteMyAccount)이 부른다 — 내 러닝 기록·카드 이미지 삭제, 크루는 나간 것으로.
exports.runPurgeMine = onCall({ region: REGION, timeoutSeconds: 120 }, async (req) => {
  const uid = req.auth && req.auth.uid;
  if (!uid) throw new HttpsError("unauthenticated", "login");
  const d = db();
  const runs = await d.collection("runs").where("uid", "==", uid).get();
  for (const s of runs.docs) await deleteRun(uid, s);
  await d.collection("runStats").doc(uid).delete().catch(() => {});
  // 지금 소속 + 예전에 나간 크루까지 — members 문서의 닉네임을 지운다(공개 읽기라서)
  const all = await d.collectionGroup("members").where("uid", "==", uid).get().catch(() => null);
  const ids = new Set(await myCrewIds(uid));
  if (all) all.docs.forEach((m) => { const c = m.ref.parent.parent; if (c && c.parent.id === "crewsV2") ids.add(c.id); });
  for (const crewId of ids) await leaveCrew(uid, crewId, true);
  return { ok: true, runs: runs.size };
});

// ── 체크인 → 크루 출석 · 헬스장 성주 ─────────────────────────────────────────
exports.crewCheckin = onDocumentCreated({ region: REGION, document: "checkins/{id}" }, async (event) => {
  const c = event.data && event.data.data();
  if (!c || !c.uid || !c.day) return;
  const created = (event.data.createTime && event.data.createTime.toMillis) ? event.data.createTime.toMillis() : Date.parse(event.time);
  const okDay = L.checkinDay(event.params.id, c, created);
  if (!okDay) { console.warn(`crewCheckin skip id=${event.params.id} day=${c.day}`); return; }
  const d = db();
  // 트리거는 드물게 두 번 올 수 있다 — 사건 id 로 한 번만
  try { await d.collection("crewEvents").doc(String(event.id)).create({ at: now(), kind: "checkin" }); } catch (e) { return; }
  const day = okDay, wk = L.weekKey(day), atMs = created;
  for (const crewId of await myCrewIds(c.uid)) {
    await bumpCrew(crewId, c.uid, atMs, (stats, member) => {
      const a = L.applyAttend(member, day);
      if (!a.counted) return null;
      let st = L.addAttend(stats, day, 1);
      st = L.crewWeekAdd(st, wk, L.weekActiveDelta(a.member, wk));
      return { stats: st, member: a.member, step: { kind: "gym_attend", amount: 1, verified: true } };
    });
  }
  if (c.centerId) {
    const ref = d.collection("centerMonth").doc(String(c.centerId) + "_" + L.monthKey(day));
    await d.runTransaction(async (tx) => {
      const s = await tx.get(ref);
      const v = s.exists ? s.data() : { counts: {}, top: null };
      const counts = Object.assign({}, v.counts);
      counts[c.uid] = (counts[c.uid] || 0) + 1;
      let top = v.top;
      if (!top || counts[c.uid] > top.n || top.uid === c.uid) top = { uid: c.uid, n: counts[c.uid] };
      tx.set(ref, { centerId: String(c.centerId), monthKey: L.monthKey(day), counts, top });
    });
  }
});

// ── 기간이 끝난 챌린지 정리 ───────────────────────────────────────────────────
exports.crewHourly = onSchedule({ region: REGION, schedule: "every 60 minutes" }, async () => {
  const d = db();
  const crews = await d.collection("crewsV2").get();
  let n = 0;
  for (const c of crews.docs) {
    const chs = await c.ref.collection("challenges").where("status", "==", "active").get();
    for (const s of chs.docs) {
      if (now() < s.data().end) continue;
      const failed = await d.runTransaction(async (tx) => {   // 막 달성된 것을 실패로 덮지 않게 다시 확인
        const cur = await tx.get(s.ref);
        if (!cur.exists || cur.data().status !== "active") return false;
        tx.update(s.ref, { status: "failed" }); return true;
      });
      if (failed) n++;
    }
    // 달성했는데 지급을 다 못 끝낸 것(중간에 끊김) — 다시 돈다. 같은 사람에게 두 번 주지 않는다(장부 키).
    //   (rewardPaid 는 만들 때 없는 필드라 == false 로는 못 찾는다 → done 을 읽고 걸러낸다)
    const done = await c.ref.collection("challenges").where("status", "==", "done").get().catch(() => null);
    if (done) for (const s of done.docs) if (!s.data().rewardPaid) await finishChallenge(c.id, s.id);
  }
  if (n) console.log(`crewHourly failed=${n}`);
});

