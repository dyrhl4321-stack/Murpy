// ─────────────────────────────────────────────────────────────────────────────
// ★10-27 소모임 캡처 → 근방단 스쿼드 (대표 "ㅇㅇ") — 대표는 근손실방지단 정모를 소모임 앱에서 연다.
//   그 화면 캡처(정모 목록·참석자)를 올리면 근방단 스쿼드가 바로 올라간다. 확인 화면 없이 바로 올리고 결과만 돌려준다.
//   ① 권한 = 관리자 · 근손실방지단(crewsV2) 크루장·운영진.
//   ② 읽기 = 러닝 인증샷 스캔과 같은 키·모델(GEMINI · gemini-3.5-flash-lite). 장마다 한 번, 실패하면 한 번 더.
//   ③ 이름 = 근방단 명부(gbd_members: 실명·소모임 닉네임 → murpyUid). 하나뿐인 정확한 짝만 머피 계정으로,
//      나머지는 스쿼드 extNames(회색 이름만, 정원 계산엔 넣는다) — 관리자가 '근방단 멤버 연결'에서 짝을 맞추면 계정으로 바뀐다.
//   ④ 만들기 = 문서 id smo_(제목+시작 시각). 같은 정모를 또 보내면 고친다(사람은 더하기만).
//      참석자 화면은 제목이 없어 같은 시각의 정모(같이 보낸 목록 → 이미 올린 smo_ 스쿼드)에 붙인다.
//   ⑤ 출첵앱 = 관리자·근방단 연결자가 연 스쿼드라 기존 gbdSyncSquad 가 그대로 가져간다(짝 맞은 사람만).
//   올린 캡처 원본은 읽은 뒤 지운다. 시도마다 gbdCaptureLog(누가·몇 장·결과·토큰).
// ─────────────────────────────────────────────────────────────────────────────
const { onCall, HttpsError } = require("firebase-functions/v2/https");
const { defineSecret } = require("firebase-functions/params");
const { getFirestore, FieldValue } = require("firebase-admin/firestore");
const { getStorage } = require("firebase-admin/storage");
const CL = require("./crew_logic.js");
const L = require("./gbdcapture_logic.js");
const S = require("./gbdsync.js");

const REGION = "asia-northeast3";
const GEMINI = defineSecret("GEMINI_API_KEY");
const BUCKET = "murpyprototype.firebasestorage.app";
const MODEL = "gemini-3.5-flash-lite";   // crew.js OCR_MODEL 과 같게
const OCR_URL = process.env.SMO_OCR_URL_OVERRIDE   // 에뮬레이터 시험 때만(.env.local)
  || `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent`;
const GBD_CREW = "FSuECLq2EanaXSrBQxdz";   // crewsV2 근손실방지단
const ADMIN_EMAILS = ["dyrhl4321@gmail.com"];
const isAdminReq = (req) => !!(req.auth && req.auth.token && req.auth.token.email_verified !== false && ADMIN_EMAILS.includes(String(req.auth.token.email || "")));
const db = () => getFirestore();

const SCHEMA = {
  type: "OBJECT",
  properties: {
    screen: { type: "STRING", enum: ["list", "attendees", "detail", "other"] },
    meetings: { type: "ARRAY", items: { type: "OBJECT", properties: {
      title: { type: "STRING", nullable: true }, date: { type: "STRING", nullable: true }, time: { type: "STRING", nullable: true },
      place: { type: "STRING", nullable: true }, cost: { type: "STRING", nullable: true },
      capacity: { type: "INTEGER", nullable: true }, joined: { type: "INTEGER", nullable: true },
      type: { type: "STRING", enum: L.TYPES }, photoBox: { type: "ARRAY", items: { type: "INTEGER" }, nullable: true },
      attendees: { type: "ARRAY", items: { type: "STRING" } },
    } } },
  },
  required: ["screen", "meetings"],
};
const PROMPT = [
  "This is a screenshot from the Korean meetup app Somoim (소모임) of a fitness club. Read it.",
  "screen: 'list' if it shows meetup cards (정모) with D-day, title, 일시, 위치, 비용, 참석 (n/m); 'attendees' if it is a 참석자 list;",
  "'detail' if it is a single meetup page; otherwise 'other' (then meetings = []).",
  "meetings: one item per meetup whose title AND date are fully visible (skip cards cut off at the top or bottom).",
  "date = YYYY-MM-DD if a year is shown, else MM-DD. time = 24-hour HH:MM (오후 4:00 → 16:00).",
  "place = the 위치 text without '(지도보기)'. cost = the 비용 text as written. capacity and joined from '참석 3명 참석중 (3/10)' → joined 3, capacity 10.",
  "photoBox = tight [ymin, xmin, ymax, xmax] on a 0-1000 scale around that meetup's representative photo thumbnail, or null.",
  "type = the exercise from the title and place: gym (헬스·피트니스·PT·하체·등), running (러닝·런·마라톤), hyrox (하이록스), hiking (등산·산행), climbing, yoga, dance, golf, tennis. If unsure use gym.",
  "For an 'attendees' screen return exactly one meeting: title null, date and time from the header like '10/28일 오후 4:00 정모 참석자 (4명)', joined = that count,",
  "attendees = each person's main bold name exactly as written (not the small gray second line, not buttons like 거부).",
  "For 'list' cards attendees = [] (faces only). Never invent text that is not printed.",
].join(" ");

