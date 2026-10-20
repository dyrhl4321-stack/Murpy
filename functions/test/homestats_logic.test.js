// 홈 "오늘 n명 운동" 하루 집계 — 날짜 경계(자정 KST)·고유 인원·최근 사진 3장
const test = require("node:test");
const assert = require("node:assert");
const H = require("../homestats_logic.js");

const KST = (y, m, d, hh, mm) => Date.UTC(y, m - 1, d, hh - 9, mm || 0);

test("dayKey: 자정 KST 경계 — 23:59 는 그날, 00:00 은 다음날", () => {
  assert.strictEqual(H.dayKey(KST(2026, 10, 20, 23, 59)), "20261020");
  assert.strictEqual(H.dayKey(KST(2026, 10, 21, 0, 0)), "20261021");
  assert.strictEqual(H.dayKey(KST(2026, 10, 21, 8, 59)), "20261021");   // UTC 로는 아직 20일 23:59
});

test("dayRange: 그날 0시~다음날 0시(KST) ms", () => {
  const [a, b] = H.dayRange("20261020");
  assert.strictEqual(a, KST(2026, 10, 20, 0, 0));
  assert.strictEqual(b, KST(2026, 10, 21, 0, 0));
});

test("lastKeys: 오늘 포함 n일, 최신이 먼저", () => {
  assert.deepStrictEqual(H.lastKeys(KST(2026, 11, 1, 1, 0), 3), ["20261101", "20261031", "20261030"]);
});

test("aggregate: 최신순 글에서 고유 인원, 사진은 서로 다른 사람 최근 3명", () => {
  const posts = [
    { userId: "a", userPhoto: "pa" }, { userId: "b", userPhoto: "pb" }, { userId: "a", userPhoto: "pa2" },
    { userId: "", userPhoto: "x" }, { userId: "c" }, { userId: "d", userPhoto: "pd" },
  ];
  const r = H.aggregate(posts);
  assert.strictEqual(r.n, 4);
  assert.deepStrictEqual(r.uids, ["a", "b", "c", "d"]);
  assert.deepStrictEqual(r.recent, [{ uid: "a", photo: "pa" }, { uid: "b", photo: "pb" }, { uid: "c", photo: "" }]);
});

test("aggregate: 글 없음 = 0명", () => {
  assert.deepStrictEqual(H.aggregate([]), { n: 0, uids: [], recent: [] });
});
