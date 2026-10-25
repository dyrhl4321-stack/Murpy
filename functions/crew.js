// ─────────────────────────────────────────────────────────────────────────────
// ★10-19 크루 기록 — 서버 함수(가입·탈퇴, 러닝 인증샷 판정, 체크인 → 크루 출석·성주, 챌린지).
//   설계 = docs/superpowers/specs/2026-10-19-crew-records-design.md · 숫자 계산 = crew_logic.js
//   ★크루 숫자(stats)·러닝 기록(runs)·개인 기록(runStats)은 **서버만** 쓴다(규칙이 클라이언트 쓰기를 막는다).
//   ★판정 3단계(10-22 대표): 'scan' 스캔 인증(카드 스캔 + 거르기 통과) · 'verified' 원본 확인(건강 앱 대조, 아이폰 1.1.0 뒤)
//     · 'unverified' 미인증(거르기에 걸림 → 개인 기록만). 크루 누적·챌린지·칭호·인증 보상 = scan·verified(L.counts).
//     1차(웹)는 HEALTH_VERIFY_ON=false — 앱이 원본을 못 보내는 동안 클라이언트가 health 를 지어내 보내도 무시한다.
//   ★휴면 `crews` 컬렉션과는 별개다(새 컬렉션 crewsV2).
// ─────────────────────────────────────────────────────────────────────────────
const { onCall, HttpsError } = require("firebase-functions/v2/https");
const { onDocumentCreated, onDocumentWritten } = require("firebase-functions/v2/firestore");
const { getDatabase } = require("firebase-admin/database");
const { onSchedule } = require("firebase-functions/v2/scheduler");
const { defineSecret } = require("firebase-functions/params");
const { getFirestore, FieldValue } = require("firebase-admin/firestore");
const { getStorage } = require("firebase-admin/storage");
const { getAuth } = require("firebase-admin/auth");
const crypto = require("crypto");
const L = require("./crew_logic.js");

const REGION = "asia-northeast3";
const GEMINI = defineSecret("GEMINI_API_KEY");
const BUCKET = "murpyprototype.firebasestorage.app";
const HEALTH_VERIFY_ON = false;          // 2차에서 true
// ★러닝 카드 올리기는 개인정보 처리방침 개정 시행(10-26) 뒤에 연다(대표 확정 (가)). index.html CREW_CFG.RUN_UPLOAD_ON 과 같이 바꿔 배포.
const RUN_UPLOAD_ON = true;   // ★10-26 0시 처리방침 1.1 시행 → 대표 지시로 켬(웹 CREW_CFG.RUN_UPLOAD_ON 과 같이)
const OCR_MODEL = "gemini-3.5-flash-lite";   // 10-19 실측: 2.5-flash-lite 는 새 키에 404(단종). 카드 1장 ≈1,300토큰·2초
const TITLE_OF = { 100: "크루 100K", 500: "크루 500K", 1000: "크루 1000K" };

