// ─────────────────────────────────────────────────────────────────────────────
// ★10-19 크루 기록 — 판정·집계 순수 로직(파이어베이스 없음, 단위 시험 test/crew_logic.test.js).
//   설계 = docs/superpowers/specs/2026-10-19-crew-records-design.md
//   입출력(Firestore·제미나이)은 crew.js 가 하고, 숫자 계산은 전부 여기서 한다.
//   ★CFG 는 index.html 의 CREW_CFG 와 같은 값이어야 한다. 바꾸면 양쪽을 같이.
// ─────────────────────────────────────────────────────────────────────────────
const CFG = {
  RUN_REWARD: 10, RUN_REWARD_PER_DAY: 3, HEALTH_LINK_REWARD: 100,
  CHALLENGE_REWARD_GROUP: 300, CHALLENGE_REWARD_SOLO: 200,   // 대표 확정 10-19: 함께 달성 300(기간 중 운동한 사람) · 내 목표 200
  MILESTONES: [100, 500, 1000],
  RUN_PER_HEAD_KM: 15, GYM_PER_HEAD: 6, CHALLENGE_DAYS: 14,
  KM_MIN: 0.5, KM_MAX: 100, PACE_MIN: 150, PACE_MAX: 900, TIME_TOL: 0.12, MAX_AGE_DAYS: 7,
};
const DAY = 864e5;

// 하루 경계 = KST 새벽 5시(functions earn 과 같음)
function kstDay(ms) { return new Date(ms + 9 * 3600e3 - 5 * 3600e3).toISOString().slice(0, 10).replace(/-/g, ""); }
function monthKey(day) { return String(day).slice(0, 6); }
function dayToUtc(day) { const s = String(day); return Date.UTC(+s.slice(0, 4), +s.slice(4, 6) - 1, +s.slice(6, 8)); }
function weekKey(day) {
  const d = new Date(dayToUtc(day));
  const wd = d.getUTCDay() || 7;                 // 월=1 … 일=7
  d.setUTCDate(d.getUTCDate() + 4 - wd);         // 그 주 목요일이 속한 해가 ISO 연도
  const y = d.getUTCFullYear();
  const wk = Math.ceil(((d - Date.UTC(y, 0, 1)) / DAY + 1) / 7);
  return y + "-W" + String(wk).padStart(2, "0");
}
function prevWeekKey(wk) {
  const [y, w] = wk.split("-W").map(Number);
  // 그 주 목요일에서 7일 전
  const jan4 = Date.UTC(y, 0, 4), jan4wd = new Date(jan4).getUTCDay() || 7;
  const thu = jan4 + (4 - jan4wd) * DAY + (w - 1) * 7 * DAY;
  return weekKey(kstDayUtc(thu - 7 * DAY));
}
function kstDayUtc(ms) { return new Date(ms).toISOString().slice(0, 10).replace(/-/g, ""); }

// ── 제미나이 응답 정규화 ─────────────────────────────────────────────────────
function toNum(v) {
  if (typeof v === "number") return isFinite(v) ? v : null;
  if (typeof v !== "string") return null;
  const m = v.replace(/,/g, "").match(/-?\d+(\.\d+)?/);
  return m ? Number(m[0]) : null;
}
// "25:31" · "1:52:03" · "5'05\"" · 1531 → 초
function toSec(v) {
  if (typeof v === "number") return isFinite(v) ? Math.round(v) : null;
  if (typeof v !== "string") return null;
  const parts = v.match(/\d+/g);
  if (!parts) return null;
  if (parts.length === 1) return Number(parts[0]);
  return parts.slice(-3).reduce((a, p) => a * 60 + Number(p), 0);
}
function parseOcr(text) {
  let o;
  try { o = JSON.parse(text); } catch (e) { return null; }
  if (!o || typeof o !== "object") return null;
  const app = ["strava", "nrc"].includes(o.app) ? o.app : "unknown";
  const dateISO = typeof o.dateISO === "string" && /^\d{4}-\d{2}-\d{2}$/.test(o.dateISO) ? o.dateISO : null;
  return { isRunCard: o.isRunCard === true, app, km: toNum(o.km), sec: toSec(o.sec), paceSec: toSec(o.paceSec), dateISO };
}

