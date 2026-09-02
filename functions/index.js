// notifications 컬렉션에 새 문서가 생기면, 받는 사람(toUid)의 기기로 FCM 푸시 전송
const { onDocumentCreated } = require("firebase-functions/v2/firestore");
const { initializeApp } = require("firebase-admin/app");
const { getFirestore, FieldValue } = require("firebase-admin/firestore");
const { getMessaging } = require("firebase-admin/messaging");

initializeApp();

// ─────────────────────────────────────────────────────────────────────────────
// 알림 문구
//
// ★타입이 여기 없으면 "머피 / 새 알림이 있어요" 라는 밋밋한 기본값으로 떨어진다.
//   실제로 room_visit·poke·squad_invite 가 빠져 있어서 그렇게 떴다(대표 8-14).
//   **앱에 새 알림 타입을 추가하면 여기에도 반드시 한 줄 추가할 것.**
//
// ★푸시 알림은 OS 가 그리는 영역이라 우리 SVG 아이콘을 못 쓴다.
//   그래서 여기서만 이모지를 허용한다(앱 UI 의 이모지 금지 규칙과 별개, 대표 8-14 승인).
//
// 쓸 수 있는 값: n.fromNickname / n.postText / n.text
// ─────────────────────────────────────────────────────────────────────────────
const cut = (s, n) => {
  const t = String(s || "").replace(/\s+/g, " ").trim();
  return t.length > n ? t.slice(0, n) + "…" : t;
};

