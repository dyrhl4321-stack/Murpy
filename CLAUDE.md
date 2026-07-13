# MURPY 프로젝트

> 이 파일은 세션 종료 시 자동으로 업데이트됩니다.
> 대규모 전략/기획 확정본은 `murpyworld-master-brief.md`(2026-07-12) 우선.

---

## 1. 서비스 정보

| 항목 | 내용 |
|------|------|
| 서비스명 | Murpy (머피) |
| 슬로건 | Move Together |
| 목적 | 운동하는 사람들을 연결하는 커뮤니티 운영 플랫폼 + 픽셀 캐릭터(머피월드) |
| 운영자 | 김현수 (GBD CREW 근손실방지단 247명 운영, 퍼스널 트레이너) |
| 배포 URL | https://dyrhl4321-stack.github.io/Murpy |
| GitHub | https://github.com/dyrhl4321-stack/Murpy |
| Firebase 프로젝트 | murpyprototype |
| Firebase API Key | AIzaSyBvMB4T-ApzHDsfmBx4f5HpPmgkqlcZ7VQ |

## 2. 핵심 철학

- 소개팅앱이 아닌 **운동 커뮤니티 운영 플랫폼**
- 카카오톡 오픈채팅/소모임을 대체하는 것이 목표
- GBD CREW에서 쓰는 공지/출석/운동인증/모임신청/크루운영 문화를 앱 안으로 이전
- 진짜 경쟁자: 카카오톡, 오픈채팅, 소모임, 당근모임
- **머피월드 = 코스메틱 경제**: 운동 인증·활동으로 캐릭터를 꾸미고 정체성/노력/희소성을 표현. 공정성 하드룰 — 어떤 아이템도 매칭/피드 노출에 알고리즘 이점 없음.

## 3. 기술 스택

- **단일 HTML 파일** (`index.html`, 약 10,200줄) — CSS + HTML + JS 전부
- Firebase Auth — `signInWithPopup` (구글 로그인)
- Firebase Firestore — SDK 10.12.0 ES module
- imgBB API — 이미지 업로드
- Canvas 2D — 머피월드 픽셀 캐릭터 레이어 합성·오버월드 렌더 (NEAREST, 정수배)
- GitHub Pages — 배포 (main 직접, 별도 gh-pages 브랜치 없음)
- PWA (manifest.json, service worker `sw.js`)

## 4. 파일 구조

```
Murpy/
├── index.html                  # 전체 앱 (단일 파일)
├── sw.js                       # 서비스워커 (STATIC/CDN 캐시=버전접미사, IMG 캐시=원격이미지)
├── manifest.json / icon.svg
├── firestore.rules             # 보안 규칙 소스
├── murpyworld-master-brief.md  # 전략 확정본 (2026-07-12)
├── char/                       # 머피월드 캐릭터·아이템 에셋 + 파이프라인 스크립트
│   ├── walk.png                # base 캐릭터 시트(846/423, 12프레임) ※절대 재수정 금지
│   ├── items/                  # top_/bottom_/shoes_/hat_ 시트 + _thumb
│   ├── fields/                 # 오버월드 배경(헬스장·한강·테니스·골프 등)
│   ├── seal_gaps.py            # 투명 틈(살 비침) 메움
│   ├── recolor_edge_skin.py    # 불투명 살색 오염(밑단 살 띠) recolor
│   ├── level_hem.py / extend_hem.py  # 밑단 평탄화·연장
│   └── extract_item.py 등      # 아이템 추출 파이프라인
├── docs/                       # 설계·리버스엔지니어링·로드맵 문서
└── .claude/settings.json       # 훅(세션 종료 시 CLAUDE.md 자동 갱신)
```

## 5. 앱 구조 (하단탭 6개)

| 탭 | 페이지 ID | 내용 |
|----|-----------|------|
| 홈 | `page-home` | 운동 인증 피드 (사진 필수, 필터, 좋아요/댓글, 편집) |
| 매칭 | `page-match` | 이성 매칭 (Firestore 실연동 — 프로필 카드/좋아요/받은 좋아요/상호매칭) |
| 대숲 | `page-bamboo` | 익명 게시판 (카테고리 칩, 저에요 신청, 채팅 연결) |
| 크루 | `page-crew` | 운동 크루 (게시판/사진첩/채팅/정모/회비/출석/관리자탭) |
| 머피월드 | `page-char` | 픽셀 캐릭터 꾸미기 + 오버월드(방·필드 이동), 코드 공유 |
| 센터 | `page-center` | 지역 헬스장 (Firestore, 별점/리뷰/신고/수정요청/관리자편집) |

## 6. Firebase 컬렉션 구조

