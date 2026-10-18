// 크루 기록 순수 로직 시험 — `cd functions && node --test test/`
const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("../crew_logic.js");

const NOW = Date.parse("2026-10-19T12:00:00+09:00");

test("kstDay 는 새벽 5시 경계", () => {
  assert.equal(L.kstDay(Date.parse("2026-10-19T04:59:00+09:00")), "20261018");
  assert.equal(L.kstDay(Date.parse("2026-10-19T05:00:00+09:00")), "20261019");
});

test("monthKey / weekKey", () => {
  assert.equal(L.monthKey("20261019"), "202610");
  assert.equal(L.weekKey("20261019"), "2026-W43");
  assert.equal(L.weekKey("20260101"), "2026-W01");
  assert.equal(L.weekKey("20251229"), "2026-W01");   // ISO 주는 연도를 넘는다
});

test("checkCard 정상 카드", () => {
  const r = L.checkCard({ isRunCard: true, app: "strava", km: 5.02, sec: 1531, paceSec: 305, dateISO: "2026-10-19" }, { nowMs: NOW });
  assert.equal(r.ok, true);
  assert.deepEqual(r.run, { km: 5.02, sec: 1531, paceSec: 305, runDay: "20261019", dayFromCard: true, app: "strava" });
});

test("checkCard 날짜 없는 카드는 올린 날로", () => {
  const r = L.checkCard({ isRunCard: true, app: "nrc", km: 5, sec: 1500, paceSec: null, dateISO: null }, { nowMs: NOW });
  assert.equal(r.ok, true);
  assert.equal(r.run.runDay, "20261019");
  assert.equal(r.run.dayFromCard, false);
  assert.equal(r.run.paceSec, 300);
});

test("checkCard 시간이 없으면 거리×페이스", () => {
  const r = L.checkCard({ isRunCard: true, km: 10, sec: null, paceSec: 330, dateISO: null }, { nowMs: NOW });
  assert.equal(r.ok, true);
  assert.equal(r.run.sec, 3300);
  assert.equal(r.run.app, "unknown");
});

test("checkCard 거르기", () => {
  const c = (o) => L.checkCard(Object.assign({ isRunCard: true, km: 5, sec: 1500, paceSec: 300, dateISO: "2026-10-19" }, o), { nowMs: NOW }).why;
  assert.equal(c({ isRunCard: false }), "not_card");
  assert.equal(c({ km: 0.3, sec: 90, paceSec: 300 }), "km_range");
  assert.equal(c({ km: 120, sec: 36000, paceSec: 300 }), "km_range");
  assert.equal(c({ km: 5, sec: 500, paceSec: 100 }), "pace_range");
  assert.equal(c({ km: 5, sec: 2000, paceSec: 300 }), "time_mismatch");
  assert.equal(c({ dateISO: "2026-10-11" }), "too_old");
  assert.equal(c({ dateISO: "2026-10-12" }), undefined);   // 7일 전은 통과
  assert.equal(c({ dateISO: "2026-10-22" }), "bad_date");  // 미래 날짜
  assert.equal(c({ km: null }), "unreadable");
  assert.equal(c({ sec: null, paceSec: null }), "unreadable");
  assert.equal(L.checkCard(null, { nowMs: NOW }).why, "unreadable");
});

test("isDupRun 같은 날·같은 거리·같은 시간(1초 오차)", () => {
  const run = { runDay: "20261019", km: 5.02, sec: 1531 };
  assert.equal(L.isDupRun(run, [{ runDay: "20261019", km: 5.02, sec: 1532 }]), true);
  assert.equal(L.isDupRun(run, [{ runDay: "20261018", km: 5.02, sec: 1531 }]), false);
  assert.equal(L.isDupRun(run, [{ runDay: "20261019", km: 5.1, sec: 1531 }]), false);
  assert.equal(L.isDupRun(run, []), false);
});

