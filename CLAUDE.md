# MURPY 프로젝트

> **이 파일은 다른 문서들의 요약본이다.** 상세는 항상 `docs/` 아래 설계 문서가 소스이고,
> 여기에는 "어디를 봐야 하는가"와 "지금 어디까지 왔는가"만 적는다.
> 충돌하면 **코드 > 설계 문서 > CLAUDE.md** 순으로 신뢰할 것.
> 전략 확정본은 `murpyworld-master-brief.md`(2026-07-12), 경제·가격은 `Murpy_private/머피경제_v2_출시가격확정.md`(비공개).
> ★2026-08-29 코드 전수 인벤토리로 재작성(줄번호는 그날 기준, 금방 밀린다 — 함수명으로 rg 할 것).

---

## 0. ★문서 인덱스 (먼저 여기를 본다)

작업 전에 해당 영역의 설계 문서를 읽는다. **CLAUDE.md만 믿고 "미구현"이라고 판단하지 말 것**
— 이 파일이 낡아서 이미 만든 기능을 없다고 오판한 사고가 반복됐다(8-29에도 메모리가 낡아 7건을 미완으로 오판).

| 영역 | 문서 |
|---|---|
| **전략 확정본** | `murpyworld-master-brief.md` (7-12) |
| **출시 전 진단·보안·서버 (8-29)** | `Murpy_private/출시전_종합진단_2026-08-29.md` — 치명 3건·서버 폭발 6곳·가격·성비 결정안 |
| **경제·가격 (비공개)** | `Murpy_private/머피경제_v2_출시가격확정.md` · `MURPY_사업요약.pdf`(메일용) · `머피_경제이론_대표정리.pdf` |
| 사업계획 마스터 | `docs/사업계획/MASTER_INDEX.md` · `master/01_TIPS` `02_VC` `03_IR` · `MURPY_사업_설명서_최종본.md` |
| 수익화 | `MONETIZATION.md` (272KB 기준, 낡음 — 가격은 위 비공개 문서가 진실) |
| **특허 (비공개)** | `Murpy_private/patent/` — 1차시안 + 포트폴리오 검토. **공개 저장소 금지** |
| 스토어 등록 | `docs/prompts/2026-08-29-store-submission.txt` · 8-29 커밋 `3052f8c`(등록 현황·인수인계) `9fded83`(플레이스토어 문구) |
| 코덱스 인수인계 | 8-29 커밋 `993e62e` (v801 기준 프롬프트) |
| 카카오 로그인 Worker | `tools/kakao-worker/README.txt` (8-29 교체 완료) |
| 머피룸 파티·같이 하기 | `docs/superpowers/specs/2026-08-20-murpy-room-together-design.md` |
| 펫 | `specs/2026-08-24-murpy-room-pets-design.md` · 낙서판 `2026-08-24-room-jam-design.md` |
| 덤벨 피하기·게스트 바이럴 | `specs/2026-08-19-dumbbell-dodge-minigame-design.md` · `2026-08-20-dodge-guest-viral-design.md` |
| 명예의 전당 | `specs/2026-08-19-hall-of-fame-ranking-design.md` |
| 필드 히든 오브젝트 | `specs/2026-08-18-field-hidden-artifact-design.md` |
| 개인정보·약관·탈퇴 | `specs/2026-08-13-privacy-terms-account-deletion-design.md` (`privacy.html`·`terms.html`) |
| 히든 캐릭터 / 월간 한정 / 방 충돌 / 스쿼드 P0 / 체크인 탭 / 센터 뱃지 | `specs/2026-07-27-hidden-characters-design.md` · `2026-07-21-monthly-limited-*` · `2026-07-22-room-rescale-*` · `2026-07-19-squad-p0-design.md` · `2026-07-19-checkin-tab-*` · `2026-07-15-center-badge-*` |
| 범프/하이파이브 타당성 | `docs/MURPY_SQUAD_HIGH_FIVE_FEASIBILITY.md` |
| 에셋 스튜디오 · 추출 파이프라인 | `specs/2026-07-10-asset-studio-*` · `tools/asset-studio/README.md` · `tools/character-customizer/V2_DIFF_PIPELINE.md` |
| 생성 AI 자체학습(B안) | `docs/murpyworld-ai-generation-roadmap.md` |
| 캐릭터 규격 · 프롬프트 | `docs/character-sprite-spec.md` · `docs/캐릭터-아이템-작업가이드.md` · `docs/prompts/README.md` |
| 유저 피드백 22건 | `docs/feedback/2026-08-07-*.md` |

---