```
users/        {uid}: {nickname, photoURL, photos[], character, wardrobe[],
                      credits, streak, ...}     # 캐릭터·크레딧·스트릭이 유저 문서에
feed/         {postId}/comments/                # 홈 피드 + 댓글
bamboo/       {postId}/comments/                # 대숲 (category, requesters[], likedBy[])
matches/      상호 좋아요/매칭 상태
likes/        매칭 좋아요(보낸/받은)
chats/        {chatId}/messages/                # 1:1 채팅
notifications/ 알림 (type: like/comment/crew/match ...)
centers/      {centerId}/ratings/{uid}          # 센터 + 사용자 별점/리뷰(평균·리뷰수 자동재계산)
crews/        {crewId}/feed|posts|photos|chat|treasury
              crews/{crewId}/schedules/{schedId}/applicants   # 정모 참가신청
              (정모 출석: 출석코드/QR 체크인 — startAttendance/submitAttendCode/qrCheckinMember)
reports/            리뷰/콘텐츠 신고
centerEditRequests/ 센터 정보 수정 요청
```

## 7. 완료된 기능 (2026-07-13 기준)

**계정·프로필**
- 구글 로그인 / 자동로그인, 닉네임 설정·변경, 프로필 사진(원형크롭 imgBB) + 다중 사진 그리드/재정렬
- 스플래시, 온보딩(obComplete) + 코치마크(showCoach — 매칭/대숲/머피월드 타겟 스포트라이트)

**피드/대숲/채팅**
- 홈 피드: 사진 크롭, 좋아요/댓글, 필터바(setFeedFilter), 글/댓글 편집·삭제, 풀스크린 뷰어
- 운동 인증(face verify: startFaceVerify) + 인증 상태/완성도 표시
- 대숲: 카테고리 칩, 익명 글, 저에요 신청, 채팅 연결, 상호수락 매칭
- 1:1 채팅 실시간(onSnapshot), 빠른메시지

**매칭** (※ 옛 더미 아님, 실연동)
- 프로필 카드 실데이터(users 공개읽기), 좋아요/패스(sendLike, likes/matches), 받은 좋아요 패널, 상호 좋아요 시 채팅 자동 개설, 비로그인=블러+잠금

**크루**
- 생성/가입(가입비·승인), 게시판/사진첩/채팅/정모(Firestore), 회비(treasury), 정모 수정/삭제
- 참가신청 승인/거절(openApplicantsPanel), **정모 출석체크(출석코드 발급 + QR 멤버 체크인, 지각 판정)**, 관리자탭(renderCrewAdminTab), 크루 문서 편집

**센터**
- Firestore 연동(강남15/마포8 시딩), 지역 필터(REGION_MAP), 인스타 스타일 상세(커버/갤러리/공지)
- **사용자 별점/리뷰(centers/{id}/ratings, 평균·리뷰수 자동)**, 신고, 정보 수정요청, 관리자 편집

**머피월드(캐릭터)**
- 픽셀 캐릭터 레이어 합성 렌더(body→bottom→shoes→top→hair→hat→accessory)
- 꾸미기(아이템 착용/색상, wardrobe 저장), 오버월드(방+필드 5종, 충돌맵, 이동), 입장 포탈 연출
- 캐릭터 코드 공유(submitCharCode), 아이템 카탈로그(_ITEM_V 버전관리)

**머피 크레딧/스트릭**
- 크레딧(CREDITS_MODE='beta' — 표시+적립 무제한, 아직 차감 안 함. 웰컴10/일1, 매칭·대숲 비용1), 스트릭 UI

**인프라**
- PWA 설치, 오프라인 배너, 캐시 우선 로딩(sw.js), 피드 페이지네이션(startAfter/limit), Firestore 영구 보안규칙(2026-06-23 게시)

## 8. 미완성 / 진행 중

- [ ] imgBB API 키 하드코딩 → Cloud Functions 프록시 (공개 런칭 전)
- [ ] 크레딧 `enforced` 모드 전환(차감·게이트) — 사용자 충분히 모인 뒤
- [ ] 히든 캐릭터 3종(풀스프라이트) + 잠금 실루엣 UI + 해금 판정 (master-brief 2장)
- [ ] 센터 체크인 코어(Geolocation + haversine 반경) + 타임스탬프 스탬프 (master-brief 3장)
- [ ] 방 자동 물화(메달/트로피) + 방명록 + 스트릭 화분 (master-brief 4장)
- [ ] 에셋 파이프라인 ①슬롯템플릿 자동추출 ②자동 후처리 (생산속도 병목)
- [ ] 체크인/해금 Cloud Functions 이관 + 어뷰징 방어 (공개 런칭 전 필수)

## 9. 주요 함수 (window.* Firestore 브릿지 중심)