// 우리 버킷의 uploads/{uid}/ 다운로드 URL 만 받는다 → Storage 경로
function storagePathOf(url, uid, bucket) {
  let u;
  try { u = new URL(String(url)); } catch (e) { return null; }
  if (u.hostname !== "firebasestorage.googleapis.com") return null;
  const m = u.pathname.match(/^\/v0\/b\/([^/]+)\/o\/(.+)$/);
  if (!m || m[1] !== bucket) return null;
  const path = decodeURIComponent(m[2]);
  return path.startsWith("uploads/" + uid + "/") && !path.includes("..") ? path : null;
}

// ── 카드 판정 ───────────────────────────────────────────────────────────────
function checkCard(ocr, { nowMs }) {
  if (!ocr) return { ok: false, why: "unreadable" };
  if (!ocr.isRunCard) return { ok: false, why: "not_card" };
  const km = ocr.km;
  if (!(km > 0)) return { ok: false, why: "unreadable" };
  let sec = ocr.sec > 0 ? Math.round(ocr.sec) : null;
  let paceSec = ocr.paceSec > 0 ? Math.round(ocr.paceSec) : null;
  if (!sec && !paceSec) return { ok: false, why: "unreadable" };
  if (km < CFG.KM_MIN || km > CFG.KM_MAX) return { ok: false, why: "km_range" };
  if (sec && paceSec && Math.abs(km * paceSec - sec) / sec > CFG.TIME_TOL) {
    // 페이스 범위 밖이 먼저 보이면 그걸 이유로
    if (paceSec < CFG.PACE_MIN || paceSec > CFG.PACE_MAX) return { ok: false, why: "pace_range" };
    return { ok: false, why: "time_mismatch" };
  }
  if (!paceSec) paceSec = Math.round(sec / km);
  if (!sec) sec = Math.round(km * paceSec);
  if (paceSec < CFG.PACE_MIN || paceSec > CFG.PACE_MAX) return { ok: false, why: "pace_range" };
  const today = kstDay(nowMs);
  let runDay = today, dayFromCard = false;
  if (ocr.dateISO) {
    runDay = ocr.dateISO.replace(/-/g, "");
    dayFromCard = true;
    const age = (dayToUtc(today) - dayToUtc(runDay)) / DAY;
    if (age < -1) return { ok: false, why: "bad_date" };          // 미래(시차 하루는 봐준다)
    if (age > CFG.MAX_AGE_DAYS) return { ok: false, why: "too_old" };
  }
  return { ok: true, run: { km, sec, paceSec, runDay, dayFromCard, app: ocr.app || "unknown" } };
}

// 같은 날·같은 거리에 시간(반올림 오차 허용) 또는 페이스(1초)가 같으면 같은 기록.
//   ★시간 줄을 잘라 내고 다시 올리면 시간이 '거리×페이스'로 되살아나 몇 초 어긋난다(리뷰 10-19) — 오차를 거리에 비례해 준다.
function isDupRun(run, existing) {
  const tol = Math.max(2, run.km * 0.6);
  return (existing || []).some((e) => e.runDay === run.runDay && Math.abs(e.km - run.km) < 0.01
    && (Math.abs(e.sec - run.sec) <= tol || (e.paceSec > 0 && run.paceSec > 0 && Math.abs(e.paceSec - run.paceSec) <= 1)));
}
// 챌린지 기간 판정에 쓰는 '기록 시각' = 기록한 날 한국 시간 정오(올린 시각이 아니다 — 리뷰 10-19)
function runAtMs(runDay) {
  const d = String(runDay);
  return Date.parse(d.slice(0, 4) + "-" + d.slice(4, 6) + "-" + d.slice(6, 8) + "T12:00:00+09:00");
}
// ★체크인은 클라이언트가 직접 쓴다(GPS 판정도 클라이언트). 날짜만큼은 믿지 않는다 —
//   문서 id 가 앱이 쓰는 모양(uid_센터_날짜)이고 그 날짜가 서버 시각의 한국 날짜(자정 경계, 직전 하루까지)와 맞을 때만 센다.
//   안 그러면 날짜만 바꾼 가짜 체크인 60개로 크루 출석·챌린지 머피·성주를 만들 수 있다(리뷰 10-19).
function checkinDay(id, data, createMs) {
  if (!data || !data.uid || !data.centerId || !data.day) return null;
  const day = String(data.day);
  if (String(id) !== data.uid + "_" + data.centerId + "_" + day) return null;
  const today = kstDayUtc(createMs + 9 * 3600e3), yday = kstDayUtc(createMs + 9 * 3600e3 - DAY);
  return day === today || day === yday ? day : null;
}