## 1. 서비스 정보

| 항목 | 내용 |
|------|------|
| 서비스명 | Murpy (머피) · 슬로건 Move Together |
| 한 문장 | **운동하는 사람을 연결하는 앱** — 상대가 진짜 운동하는 사람인지 인증 기록으로 증명. 매출은 머피(연결 신청 + 머피월드) |
| 운영자 | 김현수 (GBD CREW 근손실방지단 247명 운영, 퍼스널 트레이너) |
| **배포** | **https://murpy.app** (GitHub Pages, `CNAME`) · 옛 주소 dyrhl4321-stack.github.io/Murpy 도 산다 |
| GitHub | https://github.com/dyrhl4321-stack/Murpy (main 직접 배포) |
| Firebase | `murpyprototype` · Blaze · Functions asia-northeast3 · **이 PC 에 firebase CLI 로그인돼 있음**(8-29, dyrhl4321) |
| RTDB | `murpyprototype-default-rtdb.asia-southeast1` |
| 카카오 로그인 | Worker `https://murpy-kakao.dyrhl4321.workers.dev` (Cloudflare 계정 dyrhl4321, wrangler 로그인됨) — 커스텀 토큰 발급 |
| Analytics | GA4 `G-1W5DDCFEKY` (8-29 켬) |
| 관리자 | `dyrhl4321@gmail.com` (`ADMIN_EMAILS`, 규칙 `isAdmin()` 이메일 비교) |

## 2. 핵심 철학

- 소개팅앱이 아닌 **운동 커뮤니티 운영 플랫폼**. 진짜 경쟁자 = 카카오톡 오픈채팅·소모임·당근모임
- **화폐는 머피 하나, 쓰는 곳은 둘**(매칭·머피월드). 매칭은 주로 남성, 머피월드는 주로 여성(꾸미기 상위 77%) → 저쪽(글램)은 매칭밖에 매출이 없어 비싸야 하고 우리는 싸게 팔 수 있다
- **공정성 하드룰** — 어떤 아이템도 매칭/피드 노출에 알고리즘 이점 없음
- **검증된 만남이 자산** — 위치·사진·코드·대면접촉(범프) 순으로 신뢰등급 차등 (특허 축)
- 매칭은 양면 시장 → 지금은 **가격표는 박아두고 무료를 크게 연다**(하루 3회). 나중에 가격 인상이 아니라 무료 축소

## 3. 기술 스택

- **단일 HTML 파일** `index.html` (**36,100줄**, gzip 740KB) — CSS + HTML + JS 전부. classic `<script>` 5블록 + `<script type="module">` 1블록(Firebase)
- Firebase Auth(구글·카카오 커스텀토큰·익명) / Firestore 10.12.0 / RTDB(방·스쿼드 실시간) / Storage(사진) / Functions(v2, 3개) / Analytics
- Canvas 2D 픽셀 렌더(NEAREST, 정수배) · MapTiler 지도 · GitHub Pages · PWA(`manifest.json`, `sw.js`, FCM `firebase-messaging-sw.js`)
- 진단: `murpy.app/?diag=1` (빌드 버전·kakao 모드·analytics·펫 발행 상태 등)

## 4. 파일 구조

```
Murpy/
├── index.html              # 전체 앱 (단일 파일)
├── sw.js                   # 서비스워커 — 버전 murpy-vNNN 3곳 (tools/bump-version.mjs 가 올린다)
├── version.txt             # 앱이 60초마다 폴링해 새 버전 감지
├── firestore.rules · firestore.indexes.json · database.rules.json · storage.rules
├── functions/index.js      # sendNotifPush · settleArtSold · earn(그림자)
├── privacy.html · terms.html
├── char/                   # 에셋 + 파이프라인 (walk.png = base, 절대 재수정 금지)
├── tools/                  # 아래 §9
├── docs/                   # 설계·사업계획·프롬프트·피드백
└── ios/                    # Xcode 프로젝트(스토어용, Mac 필요)
```

## 5. 앱 구조

**하단탭 5개**: 홈(피드) / 매칭 / 대숲 / **스쿼드**(`crew` 탭 → `renderSquadPage`) / 머피월드(`char`)
※ `page-center` 는 `display:none` — **센터 탭은 없다.** 센터 상세·리뷰·신고·수정요청은 도달 불가한 죽은 코드.
※ 크루(`crews` 컬렉션, `renderCrews`·QR·공금) 는 **휴면** — 스쿼드로 대체됨.

**머피월드 내부**: 방(내 방·손님 방) · 필드(`_FIELDS` = home/gym/tennis/golf **4종**) · 체크인(지도·도장) · 머피캠