| 함수 | 역할 |
|------|------|
| `goPage(name)` / `openPanel`·`openModal` / `showToast` / `requireLogin` | 네비·UI 공통 |
| `renderMatch` / `sendLike` | 매칭 렌더·좋아요(likes/matches) |
| `postBambooFirestore` / `toggleBambooLikeFirestore` / `sendBambooRequest` / `_acceptBambooMatch` | 대숲 |
| `submitFeedPost` / `setFeedFilter` / `submitComment` / `saveEditPost` | 피드 |
| `createCrew`/`joinCrew` / `submitCrewPost` / `uploadCrewPhoto` / `sendCrewChatFirestore` | 크루 |
| `openApplicantsPanel`/`rejectApplicant` / `startAttendance`/`showAttendCode`/`submitAttendCode`/`qrCheckinMember` | 크루 정모·출석 |
| `loadCentersFirestore` / `saveRatingFirestore` / `saveReportToFirestore` / `saveCenterEditRequest` / `openCenterAdminEdit` | 센터 |
| `renderCharacter`/`renderCharSpace` / `_charBuildLayers`/`_charRenderAvatar` / `refreshMyCharacter` / `submitCharCode` / `_charPersistCharacter`·`_charPersistWardrobe` | 머피월드 캐릭터 |
| `renderCreditUI`/`spendCredit`/`mwUpdateCoin` / `renderStreakUI` | 크레딧·스트릭 |
| `openChatFirestore`/`sendChatFirestore` / `startNotifListener` | 채팅·알림 |
| `saveProfile`/`saveNickname`/`persistUserPhotos`/`uploadImgbb` / `obComplete`/`showCoach` | 프로필·온보딩 |

## 10. 작업 시 주의사항

- **단일 파일**: 모든 CSS/HTML/JS가 `index.html` 한 파일(약 10,200줄)
- **Firebase 모듈 스코프**: ES module import 함수는 onclick에서 접근 불가 → `window.xxx` 전역 등록(브릿지 패턴). 모듈=Firebase/Firestore/Auth, 일반 script=DOM/UI.
- **작업 후 반드시 git push** (main 직접 배포). 에셋/JS 바꾸면 `sw.js`의 `murpy-vNNN` 3곳 + `index.html` cache-bust 주석 올릴 것(현재 **v121 / v20260713001**). 로컬 PNG는 STATIC_CACHE(버전 purge)라 버전만 올리면 전달됨.
- **머피월드 에셋 하드룰** (master-brief 0장):
  - `char/walk.png`(base 시트) **절대 재수정 금지**
  - **정수배 + NEAREST 리샘플만** (비정수배는 반투명 픽셀 폭증)
  - 레이어 순서 body→bottom→shoes→top→hair→hat→accessory
  - 아이템 경계 결함 도구: 투명틈=`seal_gaps.py`, 불투명 살색오염=`recolor_edge_skin.py`, 밑단들썩=`level_hem.py`
  - 등록 전 합성 미리보기로 정렬 증명·승인 후 등록 (말로만 "됐어요" 금지)
- **Firestore 보안 규칙**: 2026-06-23 영구 규칙 게시(만료 없음). `firestore.rules`가 소스. 전 컬렉션 커버, 쓰기=로그인, 삭제=작성자/관리자만. CLI 토큰 만료 시 콘솔 직접 게시.
- imgBB API 키 코드 하드코딩 상태
- **관리자 이메일**: `dyrhl4321@gmail.com` (센터 편집·시딩 버튼 표시)
- **색상 시스템**: 블랙70/화이트20/블루(#3D7EFF)7/골드(#F5C24B)3. 블루=액션/CTA/활성, 골드=별점/VERIFIED. 초록=대숲 정체성 악센트. **UI는 이모지 대신 머피 라인 SVG 아이콘.**

## 11. 다음 작업 우선순위 (master-brief 6장)

1. 파이프라인 개선 — 슬롯템플릿 자동추출 + 자동 후처리 (에셋 생산속도 = 병목)
2. 히든 캐릭터 3종 + 잠금 실루엣 UI + 해금 판정
3. 센터 체크인 코어 (Geolocation + haversine + 반경 150~200m)
4. 타임스탬프 스탬프 이미지 (착용 코스메틱 렌더 포함)
5. 파이프라인 프레임 전파 + 후보 레이싱
6. 우리센터 머피들 + 센터 도감 깊이축
7. 방 자동 물화(메달/트로피) + 방명록 + 스트릭 화분
8. 공개 런칭 전: 체크인 Cloud Functions 이관 + 어뷰징 방어

## 12. 절대 하지 말 것 (master-brief 7장)

- base 시트 수정 / 비정수배 리샘플 / NEAREST 외 보간
- PixelLab·Imagen 마스크 API·SAM2·ControlNet 재검토
- 카메라 실착 인식으로 캐릭터 옷 대체(코스메틱 경제와 충돌)
- 해금 조건 명시적 공개(체크리스트화) / 시간대 강제 해금(새벽 인증 등)
- 아이템의 매칭/피드 노출 버프
- 클라이언트 단독 해금·체크인 판정으로 공개 런칭
- Phase 2 생활 콘텐츠 동시 다발 개발(동사 하나만 깊게)

---
*마지막 업데이트: 2026-07-13 — CLAUDE.md 전면 갱신(6-12 이후 411커밋 반영): 매칭 실연동·센터 별점/리뷰·크루 출석체크·머피월드 캐릭터/오버월드·크레딧/스트릭·온보딩/코치마크. 레드후드 밑단 살 띠 버그 수정(recolor_edge_skin.py).*