function compose(n) {
  const who = n.fromNickname || "누군가";
  const post = cut(n.postText, 18);

  switch (n.type) {
    // ── 매칭 ────────────────────────────────────────────────
    case "match":
      return { title: "🎉 매칭 성공!",
               body: `${who}님과 연결됐어요. 첫 마디를 건네볼까요?` };

    case "bamboo_match_request":
      return { title: "💚 매칭을 원해요",
               body: "대숲에서 만난 그분이 매칭을 신청했어요" };

    case "bamboo_match_accept":
      return { title: "🎉 매칭 성공!",
               body: `${who}님이 수락했어요. 이제 프로필이 보여요` };

    // ── 피드 ────────────────────────────────────────────────
    case "feed_like":
      return { title: `❤️ ${who}님이 좋아해요`,
               body: "오늘의 운동 인증에 마음을 남겼어요" };

    case "feed_comment":
      return { title: `💬 ${who}님의 댓글`,
               body: cut(n.commentText || n.text, 40) || "내 인증글에 댓글이 달렸어요" };

    // ── 대나무숲 ─────────────────────────────────────────────
    case "bamboo_request":
      return { title: "🎋 저에요!",
               body: post ? `"${post}" 글에 신청이 왔어요`
                          : "내 대숲 글에 누군가 손을 들었어요" };

    case "bamboo_comment":
      return { title: "🎋 익명 댓글",
               body: "내 대숲 글에 조용히 답이 달렸어요" };

    // ── 대화 ────────────────────────────────────────────────
    case "chat":
      return { title: who, body: cut(n.text, 50) || "메시지를 보냈어요" };

    // ── 머피월드 ─────────────────────────────────────────────
    case "room_visit":
      return { title: "🏠 손님이 다녀갔어요",
               body: `${who}님이 내 방에 발자국을 남겼어요` };

    case "poke":
      return { title: "👋 콕!",
               body: `${who}님이 나를 콕 찔렀어요` };

    case "room_knock":
      return { title: "🚪 똑똑, 노크가 왔어요",
               body: `${who}님이 내 머피룸 앞에 와 있어요` };

    case "room_invite":
      return { title: "🔑 문이 열렸어요",
               body: `${who}님이 머피룸으로 초대했어요. 지금 들어가볼까요?` };

    // ── 그림 경매 (2026-08-26) ──────────────────────────────
    // ★재입찰은 문서를 덮어쓰므로 onDocumentCreated 가 안 뛴다 = 푸시가 안 간다.
    //   **한 사람의 첫 입찰에만** 알림이 간다. 값 경쟁은 앱 화면에서 본다.
    // ★잠금화면에서는 제목 한 줄만 읽힌다 — **누가·얼마**를 제목에 넣는다.
    //   본문은 '그래서 뭘 하면 되는지' 한 마디로 끝낸다(대표 8-27: 경매 푸시 멘트 커마).
    case "art_bid":
      return { title: `🔨 ${who}님이 ${Number(n.amount || 0).toLocaleString()}머피를 불렀어요`,
               body: "내 그림 경매 · 눌러서 낙찰하거나 더 기다릴 수 있어요" };

    case "art_won":
      return { title: `🖼 ${Number(n.amount || 0).toLocaleString()}머피에 낙찰됐어요`,
               body: `${who}님의 그림이에요 · 앱을 열면 바로 가져갈 수 있어요` };

    case "art_sold":
      // 같이 그린 그림은 **판 사람과 나머지의 몫이 다르다.** 같은 문구를 쓰면
      // "내가 판 적 없는데?" 가 된다 — seller 로 갈라서 말한다.
      return (n.seller && n.toUid && n.seller === n.toUid)
        ? { title: `🪙 그림이 팔렸어요 · ${Number(n.amount || 0).toLocaleString()}머피`,
            body: `${who}님이 가져갔어요 · 머피가 들어왔어요` }
        : { title: `🪙 같이 그린 그림이 팔렸어요 · ${Number(n.amount || 0).toLocaleString()}머피`,
            body: `${who}님이 가져갔어요 · 내 몫이 들어왔어요` };

    // ── 스쿼드 ──────────────────────────────────────────────
    case "squad_invite":
      return { title: "⚡ 같이 하실래요?",
               body: post ? `${who}님이 "${post}"에 초대했어요`
                          : `${who}님이 스쿼드에 초대했어요` };

    case "crew_apply":
      return { title: "🙋 참가 신청",
               body: post ? `${who}님이 "${post}"에 신청했어요`
                          : `${who}님이 참가를 신청했어요` };

    case "crew_approved":
      return { title: "✅ 승인됐어요",
               body: post ? `"${post}" 참가가 확정됐어요. 이제 만나러 가요`
                          : "참가 신청이 승인됐어요" };

    // ── 머피 지급 ────────────────────────────────────────────
    // ★대표 8-14: "관리자 머피 선물이 아직 기본 문구로 뜬다."
    //   여기에 분기가 없어서 아래 default 로 떨어지고 있었다.
    case "murpy_gift": {
      const amt = Number(n.amount || 0).toLocaleString();
      return { title: "머피가 도착했어요",
               body: `관리자가 ${amt} 머피 선물을 보냈어요` };
    }

    // ── 리텐션 (2026-08-30, functions/retention.js) ─────────────────────
    //   ★쪼아대는 톤은 대표·송정현 형님이 원한 것("제정신이냐" 류). 선은 '친구가 놀리는 말'까지.
    case "friend_workout":
      return { title: `🔥 ${who}님이 방금 운동했어요`,
               body: post ? `"${post}" · 누워 계신 건 아니죠?` : "오늘 몫을 채웠어요 · 누워 계신 건 아니죠?" };

    case "bamboo_nearby":
      return { title: `🎋 ${n.text || "우리 동네"} 대숲에 새 글`,
               body: post ? `"${post}"` : "동네 사람이 뭔가 털어놨어요" };

    case "gym_now":
      return { title: `🏋️ ${n.text || "내 헬스장"}에 ${who}님 도착`,
               body: "지금 가면 아는 얼굴이 있어요" };

    case "squad_again":
      return { title: `⚡ ${who}님이 또 열었어요`,
               body: post ? `"${post}" · 지난번 멤버 소집 중, 빠지면 서운해요` : "지난번 멤버 소집 중 · 빠지면 서운해요" };

    case "squad_nearby":
      return { title: `📍 ${n.text || "내 헬스장"}에서 스쿼드`,
               body: post ? `"${post}" · ${who}님이 열었어요` : `${who}님이 근처에서 스쿼드를 열었어요` };

    case "squad_host_again":
      return { title: `🔁 다음 ${post || "스쿼드"} 열까요?`,
               body: "지난 멤버들에게 알림이 가요 · 누르면 그대로 세팅돼요" };

    case "nag": {
      const d = Number(n.amount || 7);
      return { title: `⏰ 마지막 운동이 ${d}일 전이에요`,
               body: "근손실은 알림을 안 보내요. 그래서 저희가 보냅니다" };
    }

    default:
      return { title: "머피", body: "새 소식이 도착했어요" };
  }
}

// 알림 종류별로 눌렀을 때 열릴 주소. 앱(index.html)이 ?n= 을 읽어 화면을 고른다.
function linkFor(n) {
  const q = new URLSearchParams();
  if (n.type) q.set("n", String(n.type));
  if (n.fromUid) q.set("f", String(n.fromUid));
  if (n.postId) q.set("p", String(n.postId));
  const sid = n.squadId || n.crewId;
  if (sid) q.set("sq", String(sid));
  if (n.centerId) q.set("c", String(n.centerId));
  const qs = q.toString();
  return "https://murpy.app/" + (qs ? "?" + qs : "");
}

