// ────────────────────────────────────────────────────────────
// ★11-02 푸시 토큰 비공개 — users/{uid}.fcmTokens(손님도 읽는 공개 문서) → users/{uid}/private/push.tokens(본인·서버만)
//   공개 문서에는 '알림 켬' 표시 users.pushOn(불리언)만 남긴다 — 방 부르기 안내·리텐션 대상 고르기가 이걸 본다.
//   옮기는 동안(새 앱이 다 퍼지고 pushMigrateOnce 가 돌 때까지) 보내는 쪽은 **두 곳을 다** 읽고 지울 때도 두 곳에서 지운다.
//   옛 칸 fcmTokens 는 지우지 않고 빈 배열로 둔다(대표·브랜딩 11-02).
// ────────────────────────────────────────────────────────────
const { getFirestore, FieldValue } = require("firebase-admin/firestore");

const db = () => getFirestore();
const pushRef = (uid) => db().doc("users/" + uid + "/private/push");
const userRef = (uid) => db().doc("users/" + uid);

// 두 곳의 토큰을 합친다. 옛 칸을 먼저, 새 자리를 뒤에 — 기기당 하나만 남길 때(sendNotifPush) 뒤쪽이 이기므로
// 같은 기기라면 새 자리(앱이 최근에 올린 것)가 남는다. 빈 값·중복은 뺀다.
function mergeTokens(privateTokens, legacyTokens) {
  const out = [];
  const seen = new Set();
  [].concat(Array.isArray(legacyTokens) ? legacyTokens : [], Array.isArray(privateTokens) ? privateTokens : [])
    .forEach((t) => {
      const s = typeof t === "string" ? t.trim() : "";
      if (!s || seen.has(s)) return;
      seen.add(s); out.push(s);
    });
  return out;
}

async function readTokens(uid) {
  const [u, p] = await Promise.all([userRef(uid).get(), pushRef(uid).get()]);
  const ud = (u.exists && u.data()) || {};
  const pd = (p.exists && p.data()) || {};
  return { tokens: mergeTokens(pd.tokens, ud.fcmTokens), deleted: !!ud.deleted };
}

// 만료·무효 토큰을 두 곳에서 지우고, 남은 게 없으면 pushOn 을 끈다.
async function removeTokens(uid, invalid) {
  if (!invalid || !invalid.length) return;
  const b = db().batch();
  b.set(pushRef(uid), { tokens: FieldValue.arrayRemove(...invalid) }, { merge: true });
  b.set(userRef(uid), { fcmTokens: FieldValue.arrayRemove(...invalid) }, { merge: true });
  await b.commit();
  const left = await readTokens(uid);
  await userRef(uid).set({ pushOn: left.tokens.length > 0 }, { merge: true });
}

// 한 사람 옮기기 — 새 자리에 더하고 옛 칸을 비우는 것을 한 배치로(중간에 끊겨도 토큰이 사라지는 순간이 없다).
function migrateOne(batch, uid, legacyTokens) {
  const toks = mergeTokens([], legacyTokens);
  if (!toks.length) return false;
  batch.set(pushRef(uid), { tokens: FieldValue.arrayUnion(...toks), migratedAt: FieldValue.serverTimestamp() }, { merge: true });
  batch.set(userRef(uid), { fcmTokens: [], pushOn: true }, { merge: true });
  return true;
}

// 옛 칸에 토큰이 남은 사람 전부 — 한 번에 400명씩 배치. 여러 번 돌려도 같다(두 번째부터는 0명).
async function migrateAll() {
  const qs = await db().collection("users").where("fcmTokens", "!=", []).get();
  let moved = 0, tokens = 0;
  for (let i = 0; i < qs.docs.length; i += 400) {
    const b = db().batch();
    qs.docs.slice(i, i + 400).forEach((d) => {
      const t = (d.data() || {}).fcmTokens;
      if (migrateOne(b, d.id, t)) { moved++; tokens += mergeTokens([], t).length; }
    });
    await b.commit();
  }
  return { scanned: qs.size, moved, tokens };
}

// 리텐션 대상 — 새 표시(pushOn)와 옛 칸 둘 다(옮기는 동안). 탈퇴자 제외.
async function pushableUsers() {
  const [a, b] = await Promise.all([
    db().collection("users").where("pushOn", "==", true).get(),
    db().collection("users").where("fcmTokens", "!=", []).get(),
  ]);
  const byId = new Map();
  [a, b].forEach((qs) => qs.forEach((d) => {
    const u = d.data() || {};
    if (u.deleted) return;
    byId.set(d.id, Object.assign({ uid: d.id }, u));
  }));
  return Array.from(byId.values());
}

// ── ★11-02 bumpDiag(범프 진단 최근 5건)도 같은 방식 — users 문서(전원 읽기의 13%)에서 users/{uid}/private/bumpDiag.recs 로.
//   새 앱은 private 에만 쓴다. 옛 칸은 지우지 않고 빈 배열로 둔다. 이미 새 자리에 쓴 기록이 있으면 그게 앞(최신), 옛 것은 뒤, 5건까지.
async function migrateBumpDiag() {
  const qs = await db().collection("users").where("bumpDiag", "!=", []).get();
  let moved = 0;
  for (let i = 0; i < qs.docs.length; i += 200) {
    const part = qs.docs.slice(i, i + 200);
    const privs = await Promise.all(part.map((d) => db().doc("users/" + d.id + "/private/bumpDiag").get()));
    const b = db().batch();
    part.forEach((d, k) => {
      const legacy = (d.data() || {}).bumpDiag;
      if (!Array.isArray(legacy) || !legacy.length) return;
      const cur = (privs[k].exists && privs[k].data().recs) || [];
      b.set(db().doc("users/" + d.id + "/private/bumpDiag"), { recs: cur.concat(legacy).slice(0, 5), movedAt: FieldValue.serverTimestamp() }, { merge: true });
      b.set(userRef(d.id), { bumpDiag: [] }, { merge: true });
      moved++;
    });
    await b.commit();
  }
  return { scanned: qs.size, moved };
}

module.exports = { mergeTokens, readTokens, removeTokens, migrateOne, migrateAll, pushableUsers, migrateBumpDiag };
