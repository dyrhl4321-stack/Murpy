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
  assert.equal(c({ dateISO: "2026-10-22" }), "bad_date");  // 미래 날짜
  assert.equal(c({ km: null }), "unreadable");
  assert.equal(c({ sec: null, paceSec: null }), "unreadable");
  assert.equal(L.checkCard(null, { nowMs: NOW }).why, "unreadable");
});

// 대표 10-19 "그날 당일만 가능하게, 전 거는 안 됨"
test("checkCard 당일 기록만 — 카드 날짜", () => {
  const c = (o, now) => L.checkCard(Object.assign({ isRunCard: true, km: 5, sec: 1500, paceSec: 300 }, o), { nowMs: now || NOW });
  assert.equal(c({ dateISO: "2026-10-19" }).ok, true);
  assert.equal(c({ dateISO: "2026-10-18" }).why, "not_today");          // 어제
  assert.equal(c({ dateISO: "2026-10-12" }).why, "not_today");          // 지난주
  // 새벽 0~5시: 하루 경계(5시) 전이라 '오늘'은 어제 날짜지만, 카드에 찍힌 달력 날짜(오늘)도 받는다
  const dawn = Date.parse("2026-10-20T00:30:00+09:00");
  assert.equal(c({ dateISO: "2026-10-20" }, dawn).ok, true);
  assert.equal(c({ dateISO: "2026-10-19" }, dawn).ok, true);            // 어젯밤 11시 반에 뛴 것
  assert.equal(c({ dateISO: "2026-10-18" }, dawn).why, "not_today");
});