// ── 건강 앱 원본 대조(2차에서 씀) ─────────────────────────────────────────
//   거리: max(0.15km, 3%) · 시간: max(120초, 10%) — 스트라바 '이동 시간'과 건강 앱 운동 시간은 멈춘 시간만큼 다르다.
function matchHealth(run, workouts) {
  for (const w of workouts || []) {
    if (!w || w.userEntered) continue;
    if (kstDay(w.start) !== run.runDay) continue;
    if (Math.abs(w.km - run.km) > Math.max(0.15, run.km * 0.03)) continue;
    const dur = w.sec > 0 ? w.sec : (w.end - w.start) / 1000;
    if (Math.abs(dur - run.sec) > Math.max(120, run.sec * 0.1)) continue;
    return { ok: true, source: { kind: w.kind || "health", app: w.app || "", start: w.start, end: w.end, km: w.km }, why: "" };
  }
  return { ok: false, source: null, why: "no_match" };
}

// ── 카운터 ──────────────────────────────────────────────────────────────────
//   크루·멤버: 인증 = km/runs/monthKm(점수), 미인증 = pKm/pRuns(표시만).
//   개인(personal): km/runs/monthKm 는 전부, vKm/vRuns 는 인증만, 최고 기록·연속 주.
function rollMonth(s, mk) {
  if (!s.monthKey || mk > s.monthKey) { s.monthKey = mk; s.monthKm = 0; s.monthAttends = 0; return true; }
  return mk === s.monthKey;
}
const r2 = (x) => Math.round(x * 100) / 100;
function addRun(stats, run, { verified, personal }, sign) {
  const s = Object.assign({ km: 0, runs: 0 }, stats);
  const mk = monthKey(run.runDay);
  const inMonth = sign > 0 ? rollMonth(s, mk) : mk === s.monthKey;
  if (personal) {
    s.km = r2(s.km + sign * run.km); s.runs += sign;
    s.vKm = r2((s.vKm || 0) + (verified ? sign * run.km : 0)); s.vRuns = (s.vRuns || 0) + (verified ? sign : 0);
    if (inMonth) s.monthKm = r2((s.monthKm || 0) + sign * run.km);
    if (sign > 0) {
      if (!(s.bestKm >= run.km)) s.bestKm = run.km;
      if (run.paceSec && !(s.bestPaceSec <= run.paceSec)) s.bestPaceSec = run.paceSec;
      const wk = weekKey(run.runDay);
      if (!s.lastWeekKey) { s.weekStreak = 1; s.lastWeekKey = wk; }
      else if (wk > s.lastWeekKey) { s.weekStreak = prevWeekKey(wk) === s.lastWeekKey ? (s.weekStreak || 0) + 1 : 1; s.lastWeekKey = wk; }
    }
  } else if (verified) {
    s.km = r2(s.km + sign * run.km); s.runs += sign;
    if (inMonth) s.monthKm = r2((s.monthKm || 0) + sign * run.km);
  } else {
    s.pKm = r2((s.pKm || 0) + sign * run.km); s.pRuns = (s.pRuns || 0) + sign;
  }
  return s;
}
function applyRun(stats, run, opts) { return addRun(stats, run, opts || {}, 1); }
function revertRun(stats, run, opts) { return addRun(stats, run, opts || {}, -1); }

function applyAttend(member, day) {
  const m = Object.assign({ attends: 0 }, member);
  if (m.lastAttendDay === day) return { member: m, counted: false };
  m.attends += 1;
  if (rollMonth(m, monthKey(day))) m.monthAttends = (m.monthAttends || 0) + 1;
  m.lastAttendDay = day;
  return { member: m, counted: true };
}
// 크루 문서 쪽 출석 +n(멤버가 counted 일 때만 부른다)
function addAttend(stats, day, n) {
  const s = Object.assign({ attends: 0 }, stats);
  s.attends += n;
  if (rollMonth(s, monthKey(day))) s.monthAttends = (s.monthAttends || 0) + n;
  return s;
}

function weekActiveDelta(member, wk) {
  if (member.weekKey === wk) return 0;
  if (member.weekKey && member.weekKey > wk) return 0;   // 지난주 기록이 늦게 와도 이번 주를 되돌리지 않는다
  member.weekKey = wk;
  return 1;
}
function crewWeekAdd(stats, wk, delta) {
  const s = Object.assign({}, stats);
  if (s.weekKey !== wk) { if (s.weekKey && s.weekKey > wk) return s; s.weekKey = wk; s.weekActive = 0; }
  s.weekActive = (s.weekActive || 0) + delta;
  return s;
}

