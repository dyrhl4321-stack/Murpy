// notifications 컬렉션에 새 문서가 생기면, 받는 사람(toUid)의 기기로 FCM 푸시 전송
const { onDocumentCreated } = require("firebase-functions/v2/firestore");
const { initializeApp } = require("firebase-admin/app");
const { getFirestore } = require("firebase-admin/firestore");
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
  const qs = q.toString();
  return "https://murpy.app/" + (qs ? "?" + qs : "");
}

exports.sendNotifPush = onDocumentCreated("notifications/{id}", async (event) => {
  const n = event.data && event.data.data();
  if (!n || !n.toUid) return;

  const userSnap = await getFirestore().doc("users/" + n.toUid).get();
  const tokens = (userSnap.exists && userSnap.data().fcmTokens) || [];
  if (!tokens.length) return;

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