exports.sendNotifPush = onDocumentCreated("notifications/{id}", async (event) => {
  const n = event.data && event.data.data();
  if (!n || !n.toUid) return;

  const userSnap = await getFirestore().doc("users/" + n.toUid).get();
  const rawTokens = (userSnap.exists && userSnap.data().fcmTokens) || [];
  if (!rawTokens.length) return;

  // ★★같은 기기의 토큰이 여러 개면 **그 폰만 여러 번 울린다** (대표 9-02: "푸시가 두 개씩").
  //   FCM 웹 토큰은 `기기식별자:인증부분` 구조라, ':' 앞이 같으면 **같은 브라우저 설치**다.
  //   앱이 arrayUnion 으로 더하기만 해 온 탓에 이미 쌓인 계정이 있다(진단: 같은 기기 토큰 2개).
  //   앱 쪽도 고쳤지만, **이미 쌓인 사람은 앱을 고쳐도 배열이 저절로 줄지 않는다.**
  //   그래서 보내기 직전에 기기당 하나만 남긴다. 남기는 것은 **가장 나중에 등록된 것**이다
  //   (arrayUnion 은 뒤에 붙이므로 배열 뒤쪽이 최신).
  //   혹시 그게 죽어 있으면 아래 '만료/무효 토큰 정리'가 지우고, 다음 발송 때 남은 것이 쓰인다.
  const byDevice = new Map();
  for (const t of rawTokens) byDevice.set(String(t).split(":")[0], t);
  const tokens = Array.from(byDevice.values());
  if (tokens.length !== rawTokens.length) {
    console.log(`같은 기기 중복 토큰 ${rawTokens.length - tokens.length}개 제외 (uid=${n.toUid})`);
  }

  const { title, body } = compose(n);

  const message = {
    tokens,
    // ★★data-only 로 보냈다가 **알림이 아예 안 떴다**(대표 8-14: "푸시알람 왜 갑자기 안 뜨냐").
    //   표시를 서비스워커에 맡기려 했는데, 폰에 아직 옛 서비스워커가 남아 있거나
    //   data-only 를 안 그려주는 브라우저가 있으면 **하나도 안 뜬다.**
    //   안 뜨는 것은 두 번 뜨는 것보다 훨씬 나쁘다 — 되돌린다.
    //   → notification 을 다시 보내 **브라우저가 확실히 하나 띄우게** 하고,
    //     중복은 서비스워커 쪽 가드(payload.notification 이 있으면 안 띄움)로 막는다.
    // ★★postId·squadId 도 같이 실어 보낸다 — 앱이 켜져 있을 때 쓰고, 이동은 아래 link 가 한다.
    data: {
      type: String(n.type || ""),
      fromNickname: String(n.fromNickname || ""),
      fromUid: String(n.fromUid || ""),
      fromPhoto: String(n.fromPhoto || ""),
      postId: String(n.postId || ""),
      squadId: String(n.squadId || n.crewId || ""),
      title,
      body,
    },
    notification: { title, body },
    webpush: {
      headers: { Urgency: "high" },
      notification: {
        // ★버전을 붙인다 — 안 붙이면 FCM·브라우저가 **글씨 있던 옛 로고**를 계속 쓴다
        //   (대표 8-14: "푸시 로고도 murpy 글씨 제거된 앱아이콘 버전으로").
        //   icon = 알림에 크게 뜨는 그림 / badge = 상태표시줄의 작은 실루엣. 아이콘 고치면 이 숫자도 올릴 것.
        icon: "https://murpy.app/icon-192.png?v=595",
        badge: "https://murpy.app/badge-72.png?v=595",
        tag: String(n.type || "murpy"),
        renotify: true,
      },
      // ★★푸시를 누르면 **그 알림이 가리키는 곳**으로 (대표 8-14: "탭하면 항상 홈이다").
      //   예전엔 전부 murpy.app/ 였다. 앱이 ?n=<종류> 를 읽어 해당 화면으로 보낸다.
      fcmOptions: { link: linkFor(n) },
    },
  };

  const res = await getMessaging().sendEachForMulticast(message);
  // ★결과를 남긴다 — 8-14에 "알림이 안 뜬다"를 진단할 때 로그가 비어서 추측만 했다.
  console.log(`push type=${n.type} to=${n.toUid} tokens=${tokens.length} ok=${res.successCount} fail=${res.failureCount}`);
  res.responses.forEach((r, i) => {
    if (!r.success) console.warn(`  실패 ${i}: ${r.error && r.error.code} ${r.error && r.error.message}`);
  });

  // 만료/무효 토큰 정리
  const invalid = [];
  res.responses.forEach((r, i) => {
    if (!r.success) {
      const code = r.error && r.error.code;
      if (code === "messaging/registration-token-not-registered" ||
          code === "messaging/invalid-registration-token") {
        invalid.push(tokens[i]);
      }
    }
  });
  if (invalid.length) {
    const { FieldValue } = require("firebase-admin/firestore");
    await getFirestore().doc("users/" + n.toUid).update({
      fcmTokens: FieldValue.arrayRemove(...invalid),
    });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// ★8-29 경매 대금 정산 (보안 C3). 예전엔 산 사람 폰이 자기 잔액을 빼고, 판 사람 폰이 art_sold 알림을 읽어
//   자기 잔액을 더했다 → 아무나 자기 앞으로 art_sold 알림을 만들면 머피가 생겼다.
//   이제 서버가 한 트랜잭션에서 산 사람(fromUid) 에게서 gross 를 빼고 받는 사람(toUid) 에게 amount 를 준다.
//   한 구매는 참여자 수만큼 알림이 생기므로(각자 몫), **빼는 것은 seller 가 적힌 문서 하나에서만** 한다.
//   앱 쪽 스위치 = index.html `window.SERVER_SETTLE` (true 로 켜야 앱이 자기 잔액을 안 뺀다).
// ─────────────────────────────────────────────────────────────────────────────
exports.settleArtSold = onDocumentCreated("notifications/{id}", async (event) => {
  const snap = event.data; if (!snap) return;
  const n = snap.data() || {};
  if (n.type !== "art_sold" || n.paid === true) return;
  const buyer = n.fromUid, to = n.toUid;
  const amount = Number(n.amount) | 0, gross = Number(n.gross) | 0;
  if (!buyer || !to || amount <= 0 || amount > 1000 || gross < amount) {
    await snap.ref.set({ paid: false, failed: "bad_fields" }, { merge: true }); return;
  }
  const db = getFirestore();
  const chargeBuyer = !!n.seller;   // seller 가 적힌 문서 = 판 사람 몫 = 이 구매의 대표 문서
  try {
    await db.runTransaction(async (tx) => {
      const bRef = db.collection("users").doc(buyer), tRef = db.collection("users").doc(to);
      const bSnap = await tx.get(bRef);
      const bal = (bSnap.exists && typeof bSnap.data().credits === "number") ? bSnap.data().credits : 0;
      if (chargeBuyer) {
        if (bal < gross) throw new Error("insufficient");
        tx.update(bRef, { credits: bal - gross });
      }
      // 자기한테 보낸 문서(가짜 정산)라도 빼고 더하는 구조라 이득이 없다(수수료만큼 손해)
      tx.set(tRef, { credits: FieldValue.increment(amount) }, { merge: true });
      tx.set(snap.ref, { paid: true, settledAt: FieldValue.serverTimestamp(), settledBy: "server" }, { merge: true });
    });
  } catch (e) {
    await snap.ref.set({ paid: false, failed: String(e.message || e) }, { merge: true });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// ★8-29 머피 적립 서버 판정 — **그림자 모드** (보안 C2 준비).
//   지금은 각자 폰이 자기 잔액을 올린다(규칙은 1회 +1000 만 막음 → 반복하면 뚫림).
//   1단계(지금): 앱이 적립할 때마다 여기로 {reason, amount, key} 를 보내고, 서버는 **기록만** 하면서
//     자기 기준(사유별 하루 상한)으로 "허용했을 값"을 같이 적는다 → ledger/{자동id}.
//     며칠 뒤 claimed 와 allowed 가 맞으면 2단계로: 규칙에서 클라이언트 credits 증가를 막고 여기서 직접 올린다.
//   ★상한표는 index.html 의 CREDIT_* 와 같은 뜻이어야 한다. 값을 바꾸면 양쪽을 같이.
// ─────────────────────────────────────────────────────────────────────────────
const { onCall, HttpsError } = require("firebase-functions/v2/https");
const EARN_LIVE = true;   // 8-31 C2: false 로 내리면 그림자(기록만)로 돌아간다
const EARN_CAPS = {
  daily:        { max: 10,   perDay: 1 },     // 하루 첫 인증 5 + 7일 연속 5
  birthday:     { max: 55,   perDay: 1 },
  welcome:      { max: 30,   perDay: 1 },
  first_post:   { max: 500,  perDay: 1 },     // 창립 선물 500 / 출시 후 100
  visit:        { max: 2,    perDay: 2 },   // 8-30 방 구경 1→2
  like:         { max: 1,    perDay: 2 },
  checkin:      { max: 5,    perDay: 3 },     // 체크인 2 + 처음 센터 3
  dogam:        { max: 400,  perDay: 1 },     // 도장 랠리 50+100+250 (9-02 인상 — 앱 DOGAM_TIERS 와 함께 움직인다)
  squad_host:   { max: 10,   perDay: 3 },
  squad_attend: { max: 2,    perDay: 3 },
  bump_attend:  { max: 5,    perDay: 3 },
  bump:         { max: 10,   perDay: 3 },     // 첫 만남 10 / 이후 3, 하루 3명
  season:       { max: 10,   perDay: 2 },
  streak7:      { max: 5,    perDay: 1 },
  admin:        { max: 2000, perDay: 50 },
  gift:         { max: 2000, perDay: 50 },
  other:        { max: 20,   perDay: 5 },
};
exports.earn = onCall({ region: "asia-northeast3" }, async (req) => {
  const uid = req.auth && req.auth.uid;
  if (!uid) throw new HttpsError("unauthenticated", "login");
  const d = req.data || {};
  const reason = String(d.reason || "other").slice(0, 32);
  const claimed = Number(d.amount) | 0;
  const key = String(d.key || "").slice(0, 120);
  const cap = EARN_CAPS[reason] || EARN_CAPS.other;
  const db = getFirestore();
  const dayKey = new Date(Date.now() + 9 * 3600e3 - 5 * 3600e3).toISOString().slice(0, 10); // KST, 새벽 5시 경계(앱과 같음)
  // 오늘 같은 사유로 몇 번 인정했나
  const prev = await db.collection("ledger").where("uid", "==", uid).where("reason", "==", reason).where("day", "==", dayKey).get();
  let n = 0, dupKey = false;
  prev.forEach((s) => { const x = s.data() || {}; if (x.allowed > 0) n++; if (key && x.key === key && x.allowed > 0) dupKey = true; });
  let allowed = Math.min(Math.max(0, claimed), cap.max);
  let why = "";
  if (dupKey) { allowed = 0; why = "dup_key"; }
  else if (n >= cap.perDay) { allowed = 0; why = "day_cap"; }
  else if (claimed > cap.max) { why = "over_max"; }

  // ★2단계 승격 (8-31, C2): 기록만 하던 그림자에서 **서버가 직접 지급**으로.
  //   key 가 있으면 장부 문서 id 를 결정적으로 만들어(l_uid_reason_key) 트랜잭션 create 로
  //   중복을 원자적으로 막는다 — 같은 key 두 번째 요청은 create 가 실패한다.
  if (!EARN_LIVE) {
    await db.collection("ledger").add({ uid, reason, key, day: dayKey, claimed, allowed, why, mode: "shadow",
                                        at: FieldValue.serverTimestamp() });
    return { ok: true, allowed, claimed, why, mode: "shadow" };
  }
  const ledRef = key
    ? db.collection("ledger").doc(("l_" + uid + "_" + reason + "_" + key).replace(/[^\w-]/g, "_").slice(0, 900))
    : db.collection("ledger").doc();
  let balance = null;
  try {
    await db.runTransaction(async (tx) => {
      const uRef = db.collection("users").doc(uid);
      const uSnap = await tx.get(uRef);
      const bal = (uSnap.exists && typeof uSnap.data().credits === "number") ? uSnap.data().credits : 0;
      if (allowed > 0) { balance = bal + allowed; tx.update(uRef, { credits: balance }); }
      else balance = bal;
      tx.create(ledRef, { uid, reason, key, day: dayKey, claimed, allowed, why, mode: "live",
                          at: FieldValue.serverTimestamp() });
    });
  } catch (e) {
    // create 충돌 = 이미 준 key. 지급 없이 현재 잔액만 알려준다.
    const uSnap = await db.collection("users").doc(uid).get();
    balance = (uSnap.exists && typeof uSnap.data().credits === "number") ? uSnap.data().credits : 0;
    return { ok: true, allowed: 0, granted: 0, claimed, why: why || "dup_key", mode: "live", balance };
  }
  console.log(`earn live uid=${uid} reason=${reason} claimed=${claimed} granted=${allowed} why=${why}`);
  return { ok: true, allowed, granted: allowed, claimed, why, mode: "live", balance };
});

// ── 리텐션 알림 (2026-08-30) — 별도 파일. notifications 문서만 만들고 발송은 위 sendNotifPush 가 한다.
Object.assign(exports, require("./retention.js"));