const ADMIN_EMAILS = ["dyrhl4321@gmail.com"];   // index.js MURPY_ADMIN_EMAILS 와 같게
const isAdminReq = (req) => !!(req.auth && req.auth.token && req.auth.token.email_verified !== false && ADMIN_EMAILS.includes(String(req.auth.token.email || "")));
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
      tx.get(cRef.collection("challenges").where("status", "in", ["active", "done"]).limit(10)),
    ]);
    if (!c.exists || !m.exists || m.data().left) return;
    const crew = c.data();
    const prevKm = (crew.stats && crew.stats.km) || 0;
    const r = fn(Object.assign({}, crew.stats || {}), Object.assign({}, m.data()), crew);
    if (!r) return;
    const stats = r.stats;
    const upd = { stats };
    let member = r.member;
    if (r.step) {
      chs.forEach((s) => {
        const ch = Object.assign({ id: s.id }, s.data());
        // 크루 합산은 진행 중(active)일 때만, 개인 진행·활동 표시는 기간 안이면 달성 뒤에도(보상 정산용)
        member = L.memberChallengeStep(member, ch, Object.assign({ atMs }, r.step));
        const out = L.challengeStep(s.data(), Object.assign({ atMs }, r.step));
        if (out.ch.progress !== s.data().progress || out.justDone) {
          tx.update(s.ref, { progress: out.ch.progress, status: out.ch.status, doneAt: out.ch.doneAt || null });
          if (out.justDone) after.challengeDone.push(s.id);
        }
      });
    }
    // ★10-22 대표: 트랙에서 묶인 자리엔 '가장 최근에 인증한 사람'을 보여 준다 — 크루에 들어간 기록(인증 러닝·출석)의 마지막 시각
    if (r.step && r.step.verified) member = Object.assign({}, member, { lastCountAt: now() });
    const ms = L.newMilestones(prevKm, stats.km || 0, crew.milestones || []);
    if (ms.length) { upd.milestones = FieldValue.arrayUnion(...ms); after.milestones = ms; }
    tx.update(cRef, upd);
    tx.set(mRef, member, { merge: true });
    after.applied = true;
  });
  if (after.challengeDone.length) console.log(`crew challenge target reached crew=${crewId} ch=${after.challengeDone.join(",")} — 보상은 기간이 끝난 뒤 crewHourly 가 정산`);
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
// 챌린지 보상 정산(대표 10-19) — 기간이 끝난 뒤 한 번: 함께 달성 GROUP(목표를 채웠을 때, 기간 중 운동한 사람) + 내 목표 SOLO(채운 사람, 크루가 실패해도).
//   payMurpy 는 (사람, 키) 장부라 다시 돌아도 한 번만 준다 → **다 준 뒤에** rewardPaid. 끊기면 crewHourly 가 이어서.
//   알림은 그 사람에게 이번에 처음 준 금액이 있을 때만(다시 돌 때 중복 알림 없게).
async function finishChallenge(crewId, chId) {
  const d = db();
  const cRef = d.collection("crewsV2").doc(crewId);
  const chRef = cRef.collection("challenges").doc(chId);
  const [chs, c] = await Promise.all([chRef.get(), cRef.get()]);
  if (!chs.exists) return;
  const ch = Object.assign({ id: chId }, chs.data());
  if (ch.rewardPaid || !(ch.status === "done" || ch.status === "failed") || now() < ch.end) return;
  const crewName = (c.data() || {}).name || "", owner = (c.data() || {}).createdBy || "";
  const mq = await cRef.collection("members").where("left", "==", false).get();
  const pays = L.settleChallenge(ch, mq.docs.map((s) => Object.assign({ uid: s.id }, s.data())));
  const got = {};
  let missed = 0;
  for (const p of pays) {
    const r = await payMurpy(p.uid, p.amount, "crew_challenge", p.key);
    if (r > 0) got[p.uid] = (got[p.uid] || 0) + r;
    else if (!(await paidKey(p.uid, "crew_challenge", p.key))) missed++;
  }
  for (const uid in got) await notify(uid, { type: "crew_challenge_done", crewId, text: crewName, amount: got[uid], solo: ch.status !== "done" });
  if (missed) { console.warn(`crew challenge payout incomplete crew=${crewId} ch=${chId} missed=${missed} — crewHourly 가 다시 돈다`); return; }
  await chRef.update({ rewardPaid: true });
  if (owner && ch.status === "done") await notify(owner, { type: "crew_challenge_done", crewId, text: crewName, admin: true });
  console.log(`crew challenge settled crew=${crewId} ch=${chId} status=${ch.status} pays=${pays.length}`);
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
  const [join, crew0] = await Promise.all([cRef.collection("private").doc("join").get(), cRef.get()]);
  if (!L.joinAllowed(join.exists ? join.data() : null, crew0.exists ? crew0.data() : null, code)) throw new HttpsError("permission-denied", "bad_code");
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
    // 스캔 연출용 — 카드 위 숫자 자리 [ymin,xmin,ymax,xmax] 0~1000 (판정에는 안 쓴다)
    boxes: { type: "OBJECT", nullable: true, properties: {
      km: { type: "ARRAY", nullable: true, items: { type: "INTEGER" } },
      pace: { type: "ARRAY", nullable: true, items: { type: "INTEGER" } },
      date: { type: "ARRAY", nullable: true, items: { type: "INTEGER" } },
      time: { type: "ARRAY", nullable: true, items: { type: "INTEGER" } },
    } },
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
    "Also return boxes: tight bounding boxes [ymin, xmin, ymax, xmax] on a 0-1000 scale around the printed distance value, the pace value, the total time value and the date text (null for any that is not visible).",
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
      const mem = L.markActive(L.applyRun(member, run, { verified }), run.runDay);   // 챌린지 목표 인원(최근 2주 운동) 판정용
      if (verified) {
        const wk = L.weekKey(run.runDay);
        st = L.crewWeekSum(st, wk, { km: run.km });   // ★주간 합계가 먼저(주가 바뀌면 weekActive 도 0부터)
        st = L.crewWeekAdd(st, wk, L.weekActiveDelta(mem, wk));
      }
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
  const shotMs = Number((req.data || {}).shotMs) || 0;    // 카드에 날짜가 없을 때만 쓴다(당일 판정)
  const chk = L.checkCard(ocr, { nowMs: now(), shotMs, soft: true });
  if (!chk.ok) return reject(chk.why);
  const run = chk.run;

  const recent = (await d.collection("runs").where("uid", "==", uid).orderBy("createdAt", "desc").limit(30).get()).docs.map((s) => s.data());
  if (L.isDupRun(run, recent)) return reject("dup_run");

  // 같은 날 이미 크루에 들어간 내 기록(하루 2건·60km 상한)
  const sameDay = recent.filter((x) => x.runDay === run.runDay && L.counts(x.status));
  const grade = L.runGrade(run, chk.flags, { todayRuns: sameDay.length, todayKm: sameDay.reduce((a, x) => a + (x.km || 0), 0) });
  let status = grade.status, source = null;
  const health = (req.data || {}).health;
  if (HEALTH_VERIFY_ON && status === "scan" && Array.isArray(health)) {
    const m = L.matchHealth(run, health.slice(0, 30));
    if (m.ok) { status = "verified"; source = m.source; }
  }
  const counted = L.counts(status);
  const crewIds = await myActiveCrewIds(uid);
  const doc = Object.assign({}, run, { uid, img: String(req.data.url), imgPath: path, imgHash: hash,
    status, why: grade.why, source, crewIds, excluded: [], createdAt: now() });
  try { await runRef.create(doc); } catch (e) { return { ok: false, why: "dup_image" }; }
  await applyRunEverywhere(uid, doc, counted, L.runAtMs(run.runDay));   // 챌린지 기간은 '뛴 날' 기준(올린 시각 아님)

  let reward = 0;
  if (counted && (await paidToday(uid, "run_verified")) < L.CFG.RUN_REWARD_PER_DAY) {
    reward = await payMurpy(uid, L.CFG.RUN_REWARD, "run_verified", runRef.id);
  }
  console.log(`runSubmit uid=${uid} km=${run.km} sec=${run.sec} app=${run.app} status=${doc.status} crews=${crewIds.length}`);
  return { ok: true, reward, run: { id: runRef.id, km: run.km, sec: run.sec, paceSec: run.paceSec, runDay: run.runDay,
    dayFromCard: run.dayFromCard, app: run.app, status: doc.status, why: grade.why, boxes: (ocr && ocr.boxes) || null } };
});