test("parseOcr 문자열 숫자 정규화", () => {
  const o = L.parseOcr(JSON.stringify({ isRunCard: true, app: "strava", km: "5.02 km", sec: "25:31", paceSec: "5'05\"", dateISO: "2026-10-19" }));
  assert.deepEqual(o, { isRunCard: true, app: "strava", km: 5.02, sec: 1531, paceSec: 305, dateISO: "2026-10-19" });
  const h = L.parseOcr('{"isRunCard":true,"km":21.1,"sec":"1:52:03","paceSec":"5:19","dateISO":"Oct 19"}');
  assert.equal(h.sec, 6723);
  assert.equal(h.paceSec, 319);
  assert.equal(h.dateISO, null);
  assert.equal(h.app, "unknown");
  assert.equal(L.parseOcr("not json"), null);
});

test("applyRun 크루: 미인증은 대기 숫자만, 인증은 점수", () => {
  const run = { km: 5, runDay: "20261019" };
  const a = L.applyRun({}, run, { verified: false });
  assert.equal(a.km, 0); assert.equal(a.pKm, 5); assert.equal(a.pRuns, 1); assert.equal(a.monthKm, 0);
  const b = L.applyRun(a, run, { verified: true });
  assert.equal(b.km, 5); assert.equal(b.runs, 1); assert.equal(b.monthKm, 5); assert.equal(b.monthKey, "202610");
});

test("applyRun 달이 바뀌면 이번 달 숫자 초기화, 지난달 기록은 이번 달에 안 더함", () => {
  const s = { km: 10, runs: 2, monthKey: "202609", monthKm: 10, monthAttends: 3 };
  const a = L.applyRun(s, { km: 5, runDay: "20261001" }, { verified: true });
  assert.equal(a.monthKey, "202610"); assert.equal(a.monthKm, 5); assert.equal(a.monthAttends, 0); assert.equal(a.km, 15);
  const b = L.applyRun(a, { km: 3, runDay: "20260930" }, { verified: true });
  assert.equal(b.monthKm, 5); assert.equal(b.km, 18);
});

test("revertRun 은 applyRun 을 되돌린다(같은 달)", () => {
  const s = { km: 10, runs: 2, pKm: 1, pRuns: 1, monthKey: "202610", monthKm: 10 };
  for (const verified of [true, false]) {
    const r = { km: 4.2, runDay: "20261019" };
    assert.deepEqual(L.revertRun(L.applyRun(s, r, { verified }), r, { verified }), s);
  }
});

test("applyRun 개인: 전부 누적 + 인증 따로 + 최고 기록 + 연속 주", () => {
  let s = L.applyRun({}, { km: 5, paceSec: 300, runDay: "20261012" }, { verified: false, personal: true });
  assert.equal(s.km, 5); assert.equal(s.runs, 1); assert.equal(s.vKm, 0); assert.equal(s.vRuns, 0);
  assert.equal(s.bestKm, 5); assert.equal(s.bestPaceSec, 300); assert.equal(s.weekStreak, 1);
  s = L.applyRun(s, { km: 10, paceSec: 320, runDay: "20261019" }, { verified: true, personal: true });
  assert.equal(s.km, 15); assert.equal(s.vKm, 10); assert.equal(s.vRuns, 1);
  assert.equal(s.bestKm, 10); assert.equal(s.bestPaceSec, 300); assert.equal(s.weekStreak, 2);
  s = L.applyRun(s, { km: 3, paceSec: 290, runDay: "20261020" }, { verified: false, personal: true });
  assert.equal(s.weekStreak, 2); assert.equal(s.bestPaceSec, 290);
  s = L.applyRun(s, { km: 3, paceSec: 310, runDay: "20261103" }, { verified: false, personal: true });
  assert.equal(s.weekStreak, 1);   // 한 주 건너뜀
});

test("applyAttend 같은 날 두 번째는 안 셈, 달 바뀌면 초기화", () => {
  const a = L.applyAttend({}, "20261019");
  assert.equal(a.counted, true); assert.equal(a.member.attends, 1); assert.equal(a.member.monthAttends, 1);
  const b = L.applyAttend(a.member, "20261019");
  assert.equal(b.counted, false); assert.equal(b.member.attends, 1);
  const c = L.applyAttend(Object.assign({}, a.member, { monthKey: "202609", monthAttends: 9, monthKm: 7 }), "20261020");
  assert.equal(c.member.monthAttends, 1); assert.equal(c.member.monthKm, 0); assert.equal(c.member.attends, 2);
});