## 6. Firebase 데이터

```
Firestore
users/{uid}        nickname, gender, birth, age, district, gyms[], character, wardrobe[], credits, streak,
                   room, roomSaves[≤5], roomPos, roomMsg, artworks[≤60,{px,by,byUids,price,auc}], pet*, petsOut,
                   bumpers{}, fieldAuras, aura, titles[], title, monthly{}, visits{}, socialEarn, earnOnce,
                   mfDay/mfN(오늘 무료 매칭 수), fcmTokens[], provider  ※kakaoId 는 8-29 부터 안 둔다
  └ private/ · guestbook/ · roomstat/{day}/visitors · likestat/by
feed(+comments) · bamboo(+comments) · likes · matches · blocks · userReports · checkins/{uid}_{center}_{ymd}
squads/{id}(+members{part,slot,after,staff,paid,checkedIn}, chat) · banners · centers(+ratings) · centerTalk
reports · centerEditRequests · feedback · notifications · chats(+messages) · kakaoLinks(Worker 전용) · ledger(Functions 전용)
RTDB
roomLive/{owner}/{players/{uid}, kick, chat, jam/{open,px}, pets/{live,scene}}   # 머피룸 파티
squadRooms/{sid}/players/{uid}                                                   # 스쿼드 필드
Storage  uploads/{uid}/*.jpg (8MB, image만)
```

규칙 요점(8-29 배포): users 읽기 공개 · credits 는 1회 +1000 제한(**반복 가능 = C2 미해결**) · chats/messages 당사자만 · notifications create 는 fromUid 본인 · kakaoLinks/ledger 클라이언트 접근 불가.
규칙 배포 = `python tools/deploy_firestore_rules.py`(OAuth 클릭 1회) 또는 `firebase deploy --only firestore:rules`.

## 7. 완료된 기능 (2026-08-29 코드 기준)

**계정** — 구글·카카오(커스텀 토큰)·익명(방/스쿼드 게스트), 온보딩(성별로 몸통 결정), 탈퇴(익명화), 약관·개인정보
**피드·대숲·채팅·알림** — 4:5 컴포저·태그·인증뱃지·페이지네이션, 대숲(저에요 10머피·상호수락→채팅), 1:1 채팅, 알림(최근 100·FCM 푸시), 차단·신고
**매칭** — 오늘의 5명 덱(날짜 시드 로테이션, 패스 14일), 같은 헬스장+4·동네+2·활동, **무료 신청 하루 3회 → 100머피**(하루 10회 상한), 더보기 40머피, 수락 무료. 성별 필터 없음(기본 "모두")
**머피 경제** — `CREDITS_MODE='enforced'`, 가입 30 + 첫 인증 500(창립, `BETA_GIFT_ON`) / 출시 후 100, 하루 인증 5, 체크인 2, 소셜 1×2, 범프 10/3, 생일 55, 도감 10/30/80. 충전 모달 = 가격표(500머피 9,900원·2,000/34,900·4,500/69,000) + "곧 열려요"(**PG 없음**). 적립 그림자 장부(`functions earn` → `ledger`)
**머피월드** — 캐릭터(몸통 8종·아이템 34종·헤어 7·시즌 4·피부톤 3), 방 인테리어(슬롯 5·확장권 40), 손님 방문·방명록·콕·좋아요, **머피룸 파티**(RTDB, 정원 4, 초대 링크, 강퇴), 룸톡, **낙서판·같이 그리기**(32×32), 같이 찍기(폴라로이드), **그림 경매·장터**(상한 200, 수수료 10% 소각, 공동작 70/30, **서버 정산**), **펫 6종**(일과표·따라오기·채팅 명령·손님이 부르기), 공룡, 필드 히든 오브젝트(헬창의 기운), **덤벨 피하기**(gym 필드, 난이도 3, 게스트 링크 바이럴), 명예의 전당(인증·체크인·스쿼드장·게임, 월요일 팝업), 히든 캐릭터 3종, 시즌 한정·칭호, 얼굴 커마(재진 1건, 판매 UI 없음), 체크인(반경 **100m**), 머피캠·카카오 공유
**스쿼드** — 종목 9종 필드(시간대별), 생성/참가/승인(밀어서)/강퇴/운영진, 입금 토글, 출석 코드(30분) + **범프 출석**, 스쿼드 톡·공지, **부위 보드 + 참석 시간(slot)** + 명단 복사, 히어로 카드(배너), 게스트 초대(`?sq=`), 범프(가속도 동시성, 범퍼 도감)
**인프라(8-29)** — XSS 이스케이프(`_escHtml/_escJs`), 대숲 limit 200, 알림 limit 100(복합 인덱스), users 5분 캐시(`_usersAll`), RTDB 방 child 구독 + pets live/scene 분리, sw HTML no-cache, Storage 전용 업로드(imgBB 폴백 제거), Analytics 이벤트 7종