async function deleteRun(uid, snap) {
  const d = db();
  // ★트랜잭션 안에서 다시 읽는다 — 동시에 두 번 지우면 두 번 빼던 것을 막는다(리뷰 10-19)
  const r = await d.runTransaction(async (tx) => {
    const ref = d.collection("runStats").doc(uid);
    const [cur, s] = await Promise.all([tx.get(snap.ref), tx.get(ref)]);
    if (!cur.exists) return null;
    const x = cur.data();
    if (s.exists) tx.set(ref, L.revertRun(s.data(), x, { verified: L.counts(x.status), personal: true }));
    tx.delete(snap.ref);
    return x;
  });
  if (!r) return;
  const verified = L.counts(r.status);
  for (const crewId of (r.crewIds || []).filter((c) => !(r.excluded || []).includes(c))) {   // 이미 뺀 크루는 다시 빼지 않는다
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
// ── 크루 신고 · 제외 · 운영진(★10-22 대표) ──────────────────────────────────────
//   신고 = 같은 크루의 크루원이 남의 기록을 신고 → 크루장·운영진에게 알림(crewsV2/{c}/reports, 서버만 씀).
//   제외 = 크루장·운영진·관리자가 그 기록을 이 크루 합계·챌린지·이번 주 합계에서 뺀다. 개인 기록(runStats)은 그대로 둔다.
//   운영진 = crewsV2.staff[], 임명·해제는 크루장(또는 관리자)만.
const STAFF_MAX = 10, STAFF_CAN_EXCLUDE = false;
async function crewOf(crewId) {
  const c = await db().collection("crewsV2").doc(crewId).get();
  if (!c.exists) throw new HttpsError("not-found", "crew");
  return c.data();
}
exports.runReport = onCall({ region: REGION }, async (req) => {
  const uid = needUser(req);
  const runId = String((req.data || {}).runId || ""), crewId = String((req.data || {}).crewId || "");
  const why = String((req.data || {}).why || "").replace(/\s+/g, " ").trim().slice(0, 60);
  if (!runId || !crewId || crewId.includes("/") || runId.includes("/")) throw new HttpsError("invalid-argument", "args");
  const d = db();
  const cRef = d.collection("crewsV2").doc(crewId);
  const [r, me, crew] = await Promise.all([d.collection("runs").doc(runId).get(), cRef.collection("members").doc(uid).get(), crewOf(crewId)]);
  if (!r.exists || !(r.data().crewIds || []).includes(crewId)) throw new HttpsError("not-found", "run");
  if (!me.exists || me.data().left) throw new HttpsError("permission-denied", "not_member");
  if (r.data().uid === uid) throw new HttpsError("failed-precondition", "own_run");
  const ref = cRef.collection("reports").doc(runId + "_" + uid);   // 한 사람이 같은 기록을 두 번 신고하지 못하게
  try {
    await ref.create({ runId, crewId, by: uid, byNick: me.data().nickname || "", runUid: r.data().uid, km: r.data().km || 0,
      runDay: r.data().runDay || "", why, status: "open", at: now() });
  } catch (e) { return { ok: true, again: true }; }
  const to = new Set([L.leaderOf(crew)].concat(crew.staff || []).filter(Boolean));
  for (const t of to) await notify(t, { type: "crew_run_report", crewId, text: crew.name || "", runId });
  console.log(`runReport crew=${crewId} run=${runId} by=${uid} to=${to.size}`);
  return { ok: true };
});
exports.runExclude = onCall({ region: REGION }, async (req) => {
  const uid = needUser(req);
  const runId = String((req.data || {}).runId || ""), crewId = String((req.data || {}).crewId || "");
  if (!runId || !crewId || crewId.includes("/") || runId.includes("/")) throw new HttpsError("invalid-argument", "args");
  const crew = await crewOf(crewId);
  // ★10-22 대표: 10-26 오픈 땐 제외는 크루장·관리자만(운영진은 신고 알림만 받는다). 운영진에게 열 땐 STAFF_CAN_EXCLUDE 만 true.
  const okMod = STAFF_CAN_EXCLUDE ? L.canModerate(crew, uid) : L.leaderOf(crew) === uid;
  if (!(isAdminReq(req) || okMod)) throw new HttpsError("permission-denied", "not_leader");
  const d = db();
  const cRef = d.collection("crewsV2").doc(crewId), runRef = d.collection("runs").doc(runId);
  const res = await d.runTransaction(async (tx) => {
    const r0 = await tx.get(runRef);
    if (!r0.exists) return "gone";
    const r = r0.data();
    if (!(r.crewIds || []).includes(crewId)) return "not_in_crew";
    if ((r.excluded || []).includes(crewId)) return "already";
    const mRef = cRef.collection("members").doc(r.uid);
    const [c, m, chs] = await Promise.all([tx.get(cRef), tx.get(mRef),
      tx.get(cRef.collection("challenges").where("status", "in", ["active", "done"]).limit(10))]);
    const counted = L.counts(r.status), atMs = L.runAtMs(r.runDay);
    const step = { kind: "run_km", amount: r.km, atMs, verified: counted };
    let stats = L.revertRun((c.exists && c.data().stats) || {}, r, { verified: counted });
    if (counted) stats = L.crewWeekSum(stats, L.weekKey(r.runDay), { km: -r.km });
    let member = m.exists ? L.revertRun(m.data(), r, { verified: counted }) : null;
    chs.forEach((s) => {
      const ch = Object.assign({ id: s.id }, s.data());
      const out = L.challengeUnstep(s.data(), step);
      if (out.progress !== s.data().progress) tx.update(s.ref, { progress: out.progress, status: out.status, doneAt: out.doneAt || null });
      if (member) member = L.memberChallengeUnstep(member, ch, step);
    });
    if (c.exists) tx.update(cRef, { stats });
    if (member) tx.set(mRef, member, { merge: true });
    tx.update(runRef, { excluded: FieldValue.arrayUnion(crewId), excludedBy: FieldValue.arrayUnion(uid) });
    return "ok";
  });
  if (res === "gone" || res === "not_in_crew") throw new HttpsError("not-found", "run");
  // 이 기록에 걸린 신고는 처리됨으로
  const reps = await cRef.collection("reports").where("runId", "==", runId).get().catch(() => null);
  if (reps) for (const s of reps.docs) await s.ref.update({ status: "excluded", doneBy: uid, doneAt: now() }).catch(() => {});
  console.log(`runExclude crew=${crewId} run=${runId} by=${uid} res=${res}`);
  return { ok: true, already: res === "already" };
});
exports.crewSetStaff = onCall({ region: REGION }, async (req) => {
  const uid = needUser(req);
  const crewId = String((req.data || {}).crewId || ""), who = String((req.data || {}).uid || ""), on = (req.data || {}).on === true;
  if (!crewId || !who || crewId.includes("/") || who.includes("/")) throw new HttpsError("invalid-argument", "args");
  const d = db();
  const cRef = d.collection("crewsV2").doc(crewId);
  const crew = await crewOf(crewId);
  if (!(isAdminReq(req) || L.leaderOf(crew) === uid)) throw new HttpsError("permission-denied", "not_leader");
  if (who === L.leaderOf(crew)) throw new HttpsError("failed-precondition", "leader");
  const m = await cRef.collection("members").doc(who).get();
  if (on && (!m.exists || m.data().left)) throw new HttpsError("failed-precondition", "not_member");
  const staff = (crew.staff || []).filter((x) => x !== who);
  if (on) { if (staff.length >= STAFF_MAX) throw new HttpsError("resource-exhausted", "staff_max"); staff.push(who); }
  await cRef.update({ staff });
  await notify(who, { type: "crew_staff", crewId, text: crew.name || "", amount: on ? 1 : 0 });
  console.log(`crewSetStaff crew=${crewId} who=${who} on=${on} by=${uid}`);
  return { ok: true, staff };
});

// ── 크루 만들기 · 승인 · 닫기 · 시험 크루(★10-22 대표) ───────────────────────────
//   누구나 만들면 status:'pending'(만든 사람에게만 보임, 초대 코드 없음 = 가입 불가) → 관리자 crewReview 승인 때
//   만든 사람이 크루장·첫 크루원이 되고 초대 코드가 생긴다. 닫기 = 크루장 신청(closeReq) → 관리자 승인(status:'closed',
//   초대 코드 삭제, 기록은 남김). 상태는 서버만 바꾼다(규칙: crewsV2 쓰기는 관리자만).
const CODE_CHARS = "abcdefghjkmnpqrstuvwxyz23456789";
const newJoinCode = () => Array.from(crypto.randomBytes(10), (x) => CODE_CHARS[x % CODE_CHARS.length]).join("");
async function adminUids() {
  const out = [];
  for (const e of ADMIN_EMAILS) { try { out.push((await getAuth().getUserByEmail(e)).uid); } catch (x) { /* 없는 계정 */ } }
  return out;
}
// 로고에 얼굴·부적절한 그림이 있는지 Gemini 가 표시만 한다(반려는 관리자가 직접). 실패하면 null(관리자가 눈으로 본다).
async function logoCheck(key, url, uid) {
  const path = L.storagePathOf(url, uid, BUCKET);
  if (!path) return null;
  try {
    const file = getStorage().bucket(BUCKET).file(path);
    const [meta] = await file.getMetadata();
    if (Number(meta.size) > 8 * 1024 * 1024) return { tooBig: true };
    const [buf] = await file.download();
    const body = {
      contents: [{ parts: [{ inline_data: { mime_type: meta.contentType || "image/jpeg", data: buf.toString("base64") } },
        { text: "This image is a club logo uploaded to a fitness app. Answer face: true if a real human face or recognizable person photo is visible; unsafe: true if it contains nudity, violence, hate symbols or profanity. Otherwise false." }] }],
      generationConfig: { responseMimeType: "application/json", temperature: 0, thinkingConfig: { thinkingLevel: "minimal" },
        responseSchema: { type: "OBJECT", properties: { face: { type: "BOOLEAN" }, unsafe: { type: "BOOLEAN" } }, required: ["face", "unsafe"] } },
    };
    const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${OCR_MODEL}:generateContent`, {
      method: "POST", headers: { "Content-Type": "application/json", "x-goog-api-key": key }, body: JSON.stringify(body) });
    if (!r.ok) return null;
    const j = await r.json();
    const t = j && j.candidates && j.candidates[0] && j.candidates[0].content && j.candidates[0].content.parts.map((x) => x.text || "").join("");
    const o = JSON.parse(t || "{}");
    return { face: o.face === true, unsafe: o.unsafe === true };
  } catch (e) { console.warn("logoCheck", e && e.message); return null; }
}
exports.crewCreate = onCall({ region: REGION, secrets: [GEMINI], timeoutSeconds: 60 }, async (req) => {
  const uid = needUser(req);
  const d0 = req.data || {};
  const sport = ["running", "gym", "mixed"].includes(d0.sport) ? d0.sport : "running";
  const d = db();
  const all = (await d.collection("crewsV2").select("name", "createdBy", "leaderUid", "status").get()).docs.map((x) => x.data());
  const nm = L.crewNameCheck(d0.name, all.filter((c) => c.status !== "rejected").map((c) => c.name));
  if (!nm.ok) return { ok: false, why: "name_" + nm.why };
  const allowed = L.createAllowed(all.filter((c) => (c.leaderUid || c.createdBy) === uid));
  if (!allowed.ok) return { ok: false, why: allowed.why };
  const logo = d0.logo ? String(d0.logo) : "";
  if (logo && !L.storagePathOf(logo, uid, BUCKET)) throw new HttpsError("invalid-argument", "bad_logo");
  const lc = logo ? await logoCheck(GEMINI.value(), logo, uid) : null;
  const ref = d.collection("crewsV2").doc();
  await ref.set({ name: nm.name, school: String(d0.school || "").trim().slice(0, 30), sport, intro: String(d0.intro || "").trim().slice(0, 120),
    logo, logoCheck: lc, status: "pending", createdBy: uid, leaderUid: uid, staff: [], createdAt: now(), stats: { members: 0 } });
  for (const a of await adminUids()) await notify(a, { type: "crew_review_req", crewId: ref.id, text: nm.name, admin: true });
  console.log(`crewCreate ${ref.id} by=${uid} name=${nm.name} logoCheck=${JSON.stringify(lc)}`);
  return { ok: true, id: ref.id };
});
exports.crewReview = onCall({ region: REGION }, async (req) => {
  needUser(req);
  if (!isAdminReq(req)) throw new HttpsError("permission-denied", "admin_only");
  const { crewId, kind, ok, reason } = req.data || {};
  if (!crewId || String(crewId).includes("/")) throw new HttpsError("invalid-argument", "crewId");
  const d = db(), cRef = d.collection("crewsV2").doc(String(crewId));
  let crew = null, patch = null;
  await d.runTransaction(async (tx) => {
    const c = await tx.get(cRef);
    if (!c.exists) throw new HttpsError("not-found", "crew");
    crew = c.data();
    const r = L.reviewPatch(crew, { kind, ok: ok === true, reason, now: now() });
    if (r.err) throw new HttpsError("failed-precondition", r.err);
    patch = r.patch;
    const leader = L.leaderOf(crew), joinNow = kind === "create" && ok === true && !!leader;
    const uRef = joinNow ? d.collection("users").doc(leader) : null;
    const u = joinNow ? await tx.get(uRef) : null;   // ★트랜잭션은 읽기를 쓰기보다 먼저
    tx.update(cRef, patch);
    if (joinNow) {   // 만든 사람 = 크루장·첫 크루원, 초대 코드 생성
      const mRef = cRef.collection("members").doc(leader);
      tx.set(mRef, { uid: leader, nickname: (u.exists && u.data().nickname) || "", joinedAt: now(), left: false });
      tx.update(cRef, { "stats.members": FieldValue.increment(1) });
      if (u.exists) tx.update(uRef, { crewIds: FieldValue.arrayUnion(String(crewId)) });
      tx.set(cRef.collection("private").doc("join"), { code: newJoinCode() });
    }
    if (kind === "close" && ok === true) tx.delete(cRef.collection("private").doc("join"));   // 닫힌 크루는 새로 못 들어온다
  });
  const leader = L.leaderOf(crew);
  if (leader) await notify(leader, { type: "crew_reviewed", crewId: String(crewId), text: crew.name || "", kind, ok: ok === true,
    reason: String(reason || "").slice(0, 60) });
  console.log(`crewReview ${crewId} kind=${kind} ok=${ok === true}`);
  return { ok: true, status: (patch && patch.status) || crew.status || "approved" };
});
exports.crewCloseRequest = onCall({ region: REGION }, async (req) => {
  const uid = needUser(req);
  const crewId = String((req.data || {}).crewId || ""), reason = String((req.data || {}).reason || "").replace(/\s+/g, " ").trim().slice(0, 60);
  if (!crewId || crewId.includes("/")) throw new HttpsError("invalid-argument", "crewId");
  const cRef = db().collection("crewsV2").doc(crewId);
  const crew = await crewOf(crewId);
  if (L.leaderOf(crew) !== uid) throw new HttpsError("permission-denied", "not_leader");
  if ((crew.status || "approved") !== "approved") throw new HttpsError("failed-precondition", "not_open");
  await cRef.update({ closeReq: { by: uid, at: now(), reason } });
  for (const a of await adminUids()) await notify(a, { type: "crew_review_req", crewId, text: crew.name || "", close: true, admin: true });
  return { ok: true };
});
exports.crewSetTest = onCall({ region: REGION }, async (req) => {
  needUser(req);
  if (!isAdminReq(req)) throw new HttpsError("permission-denied", "admin_only");
  const crewId = String((req.data || {}).crewId || "");
  if (!crewId || crewId.includes("/")) throw new HttpsError("invalid-argument", "crewId");
  await db().collection("crewsV2").doc(crewId).update({ test: (req.data || {}).on === true });
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
      st = L.crewWeekSum(st, wk, { attends: 1 });
      st = L.crewWeekAdd(st, wk, L.weekActiveDelta(a.member, wk));
      return { stats: st, member: L.markActive(a.member, day), step: { kind: "gym_attend", amount: 1, verified: true } };
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

// ── 크루 아지트(★10-22) — RTDB crewLive/{crewId} 는 크루원만 읽고 쓴다(규칙이 _m/{uid} 거울을 본다) ──
//   거울은 서버만 쓴다: 크루원 문서(members/{uid})가 바뀔 때마다 left 를 따라 넣고 뺀다.
//   crewJoin 은 openJoin 대표 결정 전이라 배포가 묶여 있어, 가입 함수 대신 문서 트리거로 한다.
const CHAT_KEEP_DAYS = 14, CHAT_KEEP_N = 200;
exports.crewMemberMirror = onDocumentWritten({ region: REGION, document: "crewsV2/{crewId}/members/{uid}" }, async (event) => {
  const { crewId, uid } = event.params;
  const after = event.data && event.data.after && event.data.after.exists ? event.data.after.data() : null;
  const ref = getDatabase().ref("crewLive/" + crewId + "/_m/" + uid);
  if (after && !after.left) await ref.set(true); else await ref.remove();
});
// 처음 한 번(또는 거울이 비었을 때) 기존 크루원을 채운다 — crewHourly 가 크루마다 _mv 표시를 보고 부른다
async function mirrorBackfill(crewId) {
  const rt = getDatabase();
  const ms = await db().collection("crewsV2").doc(crewId).collection("members").where("left", "==", false).get();
  const m = {}; ms.docs.forEach((s) => { m[s.id] = true; });
  await rt.ref("crewLive/" + crewId + "/_m").set(Object.keys(m).length ? m : null);
  await rt.ref("crewLive/" + crewId + "/_mv").set(1);
  return ms.size;
}
// 아지트 채팅 — 14일이 지났거나 200줄을 넘은 옛 줄을 지운다
async function chatTrim(crewId) {
  const rt = getDatabase(), ref = rt.ref("crewLive/" + crewId + "/chat");
  const snap = await ref.orderByKey().once("value");
  const rows = []; snap.forEach((c) => { rows.push({ k: c.key, at: Number((c.val() || {}).t) || 0 }); });   // 앱이 쓰는 시각 필드는 t
  const cut = now() - CHAT_KEEP_DAYS * 864e5, drop = {};
  rows.forEach((r, i) => { if (r.at && r.at < cut) drop[r.k] = null; if (rows.length - i > CHAT_KEEP_N) drop[r.k] = null; });
  if (Object.keys(drop).length) await ref.update(drop);
  return Object.keys(drop).length;
}

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
    // 기간이 끝난 챌린지 보상 정산(달성·실패 모두 — 내 목표 보상은 실패해도 준다). 끊긴 정산도 여기서 이어서 한다.
    //   (rewardPaid 는 만들 때 없는 필드라 == false 로는 못 찾는다 → 읽고 걸러낸다)
    const ended = await c.ref.collection("challenges").where("status", "in", ["done", "failed"]).get().catch(() => null);
    if (ended) for (const s of ended.docs) if (!s.data().rewardPaid && now() >= s.data().end) await finishChallenge(c.id, s.id);
    // 아지트: 명단 거울 처음 채우기 · 채팅 정리 — 실패해도 챌린지 정리는 계속
    try {
      const mv = await getDatabase().ref("crewLive/" + c.id + "/_mv").once("value");
      if (mv.val() !== 1) console.log(`crew mirror backfill ${c.id} n=${await mirrorBackfill(c.id)}`);
      const t = await chatTrim(c.id); if (t) console.log(`crew chat trim ${c.id} n=${t}`);
    } catch (e) { console.warn("crew agit hourly", c.id, e && e.message); }
  }
  if (n) console.log(`crewHourly failed=${n}`);
});

