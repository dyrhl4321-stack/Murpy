// 홈 "지금 인기" 서버 집계 — 앱 loadHomeTrending 의 계산식을 그대로 옮긴 것인지 확인
const test = require("node:test");
const assert = require("node:assert");
const T = require("../hometrending_logic.js");

const NOW = Date.UTC(2026, 9, 21, 3, 0);   // 2026-10-21 12:00 KST
const u = (uid, o) => Object.assign({ uid, nickname: "n" + uid }, o);
const dressed = (n) => {
  const slots = ["bottom", "shoes", "top", "hair", "hat", "acc", "mask"], c = Object.assign({}, T.CHAR_DEFAULT);
  slots.slice(0, n).forEach((k) => { c[k] = "x_" + k; });
  return c;
};

test("dressedN: 기본 의상과 다른 칸만 센다", () => {
  assert.strictEqual(T.dressedN(null), 0);
  assert.strictEqual(T.dressedN(Object.assign({}, T.CHAR_DEFAULT)), 0);
  assert.strictEqual(T.dressedN(dressed(3)), 3);
});

test("baseUsers: 닉네임 없음·탈퇴·제외 uid 는 빠진다", () => {
  const list = T.baseUsers([u("a"), u("b", { nickname: "" }), u("c", { deleted: true }), u(T.EXCLUDE_UID[0])]);
  assert.deepStrictEqual(list.map((x) => x.uid), ["a"]);
});

test("charCandidates: 갖춰 입은 사람만, 점수순 상위 20, 같은 점수는 uid 순", () => {
  const users = [];
  for (let i = 0; i < 25; i++) users.push(u("u" + String(i).padStart(2, "0"), { character: dressed(i % 4 + 1) }));
  const c = T.charCandidates(T.baseUsers(users), NOW);
  assert.strictEqual(c.length, 20);
  assert.ok(c.every((x) => T.dressedN(x.character) > 0));
  assert.strictEqual(c[0].uid, "u03");   // 4칸 중 uid 가 가장 앞
});

test("charPool: 좋아요를 넣어 다시 줄 세우고 5명", () => {
  const cands = [u("a", { character: dressed(1) }), u("b", { character: dressed(3) }), u("c", { character: dressed(2) })];
  const pool = T.charPool(cands, { a: 100, b: 0, c: 0 }, NOW, 5);
  assert.deepStrictEqual(pool.map((x) => x.u.uid), ["a", "b", "c"]);
  assert.strictEqual(pool[0].like, 100);
});

test("freshBonus: 14일 안의 꾸미기는 최대 2점, 넘으면 0", () => {
  assert.strictEqual(T.freshBonus({ characterUpdatedAt: NOW }, NOW), 2);
  assert.strictEqual(T.freshBonus({ characterUpdatedAt: NOW - 15 * 864e5 }, NOW), 0);
  assert.strictEqual(T.freshBonus({}, NOW), 0);
});

test("pickFeatured: 날짜 해시로 하루 한 명 고정(앱과 같은 해시)", () => {
  const pool = [{ u: { uid: "a" } }, { u: { uid: "b" } }, { u: { uid: "c" } }];
  let h = 0; const k = "20261021";
  for (let i = 0; i < k.length; i++) h = ((h * 31) + k.charCodeAt(i)) >>> 0;
  assert.strictEqual(T.pickFeatured(pool, k), pool[h % 3]);
  assert.strictEqual(T.pickFeatured([], k), null);
});

test("roomTop: 가구 수로 후보, 좋아요×3+방문+가구 로 1등", () => {
  const f = (n) => ({ f: Array.from({ length: n }, () => ({})) });
  const users = T.baseUsers([u("a", { room: f(5) }), u("b", { room: f(2) }), u("c", { room: f(0) })]);
  const cands = T.roomCandidates(users);
  assert.deepStrictEqual(cands.map((x) => x.uid), ["a", "b"]);
  const top = T.roomTop(cands, { a: 0, b: 2 }, { a: 0, b: 0 });
  assert.strictEqual(top.u.uid, "b");   // 2×3+2 = 8 > 5
});

test("runners: 사진·닉네임·연속 2일 이상, 연속일 많은 순", () => {
  const list = T.runners(T.baseUsers([
    u("a", { photoURL: "p", streak: 3 }), u("b", { photoURL: "p", streak: 9 }),
    u("c", { streak: 9 }), u("d", { firestorePhotoURL: "p", streak: 1 }), u("e", { firestorePhotoURL: "p", streak: 5 }),
  ]), 3);
  assert.deepStrictEqual(list.map((x) => x.uid), ["b", "e", "a"]);
});

test("kstDayKey: 앱 mwTodayKey 와 같은 YYYYMMDD(KST)", () => {
  assert.strictEqual(T.kstDayKey(Date.UTC(2026, 9, 20, 15, 0)), "20261021");   // 10-21 00:00 KST
  assert.strictEqual(T.kstDayKey(Date.UTC(2026, 9, 20, 14, 59)), "20261020");
});

test("checkinOrder: 앱과 같이 centerId 를 세서 많은 순(동점은 처음 나온 순)", () => {
  const docs = [{ centerId: "b" }, { centerId: "a" }, { centerId: "b" }, {}, { centerId: "c" }, { centerId: "a" }];
  assert.deepStrictEqual(T.checkinOrder(docs), [["b", 2], ["a", 2], ["c", 1]]);
  assert.deepStrictEqual(T.checkinOrder([]), []);
});