test("weekActiveDelta 와 crewWeekAdd", () => {
  const m = {};
  assert.equal(L.weekActiveDelta(m, "2026-W43"), 1);
  assert.equal(L.weekActiveDelta(m, "2026-W43"), 0);
  assert.equal(L.weekActiveDelta(m, "2026-W44"), 1);
  const c = L.crewWeekAdd({ weekKey: "2026-W42", weekActive: 7 }, "2026-W43", 1);
  assert.deepEqual(c, { weekKey: "2026-W43", weekActive: 1 });
  assert.equal(L.crewWeekAdd(c, "2026-W43", 1).weekActive, 2);
});

test("challengeStep 기간·종류·인증 확인, 달성은 한 번만", () => {
  const start = Date.parse("2026-10-26T00:00:00+09:00"), end = start + 14 * 864e5;
  const ch = { kind: "run_km", start, end, target: 30, progress: 25, status: "active" };
  const at = start + 864e5;
  assert.equal(L.challengeStep(ch, { kind: "run_km", amount: 3, atMs: start - 1, verified: true }).ch.progress, 25);
  assert.equal(L.challengeStep(ch, { kind: "run_km", amount: 3, atMs: end, verified: true }).ch.progress, 25);
  assert.equal(L.challengeStep(ch, { kind: "gym_attend", amount: 1, atMs: at, verified: true }).ch.progress, 25);
  assert.equal(L.challengeStep(ch, { kind: "run_km", amount: 3, atMs: at, verified: false }).ch.progress, 25);
  const r = L.challengeStep(ch, { kind: "run_km", amount: 6, atMs: at, verified: true });
  assert.equal(r.justDone, true); assert.equal(r.ch.status, "done"); assert.equal(r.ch.progress, 31);
  const r2 = L.challengeStep(r.ch, { kind: "run_km", amount: 6, atMs: at, verified: true });
  assert.equal(r2.justDone, false); assert.equal(r2.ch.progress, 31);
  const ok = L.challengeStep(ch, { kind: "run_km", amount: 1, atMs: at, verified: true });
  assert.equal(ok.justDone, false); assert.equal(ok.ch.progress, 26);
});

test("newMilestones", () => {
  assert.deepEqual(L.newMilestones(90, 120, []), [100]);
  assert.deepEqual(L.newMilestones(450, 1200, [100]), [500, 1000]);
  assert.deepEqual(L.newMilestones(120, 130, [100]), []);
  assert.deepEqual(L.newMilestones(90, 120, [100]), []);
});

test("matchHealth 손 입력 제외, 거리 3% 안이면 인증", () => {
  const run = { runDay: "20261019", km: 5.02, sec: 1531 };
  const t0 = Date.parse("2026-10-19T07:00:00+09:00");
  const w = { start: t0, end: t0 + 1600e3, km: 5.0, app: "com.strava", userEntered: false };
  assert.equal(L.matchHealth(run, [Object.assign({}, w, { userEntered: true })]).ok, false);
  const m = L.matchHealth(run, [w]);
  assert.equal(m.ok, true); assert.equal(m.source.app, "com.strava");
  assert.equal(L.matchHealth(run, [Object.assign({}, w, { km: 4.6 })]).ok, false);
  assert.equal(L.matchHealth(run, [Object.assign({}, w, { start: t0 - 864e5, end: t0 - 864e5 + 1600e3 })]).ok, false);
  assert.equal(L.matchHealth(run, []).ok, false);
});

test("duelScore 참여율 50 + 1인당 평균 50", () => {
  const s = L.duelScore({ members: 10, active: 5, total: 25 }, { members: 20, active: 20, total: 100 });
  assert.deepEqual(s, { a: 50, b: 100 });
  assert.deepEqual(L.duelScore({ members: 0, active: 0, total: 0 }, { members: 0, active: 0, total: 0 }), { a: 0, b: 0 });
});