## 8. 미완성 / 잔업 (2026-08-29 전수 목록 — 상세는 메모리 `project_murpy_prelaunch_audit`)

**대표 손 필요**
- [ ] Sign in with Apple(앱스토어 필수) · Apple Developer · iOS 빌드(Mac) · Play 비공개 테스트
- [ ] **단체(동시) 게임** 0건 — OX 퀴즈/밸런스게임/덤벨 단체전 중 선택 · **필드별 미니게임** 1개뿐(출시 전 2개 + 시작화면·난이도·캐릭터 선택·특성)
- [ ] 범프↔헬스장 GPS 연동(대표 지정 ①, B2B 청구 근거) — 스쿼드 개설 화면 변경 상의
- [ ] 에셋: 헤어×모자 재생성, 여캐 러닝화·긴 츄리닝, 히든 캐릭터 여자 3종, 핑크 벽지·바닥(방 배경 교체 구조 없음), 후드+레깅스 살색, 캣타워 흔들림 답
- [ ] PG 결제(사업자 후) · `BETA_GIFT_ON=false`(스토어 날) · 성별 필터 UI(200~500명) · 실명 인증 · RTDB Blaze 확인 · imgBB 키 폐기(대시보드) · MapTiler 키 도메인 제한
- [ ] 대표 답 대기: 핑크 에디션 가격 · 8-13 질문 4개(무료 수락값 등)

**대표 손 없이 가능**
- [ ] **C2 2단계** — `ledger` 며칠 본 뒤 규칙에서 클라이언트 `credits` 증가 금지 + `earn` 서버 지급으로 14곳 이관
- [ ] 체크인·범프·스쿼드 출석 서버 검증(H5) · users 비로그인 공개(H3) · 익명계정 권한(H6) · 센터 수정·RTDB 채팅 uid 스푸핑
- [ ] **users 문서 분리**(room·roomSaves·bumpers·artworks 서브컬렉션) — 131명 1.8MB, 1,000명이면 13MB/회
- [ ] 1:1 채팅 `limitToLast` · likes limit · 낙서/그림 신고 경로 · 덤벨 피하기 시작화면·캐릭터 선택
- [ ] 죽은 코드(`handleProfilePic`·`openUserProfile` 중복) · `mwSetHome` 무음 실패 · `check_version.py` cp949 · sw.js activate `version:'731'` 하드코딩
- [ ] 문서: 8월 plans 체크박스, MONETIZATION.md, 사업 지식베이스 04~10

**폰 확인 대기(코드 끝)**: 카카오 `?diag=1 → kakao: custom` · 경매 1회 · 남의 방 펫·가구·그림 · 손님 펫 부르기(두 대) · 아이폰 키보드 바·엔터 전송 · 체크인 100m 실내

## 9. 주요 함수 · 도구

| 영역 | 함수 |
|---|---|
| 공통 | `goPage`/`openPanel`/`openModal`/`showToast`/`requireLogin`/`memberGate`/`_notMember` · `_escHtml`/`_escJs` · `track` |
| 매칭 | `loadMatchCandidates`(덱) · `sendLike` · `matchSpend`/`matchQuota`/`matchCostDesc` · `matchBuyMore` |
| 경제 | `earnCredit` · `spendCredit` · `earnLog`(그림자) · `grantBetaGift` · `celebrateMurpy` · `renderCreditUI` |
| 머피월드 | `_reditSave`(꾸미기) · `_mwRlJoin/_mwRlSend/_mwRlLeave`(파티) · `mwJam*` · `mwAuc*`/`_mwArtSettle`/`_mwMarketLoad` · `_mwPetPublish/_mwPetLiveWatch` · `dodgeOpen` · `loadHof` · `mwCheckin` · `_charRenderTo`(캐릭터는 이 하나로만) · `_charLayerOrder` |
| 스쿼드 | `renderSquadPage` · `openSquadDetail` · `joinSquad` · `sqStartAttend` · `bumpOpen/bpSucceed/bpEarn` · `_sqPartBoardHtml`/`sqPartTap`/`sqSlotTap` |
| 인증 | `_kakaoCodeToAuth → _kakaoWorker → _kakaoCustomAuth`(옛 `_kakaoLegacyAuth`) · `deleteMyAccount` |
| Functions | `sendNotifPush` · `settleArtSold` · `earn` |