async function ocr(key, buf) {
  const body = {
    contents: [{ parts: [{ inline_data: { mime_type: "image/jpeg", data: buf.toString("base64") } }, { text: PROMPT }] }],
    generationConfig: { responseMimeType: "application/json", responseSchema: SCHEMA, temperature: 0, thinkingConfig: { thinkingLevel: "minimal" } },
  };
  for (let attempt = 0; attempt < 2; attempt++) {   // 한 번 더(응답 없음·5xx)
    const ac = new AbortController(), t = setTimeout(() => ac.abort(), 40000);
    try {
      const r = await fetch(OCR_URL, { method: "POST", headers: { "Content-Type": "application/json", "x-goog-api-key": key }, body: JSON.stringify(body), signal: ac.signal });
      if (!r.ok) { console.warn("smo ocr http", r.status, (await r.text()).slice(0, 200)); if (r.status < 500) return null; continue; }
      const j = await r.json(), u = j.usageMetadata || {};
      const text = j && j.candidates && j.candidates[0] && j.candidates[0].content && (j.candidates[0].content.parts || []).map((p) => p.text || "").join("");
      return { text: text || "", tokIn: u.promptTokenCount || 0, tokOut: (u.candidatesTokenCount || 0) + (u.thoughtsTokenCount || 0) };
    } catch (e) { console.warn("smo ocr fail", e && e.message); } finally { clearTimeout(t); }
  }
  return null;
}

async function canUse(req) {
  if (isAdminReq(req)) return true;
  const c = await db().collection("crewsV2").doc(GBD_CREW).get();
  return c.exists && CL.canModerate(c.data(), req.auth.uid);
}
const WK = ["일", "월", "화", "수", "목", "금", "토"];
function whenKo(ms) {
  const d = new Date(ms + 9 * 3600 * 1000);
  return (d.getUTCMonth() + 1) + "." + d.getUTCDate() + "(" + WK[d.getUTCDay()] + ") " + String(d.getUTCHours()).padStart(2, "0") + ":" + String(d.getUTCMinutes()).padStart(2, "0");
}
async function profileOf(uid) {
  try { const u = await db().collection("users").doc(uid).get(); const d = u.exists ? u.data() : {}; return { nickname: String(d.nickname || "머피").slice(0, 24), character: d.character || null }; }
  catch (e) { return { nickname: "머피", character: null }; }
}

