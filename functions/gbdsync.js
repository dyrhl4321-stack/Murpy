// ─────────────────────────────────────────────────────────────────────────────
// ★10-06 스쿼드 → 근방단 출첵앱(gbdcrew) 자동 연동 — 버튼 없이, 스쿼드가 열리는 순간부터.
//   대표: "모임 끝나고 옮기는 게 아니라 스쿼드 개설 이후 그냥 전부 다 연동이 되어야 한다".
//   대상 = **근방단 명단과 연결된 사람이 연** 스쿼드(일반 머피 유저 스쿼드는 안 간다) · 2026-10-07 이후 일정만
//          (그 전 스쿼드는 대표가 이미 근방단 앱에 손으로 옮겼다).
//   명단 = 근방단 명단과 짝이 맞은 사람만. 짝이 안 맞은 사람은 빼 두고, 관리자가 짝을 맞추면
//          그 사람의 스쿼드를 다시 보낸다(resyncUid — functions `gbd` 가 부른다).
//   취소·삭제 = 근방단 앱에서 아무도 손대지 않았으면 모임도 지운다.
//   모임 문서 id = murpy_<sid>(관리자가 예전 '보내기'로 다른 모임에 합쳤으면 murpySquad 로 찾는다).
//   ★동시에 여러 번 뛴다(체크 10명 = 10번). 근방단 문서는 **읽은 뒤 바뀌었으면 쓰기를 거절**하게
//     (updateTime 전제조건) 쓰고 처음부터 다시 한다 — 모임 문서를 **스쿼드보다 먼저** 읽어야
//     늦게 읽은 쪽이 항상 더 새 스쿼드를 본다.
// ─────────────────────────────────────────────────────────────────────────────
const { onDocumentWritten } = require("firebase-functions/v2/firestore");
const { onSchedule } = require("firebase-functions/v2/scheduler");
const { getFirestore } = require("firebase-admin/firestore");
const L = require("./gbdsync_logic.js");

const GBD_API = process.env.GBD_API_OVERRIDE   // 에뮬레이터 테스트 때만 바꾼다
  || "https://firestore.googleapis.com/v1/projects/gbdcrewcheck-2af48/databases/(default)/documents";
const SYNC_FROM = Date.parse(process.env.GBD_SYNC_FROM_OVERRIDE || "2026-10-07T00:00:00+09:00");   // override 는 테스트용
const COLLS = ["gbd_meetings", "gbd_archive"];

// --- Firestore REST 값 변환 ---
function dec(v) {
  if (!v) return null;
  if ("stringValue" in v) return v.stringValue;
  if ("integerValue" in v) return Number(v.integerValue);
  if ("doubleValue" in v) return v.doubleValue;
  if ("booleanValue" in v) return v.booleanValue;
  if ("nullValue" in v) return null;
  if ("timestampValue" in v) return v.timestampValue;
  if ("arrayValue" in v) return (v.arrayValue.values || []).map(dec);
  if ("mapValue" in v) { const o = {}, f = v.mapValue.fields || {}; Object.keys(f).forEach((k) => { o[k] = dec(f[k]); }); return o; }
  return null;
}
function enc(x) {
  if (x === null || x === undefined) return { nullValue: null };
  if (typeof x === "boolean") return { booleanValue: x };
  if (typeof x === "number") return Number.isInteger(x) ? { integerValue: String(x) } : { doubleValue: x };
  if (typeof x === "string") return { stringValue: x };
  if (Array.isArray(x)) return { arrayValue: { values: x.map(enc) } };
  const f = {}; Object.keys(x).forEach((k) => { if (x[k] !== undefined) f[k] = enc(x[k]); });
  return { mapValue: { fields: f } };
}
const docUrl = (path, qs) => GBD_API + "/" + path.split("/").map(encodeURIComponent).join("/") + (qs ? "?" + qs : "");
const idOf = (name) => decodeURIComponent(String(name || "").split("/").pop());

// 근방단 명단 → { active: { 머피uid: 근방단실명 }, all: 나간 사람(removed)까지 }
//   ★나간 사람: 다가오는 모임에선 빠지고, 지난 모임의 출석 기록은 그대로 남아야 한다(출석 통계·퇴출 판정 근거).
async function linkMap() {
  const out = { active: {}, all: {} }; let tok = "";
  for (let i = 0; i < 20; i++) {
    const r = await fetch(docUrl("gbd_members", "pageSize=300" + (tok ? "&pageToken=" + encodeURIComponent(tok) : "")));
    if (!r.ok) throw new Error("gbd members " + r.status);
    const j = await r.json();
    (j.documents || []).forEach((d) => {
      const m = dec({ mapValue: { fields: d.fields || {} } });
      if (!m.murpyUid) return;
      const name = m.name || idOf(d.name);
      out.all[m.murpyUid] = name;
      if (m.status !== "removed") out.active[m.murpyUid] = name;
    });
    if (!j.nextPageToken) break; tok = j.nextPageToken;
  }
  return out;
}

