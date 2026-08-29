murpy-kakao Worker 교체 절차 (카카오 계정 탈취 취약점 C1 수정) — 2026-08-29

★★ 2026-08-29 13:30 완료됨. 새 Worker = https://murpy-kakao.dyrhl4321.workers.dev (클라우드플레어 계정 dyrhl4321, wrangler 로그인 상태)
   Secret 3개 등록(KAKAO_JS_KEY · FIREBASE_SA · ALLOWED_ORIGINS). firestore.rules 도 같은 날 배포됨(kakaoLinks 403 확인).
   옛 Worker(dyrhl2356 계정)는 손대지 않았고 앱은 v807 부터 새 주소를 본다.
   다시 배포할 땐: cd tools/kakao-worker && npx wrangler deploy --keep-vars

무엇이 문제였나
  카카오 로그인이 kakao_{id}@kakao.murpy.app / kp_{id}_mk 이메일·비밀번호 계정을 만들었고,
  카카오 id 가 users 문서(누구나 읽음)에 저장돼 있어 아무나 남의 카카오 계정으로 로그인할 수 있었다.

바뀐 구조
  카카오 토큰 검증 + Firebase 커스텀 토큰 발급을 Worker 가 한다. 클라이언트에는 비밀번호가 없다.
  앱(index.html v806+)은 Worker 가 customToken 을 주면 새 방식, access_token 만 주면 옛 방식으로 동작한다.
  → Worker 를 먼저/나중에 바꿔도 로그인이 끊기지 않는다. 단 취약점은 Worker 교체 + FIREBASE_SA 등록 후에 닫힌다.

대표님이 할 일 (Cloudflare 대시보드, 10분)
  1. Firebase 콘솔 → 프로젝트 설정 → 서비스 계정 → "새 비공개 키 생성" → JSON 다운로드
  2. Cloudflare → Workers & Pages → murpy-kakao → Settings → Variables and Secrets
       KAKAO_JS_KEY    = (기존 값 그대로)
       FIREBASE_SA     = 1번 JSON 파일 내용 전체  ← 반드시 Secret(암호화) 로
       ALLOWED_ORIGINS = https://murpy.app,https://dyrhl4321-stack.github.io
  3. murpy-kakao → Edit code → 이 폴더의 worker.js 내용으로 통째 교체 → Deploy
  4. 확인: 카카오로 로그인 → murpy.app/?diag=1 에 "kakao: custom" 이 보이면 성공
     기존 카카오 유저는 첫 로그인 때 자동으로 옛 비밀번호가 랜덤으로 바뀐다(pwRotated).

주의
  - 서비스 계정 JSON 은 공개 저장소·카톡·메일에 절대 올리지 말 것. Cloudflare Secret 에만.
  - Firestore kakaoLinks 컬렉션은 Worker(관리자 권한)만 쓴다. firestore.rules 에 read/write false 로 박아 둠.
  - 규칙(firestore.rules) 재배포도 필요: 이 PC 엔 firebase CLI 가 없어 REST + OAuth 클릭 1회 (메모리 reference_firebase_rules_deploy).