**tools/**: `bump-version.mjs`(버전 3곳 한 번에) · `check_version.py`(`PYTHONIOENCODING=utf-8` 필요) · `module-syntax-check.mjs` + `dogam-syntax-check.mjs`(둘 다 돌릴 것) · `layer-order-check.mjs` · `deploy_firestore_rules.py`/`deploy_rtdb_rules.py` · `kakao-worker/`(wrangler.toml, `--keep-vars`) · `item-purity-check.py`/`drop_stray.py`(옷 추출 뒤 필수) · `skin_bake.py`/`face_graft.py` · `asset-studio/`(리터치, 8777) · `character-customizer/customizer_cli.py`(추출은 이것으로만)

## 10. 작업 시 주의사항

- **배포 = 푸시.** index.html 고치면 ①`node tools/module-syntax-check.mjs` + `node tools/dogam-syntax-check.mjs` 둘 다 ②`node tools/bump-version.mjs <N>` ③`python tools/check_version.py` ④`git add … && git commit && git push` **한 호출로**(두 창이 같은 저장소를 만진다 — 8-29에도 다른 창 커밋이 사이에 끼었다)
- **Firebase 모듈 스코프** — onclick 에서 쓰려면 `window.xxx`. classic 블록에서 module const(`auth`, `db`)는 안 보인다 → `typeof` 로 감싸면 조용히 죽는다(펫 발행 사고)
- **`x.f && x.f()` 는 오타를 삼킨다** — 정의 0건인 함수를 불러도 조용하다. "안 된다"면 정의부터 grep
- **캐릭터는 `_charRenderTo` 하나로, 겹 순서는 `_charLayerOrder` 로만** (사본이 여섯 곳이었고 세 번 사고)
- **새 UI 를 허락 없이 만들지 말 것** — 원래 길이 어디였나부터 찾는다. 재사용한 화면의 문구가 그대로 따라오는지 확인
- **틴트 칩 금지**(반투명 색면 배지 ×, `background:none`+테두리+글자색) · **이모지 금지**(머피 라인 SVG) · 픽셀폰트는 머피월드만 · 블루=액션 골드=코인 초록=대숲 악센트
- **인라인 style 을 '' 로 지우지 말 것** · **키보드 가림은 flex-shrink 누적**부터 의심
- **RTDB 규칙은 노드 단위** — 새 노드 이름을 쓰면 쓰기가 조용히 거부된다(pets 하위는 OK)
- **돈이 빠지는 자리엔 서버 확인**(`likes` 문서 직접 읽기 등). 머피 상수는 메모리 말고 `index.html` 을 본다
- **users 문서에 큰 것 넣지 말 것** — 홈·매칭·경매가 전원 문서를 읽는다(5분 캐시 있음). `bumpDiag` 같은 진단은 5건 이하
- **유저 입력을 innerHTML 에 넣을 땐 `_escHtml`**, onclick 문자열 안은 `_escJs`
- **sw.js 를 PowerShell 로 편집 금지**(인코딩) · 한글 md/html 도 Write 도구
- **에셋** — `char/walk.png` 재수정 금지 · 정수배 NEAREST · 알파 128 이진화 · 옷 추출 후 `drop_stray.py` + `item-purity-check.py` · 썸네일은 대표 제공만 · 등록 전 합성 미리보기로 승인
- **AI 이미지 누끼 배경은 형광 초록 #00FF00** 요청 · 프롬프트 파일은 txt · 전체 종합본으로
- **비밀·수익구조·특허는 `Murpy_private/`** — 공개 저장소 금지. 서비스 계정 JSON 은 Cloudflare Secret 에만

## 11. 절대 하지 말 것

- base 시트 수정 / 비정수배 리샘플 / NEAREST 외 보간
- 카메라 실착 인식으로 캐릭터 옷 대체 (코스메틱 경제와 충돌)
- 해금 조건 명시적 공개 / 시간대 강제 해금 / 아이템의 매칭·피드 노출 버프
- 클라이언트 단독 판정으로 **결제** 붙이기 (C2 2단계 먼저)
- '벙' 단어 사용(→ 스쿼드/스쿼드장) · 정규반 자동 생성
- 특허 초안·수익구조 문서를 공개 저장소에 두는 것

---
*마지막 업데이트: 2026-08-29 — 코드 전수 인벤토리 + 출시 전 진단(v804~v817) 반영 전면 재작성.*
