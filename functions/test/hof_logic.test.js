// 명예의 전당 서버 집계 — 앱 window._hofRank 식을 그대로 옮긴 것인지 확인
const test = require("node:test");
const assert = require("node:assert");
const H = require("../hof_logic.js");

const NOW = Date.UTC(2026, 9, 31, 16, 0);   // 2026-11-01 01:00 KST — 서버(UTC)는 아직 10월, 한국은 11월
const M = "2026-11";
const u = (uid, o) => Object.assign({ uid, nickname: "n" + uid }, o);
const fe = (n) => ({ monthly: { [M]: { feed: n } } });

test("kstMonthKey: 한국 시각으로 달을 정한다", () => {
  assert.strictEqual(H.kstMonthKey(NOW), "2026-11");
  assert.strictEqual(H.kstMonthKey(Date.UTC(2026, 9, 31, 14, 59)), "2026-10");
});

test("rank: 0회·탈퇴·익명·닉네임 없음·제외 uid 는 빠진다", () => {
  const rows = H.rank([
    u("a", fe(3)), u("b", fe(0)), u("c", Object.assign(fe(5), { deleted: true })),
    u("d", Object.assign(fe(5), { isAnonymous: true })), Object.assign(fe(4), { uid: "e" }),
    u("3ojRNNyRutYE4IDQn2GrJDcXz0Q2", fe(99)),
  ], "feed", M);
  assert.deepStrictEqual(rows.map((r) => r.uid), ["a"]);
});

test("rank: 많은 순, 동점은 닉네임 가나다순, rank 는 1부터", () => {
  const rows = H.rank([
    u("x", Object.assign(fe(2), { nickname: "다람쥐" })), u("y", Object.assign(fe(5), { nickname: "호랑이" })),
    u("z", Object.assign(fe(2), { nickname: "가오리" })),
  ], "feed", M);
  assert.deepStrictEqual(rows.map((r) => [r.nick, r.n, r.rank]), [["호랑이", 5, 1], ["가오리", 2, 2], ["다람쥐", 2, 3]]);
});

test("rank: 지난달 수는 세지 않는다", () => {
  assert.strictEqual(H.rank([u("a", { monthly: { "2026-10": { feed: 9 } } })], "feed", M).length, 0);
});

test("host: 누적 hosted 로 세고 완료 횟수는 sub", () => {
  const rows = H.rank([u("a", { hostStats: { hosted: 4, completed: 2 } }), u("b", { hostStats: { hosted: 1 } })], "host", M);
  assert.deepStrictEqual(rows.map((r) => [r.uid, r.n, r.sub]), [["a", 4, "완료 2회"], ["b", 1, ""]]);
});

test("attend 는 monthly.squad, checkin 은 monthly.checkin", () => {
  const us = [u("a", { monthly: { [M]: { squad: 3, checkin: 1 } } })];
  assert.strictEqual(H.rank(us, "attend", M)[0].n, 3);
  assert.strictEqual(H.rank(us, "checkin", M)[0].n, 1);
});

test("computeHofFrom: 네 종목 + 각 1위의 커마·한마디만 담는다", () => {
  const r = H.computeHofFrom([
    u("a", Object.assign(fe(3), { character: { body: "b1" }, hofMsg: "가자", characterSheet: "s.png" })),
    u("b", Object.assign(fe(1), { character: { body: "b2" }, hofMsg: "비밀" })),
  ], NOW);
  assert.strictEqual(r.month, "2026-11");
  assert.deepStrictEqual(Object.keys(r.rows).sort(), ["attend", "checkin", "feed", "host"]);
  assert.deepStrictEqual(Object.keys(r.top), ["a"]);
  assert.strictEqual(r.top.a.hofMsg, "가자");
  assert.strictEqual(r.top.a.characterSheet, "s.png");
});
