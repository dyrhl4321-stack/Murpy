// notifications 컬렉션에 새 문서가 생기면, 받는 사람(toUid)의 기기로 FCM 푸시 전송
const { onDocumentCreated } = require("firebase-functions/v2/firestore");
const { initializeApp } = require("firebase-admin/app");
const { getFirestore } = require("firebase-admin/firestore");
const { getMessaging } = require("firebase-admin/messaging");

initializeApp();

exports.sendNotifPush = onDocumentCreated("notifications/{id}", async (event) => {
  const n = event.data && event.data.data();
  if (!n || !n.toUid) return;

  const userSnap = await getFirestore().doc("users/" + n.toUid).get();
  const tokens = (userSnap.exists && userSnap.data().fcmTokens) || [];
  if (!tokens.length) return;

  let title = "머피";
  let body = "새 알림이 있어요";
  if (n.type === "match") {
    title = "🎉 매칭 성공!";
    body = (n.fromNickname || "상대") + "님과 연결됐어요. 같이 운동해봐요";
  } else if (n.type === "bamboo_request") {
    title = "🎋 대나무숲";
    body = (n.fromNickname || "누군가") + "님이 내 글에 '저에요'를 눌렀어요";
  } else if (n.type === "crew_apply") {
    title = "크루 참가 신청";
    body = (n.fromNickname || "누군가") + "님이 참가 신청했어요";
  } else if (n.type === "crew_approved") {
    title = "크루 참가 승인";
    body = "참가 신청이 승인됐어요!";
  }

  const message = {
    tokens,
    data: {
      type: String(n.type || ""),
      fromNickname: String(n.fromNickname || ""),
      fromUid: String(n.fromUid || ""),
      fromPhoto: String(n.fromPhoto || ""),
      title,
      body,
    },
    notification: { title, body },
    webpush: {
      notification: { icon: "https://dyrhl4321-stack.github.io/Murpy/icon.svg" },
      fcmOptions: { link: "https://dyrhl4321-stack.github.io/Murpy/" },
    },
  };

  const res = await getMessaging().sendEachForMulticast(message);

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