test("checkCard 당일 기록만 — 카드에 날짜가 없으면 사진 촬영 시각", () => {
  const c = (shotMs) => L.checkCard({ isRunCard: true, km: 5, sec: 1500, paceSec: 300, dateISO: null }, { nowMs: NOW, shotMs });
  assert.equal(c(Date.parse("2026-10-19T08:10:00+09:00")).ok, true);
  assert.equal(c(Date.parse("2026-10-18T20:00:00+09:00")).why, "not_today");
  const r = c(null);                                   // 촬영 시각도 없으면 올린 시각(오늘)
  assert.equal(r.ok, true); assert.equal(r.run.runDay, "20261019"); assert.equal(r.run.dayFromCard, false);
  assert.equal(c(Date.parse("2026-10-30T08:00:00+09:00")).ok, true);   // 미래 촬영 시각(기기 시계 틀림)은 믿지 않고 올린 시각
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

test("storagePathOf 는 우리 버킷의 내 폴더만", () => {
  const B = "murpyprototype.firebasestorage.app";
  const u = (b, p) => `https://firebasestorage.googleapis.com/v0/b/${b}/o/${encodeURIComponent(p)}?alt=media&token=x`;
  assert.equal(L.storagePathOf(u(B, "uploads/U1/run_1.jpg"), "U1", B), "uploads/U1/run_1.jpg");
  assert.equal(L.storagePathOf(u(B, "uploads/U2/run_1.jpg"), "U1", B), null);
  assert.equal(L.storagePathOf(u("evil.appspot.com", "uploads/U1/a.jpg"), "U1", B), null);
  assert.equal(L.storagePathOf(u(B, "uploads/U1/../U2/a.jpg"), "U1", B), null);
  assert.equal(L.storagePathOf("https://evil.com/v0/b/" + B + "/o/uploads%2FU1%2Fa.jpg", "U1", B), null);
  assert.equal(L.storagePathOf("not a url", "U1", B), null);
});

// ── 리뷰 수정(10-19) ──
test("checkinDay: 문서 id 모양과 서버 날짜가 맞는 것만", () => {
  const t = Date.parse("2026-10-19T09:30:00+09:00");
  assert.equal(L.checkinDay("U1_c9_20261019", { uid: "U1", centerId: "c9", day: "20261019" }, t), "20261019");
  assert.equal(L.checkinDay("U1_c9_20261019", { uid: "U1", centerId: "c9", day: "20261019" }, Date.parse("2026-10-20T00:20:00+09:00")), "20261019"); // 자정 직후 하루 여유
  assert.equal(L.checkinDay("U1_c9_20260801", { uid: "U1", centerId: "c9", day: "20260801" }, t), null);   // 지난 날짜 위조
  assert.equal(L.checkinDay("U1_x_7", { uid: "U1", centerId: "c9", day: "20261019" }, t), null);          // id 모양 다름
  assert.equal(L.checkinDay("U1_c9_20261019", { uid: "U2", centerId: "c9", day: "20261019" }, t), null);
});

test("runAtMs 는 기록한 날 한낮(한국 시간) — 올린 시각이 아니다", () => {
  assert.equal(L.runAtMs("20261019"), Date.parse("2026-10-19T12:00:00+09:00"));
});

test("isDupRun: 시간 줄을 잘라 페이스로 되살린 재업로드도 잡는다", () => {
  const orig = { runDay: "20261019", km: 10.03, sec: 3318, paceSec: 331 };
  const cropped = { runDay: "20261019", km: 10.03, sec: Math.round(10.03 * 331), paceSec: 331 };   // 3320
  assert.equal(L.isDupRun(cropped, [orig]), true);
  assert.equal(L.isDupRun({ runDay: "20261019", km: 10.03, sec: 3500, paceSec: 349 }, [orig]), false);
});

// ── 챌린지 목표 인원 = 최근 2주 안에 운동한 멤버(대표 10-19) ──
test("markActive 는 더 최근 날짜만 남긴다", () => {
  assert.equal(L.markActive({}, "20261019").lastActiveDay, "20261019");
  assert.equal(L.markActive({ lastActiveDay: "20261019" }, "20261012").lastActiveDay, "20261019");
});

test("activeHeadcount: 최근 14일 안에 운동한 사람만, 최소 3명", () => {
  const ms = [
    { lastActiveDay: "20261019" }, { lastActiveDay: "20261006" }, { lastActiveDay: "20261005" },
    { lastActiveDay: "20260901" }, {}, { lastActiveDay: "20261018", left: true },
  ];
  assert.equal(L.activeHeadcount(ms, "20261019"), 3);          // 19·06 → 2명이지만 최소 3
  const many = Array.from({ length: 63 }, () => ({ lastActiveDay: "20261015" })).concat(Array.from({ length: 184 }, () => ({})));
  assert.equal(L.activeHeadcount(many, "20261019"), 63);
  assert.equal(L.activeHeadcount([], "20261019"), 3);
});

// ── 챌린지 보상 = 함께 달성 300(기간 중 운동한 사람만) + 내 목표 200(개인, 크루 실패해도) — 대표 10-19 ──
test("memberChallengeStep: 기간 안 활동 표시 + 같은 종류·인증만 개인 진행", () => {
  const start = Date.parse("2026-10-26T00:00:00+09:00"), end = start + 14 * 864e5, at = start + 864e5;
  const ch = { id: "c1", kind: "run_km", start, end, perHead: 15, status: "active" };
  let m = L.memberChallengeStep({}, ch, { kind: "run_km", amount: 5, atMs: at, verified: false });
  assert.equal(m.chAct.c1, true); assert.equal((m.ch || {}).c1 || 0, 0);            // 미인증 = 활동만
  m = L.memberChallengeStep(m, ch, { kind: "run_km", amount: 5.5, atMs: at, verified: true });
  assert.equal(m.ch.c1, 5.5);
  m = L.memberChallengeStep(m, Object.assign({}, ch, { status: "done" }), { kind: "run_km", amount: 10, atMs: at, verified: true });
  assert.equal(m.ch.c1, 15.5);                                                     // 크루가 먼저 달성해도 개인 진행은 계속
  const g = L.memberChallengeStep({}, ch, { kind: "gym_attend", amount: 1, atMs: at, verified: true });
  assert.equal(g.chAct.c1, true); assert.equal((g.ch || {}).c1 || 0, 0);           // 다른 종류 = 활동만
  const out = L.memberChallengeStep({}, ch, { kind: "run_km", amount: 5, atMs: end + 1, verified: true });
  assert.deepEqual(out, {});                                                        // 기간 밖 = 아무것도
});

test("settleChallenge: 함께 300(활동한 사람만, 달성 때만) + 내 목표 200(실패해도)", () => {
  const ch = { id: "c1", perHead: 15, status: "done" };
  const ms = [
    { uid: "a", chAct: { c1: true }, ch: { c1: 16 } },
    { uid: "b", chAct: { c1: true }, ch: { c1: 3 } },
    { uid: "c" },
    { uid: "d", chAct: { c1: true }, ch: { c1: 15 }, left: true },
  ];
  assert.deepEqual(L.settleChallenge(ch, ms), [
    { uid: "a", amount: 300, key: "c1_g" }, { uid: "a", amount: 200, key: "c1_i" },
    { uid: "b", amount: 300, key: "c1_g" },
  ]);
  assert.deepEqual(L.settleChallenge(Object.assign({}, ch, { status: "failed" }), ms), [{ uid: "a", amount: 200, key: "c1_i" }]);
});

test("parseOcr: 숫자 자리 네모(0~1000) 정리, 이상한 값은 버림", () => {
  const o = L.parseOcr(JSON.stringify({ isRunCard: true, km: 5, sec: 1500, boxes: { km: [100, 50, 200, 400], pace: [100, 500, 200, 1200], date: "x" } }));
  assert.deepEqual(o.boxes, { km: [100, 50, 200, 400], pace: [100, 500, 200, 1000] });
  assert.equal(L.parseOcr(JSON.stringify({ isRunCard: true, km: 5, sec: 1500 })).boxes, undefined);
});