// 한 정모를 스쿼드로 — 없으면 만들고 있으면 고친다. → { id, isNew, joined, cap, hasImg }
async function upsert(uid, m, people) {
  const d = db(), sid = m.sid, ref = d.collection("squads").doc(sid);
  const uids = Array.from(new Set(people.filter((p) => p.uid).map((p) => p.uid)));
  const ext = Array.from(new Set(people.filter((p) => !p.uid).map((p) => p.name)));
  const profs = {}; for (const u of uids) profs[u] = await profileOf(u);
  return d.runTransaction(async (tx) => {
    const s = await tx.get(ref), now = Date.now();
    const old = s.exists ? s.data() : null;
    const mem = Array.from(new Set(((old && old.memberUids) || []).concat(uids)));
    const extAll = Array.from(new Set(((old && old.extNames) || []).concat(ext))).filter((n) => !mem.some((u) => profs[u] && profs[u].nickname === n)).slice(0, 100);
    if (!old) {
      tx.set(ref, {
        hostUid: uid, memberUids: mem, title: m.title || "근방단 정모", exerciseType: m.type, centerId: null, location: m.place || "",
        scheduledAt: m.startMs, startedAt: null, endedAt: null, expiresAt: m.startMs + 4 * 3600 * 1000,
        capacity: Math.max(m.cap || 0, mem.length + extAll.length, 2), level: "mid", oneLineMemo: m.cost ? ("비용 " + m.cost).slice(0, 40) : "",
        img: null, joinMode: "open", feeAmount: L.feeOf(m.cost), status: "recruiting", source: "somoim", smoCost: m.cost || "",
        extNames: extAll, hostRewarded: false, createdAt: FieldValue.serverTimestamp(), smoAt: now, smoJoined: m.joined || 0,
      });
    } else {
      const patch = Object.assign(L.mergeInto(old, m), { memberUids: mem, extNames: extAll, smoAt: now });
      if (m.joined && m.joined !== old.smoJoined) patch.smoJoined = m.joined;   // 소모임 '3명 참석중' 숫자(목록 캡처엔 이름이 없다)
      if (!old.title && m.title) patch.title = m.title;
      const need = mem.length + extAll.length; if ((patch.capacity || old.capacity || 0) < need) patch.capacity = need;
      tx.update(ref, patch);
    }
    for (const u of uids) {
      if (old && (old.memberUids || []).includes(u)) continue;
      tx.set(ref.collection("members").doc(u), { status: "accepted", nickname: profs[u].nickname, character: profs[u].character, paid: false, joinedAt: FieldValue.serverTimestamp(), via: "somoim" }, { merge: true });
    }
    const cap = Math.max((old && old.capacity) || 0, m.cap || 0, mem.length + extAll.length);
    return { id: sid, isNew: !old, joined: mem.length + extAll.length, smoJoined: m.joined || (old && old.smoJoined) || 0, cap, hasImg: !!(old && old.img) };
  });
}

