// 푸시 토큰 비공개(11-02) — 두 곳 읽기·지우기·한 번 옮기기를 메모리 가짜 Firestore 로 확인한다(실서비스 접속 없음)
const test = require("node:test");
const assert = require("node:assert");
const Module = require("node:module");

// ── 가짜 firebase-admin/firestore: doc get/set(merge)·batch·where(==, !=)·arrayUnion/arrayRemove 만 ──
const store = new Map();
const AU = (v) => ({ __op: "union", v }), AR = (v) => ({ __op: "remove", v });
const apply = (cur, val) => {
  if (val && val.__op === "union") { const a = Array.isArray(cur) ? cur.slice() : []; val.v.forEach((x) => { if (!a.includes(x)) a.push(x); }); return a; }
  if (val && val.__op === "remove") return (Array.isArray(cur) ? cur : []).filter((x) => !val.v.includes(x));
  if (val && val.__op === "ts") return "TS";
  return val;
};
const setDoc = (path, data, opt) => {
  const base = opt && opt.merge ? Object.assign({}, store.get(path) || {}) : {};
  Object.keys(data).forEach((k) => { base[k] = apply(base[k], data[k]); });
  store.set(path, base);
};
const docRef = (path) => ({
  path,
  get: async () => ({ exists: store.has(path), data: () => store.get(path), id: path.split("/").pop() }),
  set: async (d, o) => setDoc(path, d, o),
});
const fakeDb = {
  doc: docRef,
  batch: () => { const ops = []; return { set: (r, d, o) => ops.push([r.path, d, o]), commit: async () => ops.forEach((o) => setDoc(...o)) }; },
  collection: (name) => ({
    where: (f, op, v) => ({
      get: async () => {
        const docs = [];
        store.forEach((d, p) => {
          const seg = p.split("/"); if (seg.length !== 2 || seg[0] !== name) return;
          if (!(f in d)) return;   // Firestore: 칸이 없으면 == · != 둘 다 안 걸린다
          const hit = op === "==" ? JSON.stringify(d[f]) === JSON.stringify(v) : JSON.stringify(d[f]) !== JSON.stringify(v);
          if (hit) docs.push({ id: seg[1], data: () => d });
        });
        return { docs, size: docs.length, forEach: (fn) => docs.forEach(fn) };
      },
    }),
  }),
};
const origLoad = Module._load;
Module._load = function (req, ...rest) {
  if (req === "firebase-admin/firestore") return { getFirestore: () => fakeDb, FieldValue: { arrayUnion: (...v) => AU(v), arrayRemove: (...v) => AR(v), serverTimestamp: () => ({ __op: "ts" }) } };
  return origLoad.call(this, req, ...rest);
};
const PT = require("../pushtokens.js");
const reset = (o) => { store.clear(); Object.keys(o).forEach((k) => store.set(k, JSON.parse(JSON.stringify(o[k])))); };

test("mergeTokens: 옛 칸 먼저·새 자리 뒤, 빈 값·중복 제거", () => {
  assert.deepStrictEqual(PT.mergeTokens(["b", "c", ""], ["a", "b", null]), ["a", "b", "c"]);
  assert.deepStrictEqual(PT.mergeTokens(undefined, undefined), []);
});

test("readTokens: 옮기는 동안 두 곳을 합쳐 읽는다", async () => {
  reset({ "users/u1": { fcmTokens: ["old"] }, "users/u1/private/push": { tokens: ["new"] } });
  assert.deepStrictEqual((await PT.readTokens("u1")).tokens, ["old", "new"]);
  reset({ "users/u2": { nickname: "x" } });
  assert.deepStrictEqual((await PT.readTokens("u2")).tokens, []);
});

test("removeTokens: 두 곳에서 지우고 남은 게 없으면 pushOn 끔", async () => {
  reset({ "users/u1": { fcmTokens: ["a"], pushOn: true }, "users/u1/private/push": { tokens: ["b"] } });
  await PT.removeTokens("u1", ["a"]);
  assert.strictEqual(store.get("users/u1").pushOn, true);       // b 가 남아 있다
  await PT.removeTokens("u1", ["b"]);
  assert.deepStrictEqual(store.get("users/u1").fcmTokens, []);
  assert.deepStrictEqual(store.get("users/u1/private/push").tokens, []);
  assert.strictEqual(store.get("users/u1").pushOn, false);
});

test("migrateAll: 옛 칸을 새 자리로 옮기고 옛 칸은 빈 배열로(지우지 않음), 두 번째는 0명", async () => {
  reset({
    "users/a": { fcmTokens: ["t1", "t2"], nickname: "A" },
    "users/b": { fcmTokens: [] },
    "users/c": { nickname: "C" },
    "users/d": { fcmTokens: ["t3"] }, "users/d/private/push": { tokens: ["t4"] },
  });
  const r = await PT.migrateAll();
  assert.deepStrictEqual(r, { scanned: 2, moved: 2, tokens: 3 });
  assert.deepStrictEqual(store.get("users/a/private/push").tokens, ["t1", "t2"]);
  assert.deepStrictEqual(store.get("users/a").fcmTokens, []);
  assert.strictEqual(store.get("users/a").pushOn, true);
  assert.strictEqual(store.get("users/a").nickname, "A");         // 다른 칸은 그대로
  assert.deepStrictEqual(store.get("users/d/private/push").tokens, ["t4", "t3"]);   // 이미 있던 새 토큰도 유지
  assert.ok(!store.has("users/c/private/push"));
  assert.deepStrictEqual(await PT.migrateAll(), { scanned: 0, moved: 0, tokens: 0 });
  assert.deepStrictEqual((await PT.readTokens("a")).tokens, ["t1", "t2"]);   // 옮긴 뒤에도 보내는 쪽이 그대로 찾는다
});

test("pushableUsers: pushOn·옛 칸 둘 다, 겹치면 한 번, 탈퇴자 제외", async () => {
  reset({
    "users/a": { pushOn: true, fcmTokens: [] },
    "users/b": { fcmTokens: ["x"] },
    "users/c": { pushOn: true, fcmTokens: ["y"] },
    "users/d": { pushOn: true, deleted: true },
    "users/e": { pushOn: false },
  });
  assert.deepStrictEqual((await PT.pushableUsers()).map((u) => u.uid).sort(), ["a", "b", "c"]);
});

test("migrateBumpDiag: 옛 진단을 새 자리로(새 기록이 앞, 5건까지), 옛 칸은 빈 배열", async () => {
  reset({
    "users/a": { bumpDiag: [{ n: 1 }, { n: 2 }, { n: 3 }], nickname: "A" },
    "users/a/private/bumpDiag": { recs: [{ n: 9 }, { n: 8 }, { n: 7 }] },
    "users/b": { bumpDiag: [{ n: 5 }] },
    "users/c": { bumpDiag: [] },
  });
  assert.deepStrictEqual(await PT.migrateBumpDiag(), { scanned: 2, moved: 2 });
  assert.deepStrictEqual(store.get("users/a/private/bumpDiag").recs.map((r) => r.n), [9, 8, 7, 1, 2]);
  assert.deepStrictEqual(store.get("users/a").bumpDiag, []);
  assert.strictEqual(store.get("users/a").nickname, "A");
  assert.deepStrictEqual(store.get("users/b/private/bumpDiag").recs, [{ n: 5 }]);
  assert.deepStrictEqual(await PT.migrateBumpDiag(), { scanned: 0, moved: 0 });
});