// 이 스쿼드의 근방단 모임 찾기 → { path, updateTime, data } | null
async function findMeeting(sid) {
  for (const c of COLLS) {
    const r = await fetch(docUrl(c + "/murpy_" + sid));
    if (r.status === 404) continue;
    if (!r.ok) throw new Error("gbd get " + r.status);
    const j = await r.json();
    return { path: c + "/murpy_" + sid, updateTime: j.updateTime, data: dec({ mapValue: { fields: j.fields || {} } }) };
  }
  for (const c of COLLS) {
    const r = await fetch(GBD_API + ":runQuery", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ structuredQuery: { from: [{ collectionId: c }], limit: 1,
        where: { fieldFilter: { field: { fieldPath: "murpySquad" }, op: "EQUAL", value: { stringValue: sid } } } } }),
    });
    if (!r.ok) throw new Error("gbd query " + r.status);
    const hit = ((await r.json()) || []).find((x) => x.document);
    if (hit) return { path: c + "/" + idOf(hit.document.name), updateTime: hit.document.updateTime, data: dec({ mapValue: { fields: hit.document.fields || {} } }) };
  }
  return null;
}

class Conflict extends Error {}
// 쓰기·지우기는 :commit 으로 — 전제조건(읽은 뒤 바뀌었으면 거절)을 본문에 싣는다.
//   주소창 쿼리(currentDocument.updateTime=)는 에뮬레이터가 못 읽어 테스트가 안 됐다.
const GBD_ROOT = GBD_API.replace(/\/documents$/, "");
const docName = (path) => GBD_API.slice(GBD_API.indexOf("projects/")) + "/" + path;
async function commit(w) {
  const r = await fetch(GBD_ROOT + "/documents:commit", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ writes: [w] }) });
  if (r.ok) return;
  const t = await r.text();
  if (/FAILED_PRECONDITION|ALREADY_EXISTS|NOT_FOUND/.test(t)) throw new Conflict(t.slice(0, 120));
  throw new Error("gbd commit " + r.status + " " + t.slice(0, 200));
}
const pre = (updateTime) => (updateTime ? { updateTime } : { exists: false });
const write = (path, fields, updateTime, mask) => commit(Object.assign(
  { update: { name: docName(path), fields: enc(fields).mapValue.fields }, currentDocument: pre(updateTime) },
  mask ? { updateMask: { fieldPaths: mask } } : {}));
const remove = (path, updateTime) => commit({ delete: docName(path), currentDocument: pre(updateTime) });

async function syncOnce(sid, links) {
  const meeting = await findMeeting(sid);          // ★모임 먼저, 스쿼드는 그 다음
  const db = getFirestore();
  const sRef = db.collection("squads").doc(sid);
  const sSnap = await sRef.get();
  const s = sSnap.exists ? sSnap.data() : null;

  if (!s || s.status === "cancelled") {
    if (meeting && L.untouched(meeting.data)) { await remove(meeting.path, meeting.updateTime); return "deleted"; }
    return "skip-gone";
  }
  if (!meeting) {
    if ((Number(s.scheduledAt) || 0) < SYNC_FROM) return "skip-old";
    if (!links.active[s.hostUid]) return "skip-host";      // 근방단 사람이 연 스쿼드가 아니다
  }
  const mSnap = await sRef.collection("members").get();
  const members = {}; mSnap.forEach((d) => { members[d.id] = d.data(); });
  const meta = L.squadMeta(s);
  const past = meta.date < L.kstDate(Date.now());
  const ours = L.oursFromMembers(members, past ? links.all : links.active);
  const patch = L.mergeMeeting(meeting && meeting.data, ours, meta, sid);
  if (!patch) return "same";
  if (meeting) {
    await write(meeting.path, patch, meeting.updateTime, Object.keys(patch));
    return "updated";
  }
  // 새 모임. 날짜가 지났으면 근방단 앱이 열릴 때 지난 모임으로 옮기니 처음부터 그쪽에 둔다
  const doc = Object.assign({ gongeum: meta.fee > 0, password: "", guestGroup: "", guests: [], guestStatus: [] }, patch,
    past ? { archivedAt: new Date().toISOString() } : {});
  await write((past ? "gbd_archive" : "gbd_meetings") + "/murpy_" + sid, doc, null, null);
  return "created";
}