function challengeStep(ch, { kind, amount, atMs, verified }) {
  const c = Object.assign({}, ch);
  if (c.status !== "active" || c.kind !== kind || !verified || !(atMs >= c.start && atMs < c.end)) return { ch: c, justDone: false };
  c.progress = r2((c.progress || 0) + amount);
  if (c.progress >= c.target) { c.status = "done"; c.doneAt = atMs; return { ch: c, justDone: true }; }
  return { ch: c, justDone: false };
}

// ── 챌린지 목표 인원 — 전체 인원이 아니라 '최근 2주 안에 한 번이라도 운동한 사람'(대표 10-19: 247명×6회 = 1482회는 비현실적) ──
//   운동 = 러닝 기록 올리기(인증·미인증 모두) 또는 헬스장 출석. 멤버 문서의 lastActiveDay 로 센다.
const ACTIVE_DAYS = 14, MIN_HEAD = 3;
function markActive(member, day) {
  const m = Object.assign({}, member);
  if (!m.lastActiveDay || String(day) > m.lastActiveDay) m.lastActiveDay = String(day);
  return m;
}
function activeHeadcount(members, today) {
  const cutoff = kstDayUtc(dayToUtc(today) - (ACTIVE_DAYS - 1) * DAY);
  const n = (members || []).filter((m) => m && !m.left && m.lastActiveDay && m.lastActiveDay >= cutoff).length;
  return Math.max(MIN_HEAD, n);
}

// ── 챌린지 보상(대표 10-19): 함께 달성 = 크루 목표를 채우면 기간 중 한 번이라도 운동한 크루원에게 GROUP,
//   내 목표 = 기간 중 1인 목표(perHead)를 채운 사람에게 SOLO(크루가 실패해도). 지급은 기간이 끝난 뒤 한 번.
//   멤버 문서에 chAct{챌린지id:true}(기간 중 활동) · ch{챌린지id:개인 진행}을 둔다.
//   활동 = 러닝 올리기(미인증 포함)·출석 / 개인 진행 = 같은 종류의 인증된 기록만(크루 합산과 같은 기준).
//   ★크루가 먼저 목표를 채워도(status done) 기간이 끝날 때까지 개인 진행은 계속 쌓는다.
function memberChallengeStep(member, ch, { kind, amount, atMs, verified }) {
  if (!ch || !(atMs >= ch.start && atMs < ch.end) || (ch.status !== "active" && ch.status !== "done")) return member;
  const m = Object.assign({}, member);
  m.chAct = Object.assign({}, m.chAct, { [ch.id]: true });
  if (ch.kind === kind && verified) m.ch = Object.assign({}, m.ch, { [ch.id]: r2(((m.ch || {})[ch.id] || 0) + amount) });
  return m;
}
function settleChallenge(ch, members) {
  const out = [];
  (members || []).forEach((m) => {
    if (!m || m.left) return;
    if (ch.status === "done" && (m.chAct || {})[ch.id]) out.push({ uid: m.uid, amount: CFG.CHALLENGE_REWARD_GROUP, key: ch.id + "_g" });
    if (ch.perHead > 0 && ((m.ch || {})[ch.id] || 0) >= ch.perHead) out.push({ uid: m.uid, amount: CFG.CHALLENGE_REWARD_SOLO, key: ch.id + "_i" });
  });
  return out;
}

function newMilestones(prevKm, nextKm, reached) {
  return CFG.MILESTONES.filter((m) => prevKm < m && nextKm >= m && !(reached || []).includes(m));
}

function duelScore(a, b) {
  const per = (x) => (x.members > 0 ? x.total / x.members : 0);
  const top = Math.max(per(a), per(b));
  const one = (x) => {
    const rate = x.members > 0 ? x.active / x.members : 0;
    return Math.round((rate * 50 + (top > 0 ? per(x) / top : 0) * 50) * 10) / 10;
  };
  return { a: one(a), b: one(b) };
}

module.exports = {
  CFG, kstDay, monthKey, weekKey, parseOcr, storagePathOf, checkCard, isDupRun, runAtMs, checkinDay, matchHealth,
  applyRun, revertRun, applyAttend, addAttend, weekActiveDelta, crewWeekAdd, challengeStep, newMilestones, duelScore, markActive, activeHeadcount, memberChallengeStep, settleChallenge,
};