exports.gbdCapture = onCall({ region: REGION, secrets: [GEMINI], timeoutSeconds: 300, memory: "512MiB" }, async (req) => {
  const uid = req.auth && req.auth.uid;
  if (!uid) throw new HttpsError("unauthenticated", "login");
  if (!(await canUse(req))) throw new HttpsError("permission-denied", "gbd_staff_only");
  const data = req.data || {};

  // 대표 사진 붙이기 — 폰이 AI 가 준 자리로 잘라 올린 그림(본인 폴더)만, 내가 올린 smo_ 스쿼드에만
  if (data.cover) {
    const sid = String(data.cover.sid || ""), url = String(data.cover.url || "");
    if (!/^smo_[0-9a-f]{16}$/.test(sid) || !CL.storagePathOf(url, uid, BUCKET)) throw new HttpsError("invalid-argument", "cover");
    const ref = db().collection("squads").doc(sid), s = await ref.get();
    if (!s.exists || (s.data().hostUid !== uid && !isAdminReq(req))) throw new HttpsError("permission-denied", "not_host");
    if (!s.data().img) await ref.update({ img: url });
    return { ok: true };
  }

  const paths = (Array.isArray(data.paths) ? data.paths : []).slice(0, 10).map((p) => String(p || ""));
  if (!paths.length) throw new HttpsError("invalid-argument", "paths");
  const mine = (p) => p.startsWith("uploads/" + uid + "/smo_") && !p.includes("..");
  let gbdList = [], gbdOk = true;
  try { gbdList = await S.gbdMembers(); } catch (e) { gbdOk = false; console.warn("smo gbd members", e && e.message); }
  const now = Date.now(), items = [], found = [];   // found = { i, m }
  let tokIn = 0, tokOut = 0;
  for (let i = 0; i < paths.length; i++) {
    const p = paths[i];
    if (!p) { items.push({ ok: false, msg: "올리지 못했어요" }); continue; }
    if (!mine(p)) { items.push({ ok: false, msg: "이 캡처는 읽을 수 없어요" }); continue; }
    const file = getStorage().bucket(BUCKET).file(p);
    let buf = null;
    try { const [meta] = await file.getMetadata(); if (Number(meta.size) <= 10 * 1024 * 1024) [buf] = await file.download(); } catch (e) { console.warn("smo dl", e && e.message); }
    file.delete().catch(() => {});   // 원본은 읽고 바로 지운다
    if (!buf) { items.push({ ok: false, msg: "캡처를 열지 못했어요" }); continue; }
    const o = await ocr(GEMINI.value(), buf);
    if (!o) { items.push({ ok: false, msg: "지금 못 읽었어요 · 다시 보내 주세요" }); continue; }
    tokIn += o.tokIn; tokOut += o.tokOut;
    const r = L.parseCapture(o.text, now);
    if (!r || r.screen === "other") { items.push({ ok: false, msg: "정모 화면이 아니에요" }); continue; }
    if (!r.meetings.length) { items.push({ ok: false, msg: "날짜를 못 읽었어요 · 다시 보내 주세요" }); continue; }
    r.meetings.forEach((m) => found.push({ i, m }));
    items.push({ ok: true, screen: r.screen, n: r.meetings.length });
  }

  // 정모 단위로 모은다 — 제목 있는 것끼리는 (제목+시각), 참석자 화면(제목 없음)은 같은 시각의 정모에 붙인다
  const byKey = new Map();
  for (const f of found.filter((x) => x.m.title)) {
    const k = L.titleKey(f.m.title) + "|" + f.m.startMs, cur = byKey.get(k);
    if (cur) { cur.names = cur.names.concat(f.m.names); cur.m = Object.assign({}, cur.m, ...Object.entries(f.m).filter(([, v]) => v !== null && v !== "").map(([k2, v]) => ({ [k2]: v }))); }
    else byKey.set(k, { m: Object.assign({}, f.m, { sid: L.smoId(f.m.title, f.m.startMs) }), names: f.m.names.slice(), from: [f.i] });
  }
  const orphan = {};   // 참석자 화면 i → 붙인 결과
  for (const f of found.filter((x) => !x.m.title)) {
    let tgt = Array.from(byKey.values()).find((g) => g.m.startMs === f.m.startMs);
    if (!tgt) {   // 이미 올린 소모임 스쿼드 중 같은 시각
      const q = await db().collection("squads").where("scheduledAt", "==", f.m.startMs).get();
      const hit = q.docs.filter((x) => x.data().source === "somoim" && x.data().status !== "cancelled");
      if (hit.length === 1) { tgt = { m: Object.assign({}, f.m, { sid: hit[0].id, title: "" }), names: [], from: [] }; byKey.set("old|" + hit[0].id, tgt); }
    }
    if (!tgt) { orphan[f.i] = "이 참석자 화면의 정모를 못 찾았어요 · 정모 목록 캡처도 같이 보내 주세요"; continue; }
    tgt.names = tgt.names.concat(f.m.names); tgt.from.push(f.i);
    if (f.m.joined && !tgt.m.joined) tgt.m.joined = f.m.joined;
  }

  const squads = [], covers = [], unknown = new Set();
  for (const g of byKey.values()) {
    const people = L.matchNames(Array.from(new Set(g.names)), gbdList);
    people.filter((p) => !p.uid).forEach((p) => unknown.add(p.name));
    try {
      const r = await upsert(uid, g.m, people);
      squads.push({ id: r.id, title: g.m.title || "(참석자 추가)", when: whenKo(g.m.startMs), place: g.m.place || "", joined: r.joined, smoJoined: r.smoJoined, cap: r.cap, isNew: r.isNew });
      const src = found.find((f) => f.m.title && L.smoId(f.m.title, f.m.startMs) === r.id && f.m.photoBox);
      if (src && !r.hasImg) covers.push({ i: src.i, sid: r.id, box: src.m.photoBox });
    } catch (e) { console.warn("smo upsert", g.m.sid, e && e.message); }
  }
  // 장마다 한 줄 결과
  items.forEach((it, i) => {
    if (!it.ok) return;
    if (orphan[i]) { it.ok = false; it.msg = orphan[i]; return; }
    const mine2 = Array.from(byKey.values()).filter((g) => g.from.includes(i)), nNew = mine2.filter((g) => squads.find((q) => q.id === g.m.sid && q.isNew)).length;
    it.msg = it.screen === "attendees" ? "참석자 " + found.filter((f) => f.i === i).reduce((t, f) => t + f.m.names.length, 0) + "명 · " + (mine2[0] ? whenKo(mine2[0].m.startMs) + " 정모에 넣음" : "")
      : "정모 " + it.n + "개 · " + (nNew === mine2.length ? "새로 올림" : nNew ? "새로 " + nNew + " · 고침 " + (mine2.length - nNew) : "고침");
  });
  await db().collection("gbdCaptureLog").add({ by: uid, at: FieldValue.serverTimestamp(), n: paths.length, ok: items.filter((x) => x.ok).length,
    squads: squads.map((q) => q.id), unknown: Array.from(unknown).slice(0, 50), tokIn, tokOut, gbdOk }).catch(() => {});
  console.log(`gbdCapture by=${uid} n=${paths.length} squads=${squads.length} tok=${tokIn}/${tokOut}`);
  return { items: items.map((x) => ({ ok: x.ok, msg: x.msg })), squads, unknown: Array.from(unknown), covers, gbdOk };
});