async function syncSquad(sid, links) {
  links = links || await linkMap();
  for (let i = 0; i < 6; i++) {
    try { return await syncOnce(sid, links); } catch (e) {
      if (!(e instanceof Conflict)) throw e;
      await new Promise((r) => setTimeout(r, 150 + Math.random() * 400 * (i + 1)));
    }
  }
  throw new Error("gbd sync conflict x6 " + sid);
}

// 짝이 새로 맞거나 풀린 사람 → 그 사람이 든 2026-10-07 이후 스쿼드를 다시 보낸다
async function resyncUid(uids) {
  const list = [...new Set((uids || []).filter(Boolean))];
  if (!list.length) return 0;
  const db = getFirestore();
  const sids = new Set();
  for (const u of list) {
    const q = await db.collection("squads").where("memberUids", "array-contains", u).get();
    q.forEach((d) => { if ((Number(d.data().scheduledAt) || 0) >= SYNC_FROM) sids.add(d.id); });
  }
  const links = await linkMap();
  let n = 0;
  for (const sid of sids) {
    try { await syncSquad(sid, links); n++; } catch (e) { console.warn("gbd resync", sid, e.message); }
  }
  return n;
}

// --- 트리거: 관련 칸이 바뀐 쓰기에만 뛴다(지각 판정·채팅 수 같은 건 무시) ---
const pick = (o, ks) => JSON.stringify(ks.map((k) => (o ? o[k] : undefined)));
const SQ_KEYS = ["hostUid", "scheduledAt", "location", "title", "feeAmount", "status"];
const MEM_KEYS = ["status", "checkinType", "checkedIn", "paid"];
const scheduledOf = (ev) => {
  const a = ev.data.after && ev.data.after.exists ? ev.data.after.data() : null;
  const b = ev.data.before && ev.data.before.exists ? ev.data.before.data() : null;
  return { a, b };
};

exports.gbdSyncSquad = onDocumentWritten("squads/{sid}", async (ev) => {
  const { a, b } = scheduledOf(ev);
  if (pick(a, SQ_KEYS) === pick(b, SQ_KEYS)) return;
  if ((Number((a || b || {}).scheduledAt) || 0) < SYNC_FROM) return;
  const r = await syncSquad(ev.params.sid);
  console.log("gbd sync squad", ev.params.sid, r);
});
exports.gbdSyncMember = onDocumentWritten("squads/{sid}/members/{uid}", async (ev) => {
  const { a, b } = scheduledOf(ev);
  if (pick(a, MEM_KEYS) === pick(b, MEM_KEYS)) return;
  const s = await getFirestore().collection("squads").doc(ev.params.sid).get();
  if (s.exists && (Number(s.data().scheduledAt) || 0) < SYNC_FROM) return;
  const r = await syncSquad(ev.params.sid);
  console.log("gbd sync member", ev.params.sid, ev.params.uid, r);
});

// 매시간 최근·다가오는 스쿼드를 다시 맞춘다 — 근방단 쪽 변화(멤버스에서 나감 처리 등)는 머피 트리거가
//   못 듣는다. 트리거가 실패했던 것도 여기서 메워진다.
//   ★시작 후 24시간까지 포함: 출첵앱의 일부 저장(모임 저장·지난 모임 편집·출석 초기화)은 화면에 들고 있던
//     값을 통째로 다시 써서 방금 머피가 보낸 칸을 옛 값으로 되돌릴 수 있다 — 모임 도중이 제일 흔하다.
//     옛 murpySent 도 같이 되돌아가므로 다음 맞춤에서 "머피 값 ≠ murpySent" 로 그 사람 칸만 복구된다.
//     (나간 사람은 지난 모임이면 links.all 로 유지되니 출석 기록이 지워지지 않는다)
exports.gbdSyncHourly = onSchedule({ region: "asia-northeast3", schedule: "every 60 minutes" }, async () => {
  const q = await getFirestore().collection("squads").where("scheduledAt", ">=", Math.max(SYNC_FROM, Date.now() - 24 * 3600 * 1000)).get();
  if (q.empty) return;
  const links = await linkMap();
  const r = {};
  for (const d of q.docs) {
    try { const x = await syncSquad(d.id, links); r[x] = (r[x] || 0) + 1; } catch (e) { console.warn("gbd hourly", d.id, e.message); }
  }
  console.log("gbd hourly", q.size, JSON.stringify(r));
});

exports.resyncUid = resyncUid;
exports.syncSquad = syncSquad;
