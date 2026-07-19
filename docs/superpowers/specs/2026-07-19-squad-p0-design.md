# 즉석 스쿼드 P0 (스쿼드 코어 + 벙주 이코노미 + 종목별 한 방 뷰) 설계 (2026-07-19)

> 상위 전략·타당성: `docs/MURPY_SQUAD_HIGH_FIVE_FEASIBILITY.md`. 본 문서는 그 로드맵의 **P0** 확정 설계.
> 근접 하이파이브(Capacitor+Swift)는 범위 밖(Phase 2+). P0는 순수 웹.

## 배경 / 목적

- MURPY는 장기 소속형 "크루"를 걷어내고, **그날 함께 운동할 소규모(2~8명) 임시 "스쿼드"**로 전환한다.
- **진짜 타겟 = "벙주"**: 주 1회 ~10명짜리 벙을 굴리는 서브 호스트. 대규모 30명+ 모임(소모임 앱 영역)이 아니라, **소규모를 자주 여는 벙주를 위한 빠르고 실질적인 도구.** 유입은 기존 소모임·카톡방 → MURPY 스쿼드.
- **차별화 3축:** ①빠른 개설·출첵 ②참가자들의 머피월드 픽셀 캐릭터가 종목별 필드에 "한 방에 모인" 뷰 ③벙주가 실질 혜택(등급·머피 적립, 추후 참가비 정산)을 가져감.

## 확정 결정 (대표)

1. **크루(GBD 포함) 개념 제거 → 슬림 스쿼드로 통일.** 하단 '크루' 탭을 '스쿼드' 탭으로 전환. 기존 크루 Firestore 데이터·코드는 **삭제하지 않고 진입점만 교체**(단일 파일 리스크 최소화, 휴면).
2. **게시판·사진첩 제거.** 스쿼드는 딱 필요한 것만: 썸네일·일시·장소·인원·금액·공금기록·QR출첵·멤버확인 + 채팅 + 한 방 뷰.
3. **공금(선입금) 유지.** (타당성 보고서는 일회성이라 제거 제안했으나 대표 지시로 유지 — 코트비·세션비 갹출에 필요.) 단 **P0는 "금액 표시 + 걷은 기록"까지**, 실이체는 계좌, 앱은 관리. **실결제·정산(PG)은 사업자 셋업 후 Phase 2.**
4. **참가 방식 = 생성 시 호스트가 "즉시 참가 / 호스트 승인" 선택.**
5. **다종목 스쿼드(7종):** 헬스 · 러닝 · 골프 · 테니스 · 클라이밍 · 하이록스 · 등산.
6. **한 방 뷰 = 종목별 필드 배경 위 참가 캐릭터 정적 배치**("우리 센터 머피들" 필드 재사용). 걸어다니는 인터랙티브 룸은 다음 단계.
7. **벙주 이코노미 3층 중 P0 = ①등급/인증 + ②호스트 머피 적립** (둘 다 가상, 사업자 전 가능). ③참가비 실정산은 Phase 2.

## 대상 코드 (단일 파일 `index.html`)

- 하단 탭 '크루' 진입: `goPage('crew')` / `page-crew` 렌더 → 스쿼드로 교체.
- 재활용 대상(크루): `crews/{id}/schedules|applicants|chat`, `startAttendance`/`submitAttendCode`/`endAttendance`(6자리 코드·30분 만료·지각 5분·결석), `openQRModal`/`qrCheckinMember`, `treasury`(공금), `notifications`.
- 머피월드 한 방 뷰 재사용: `mwCenterField`/`mwFieldPlace`(x16~76/y56~86 안전영역)/`mwMiniCharHtml`/`centerFieldSrc`.
- 크레딧: `users/{uid}.credits`, `mwUpdateCoin`.

## 설계 상세

### A. 네비게이션 / 페이지
- 하단 탭 '크루' → '스쿼드'로 라벨·아이콘 교체. `page-crew`를 스쿼드 리스트로 재구성(기존 크루 렌더 함수는 남기되 미연결).
- 스쿼드 리스트(피드): 오늘/예정 스쿼드 카드 + 상단 `[+ 스쿼드 만들기]`.

### B. 스쿼드 카드 (피드 아이템)
- 좌측 **썸네일**(종목 아이콘 또는 호스트 지정) · 제목 · **몇월·몇시 · 장소(센터/텍스트)** · **인원(현재/정원)** · **금액**.
- 배지: 종목 태그, source, 강도, 상태(모집중/마감/진행/종료).

### C. 스쿼드 생성 (30초 폼)
- 입력: 종목(7종 선택) · 장소(센터 검색 또는 자유텍스트) · 날짜·시간 · 정원(2~8) · 강도 · 한 줄 메모 · (선택)참가비 금액 · 참가방식(즉시/승인).
- `source='manual'`. QR/센터/매칭 생성은 P1+.

### D. 스쿼드 상세
- 헤더: 썸네일·일시·장소·인원·금액·공금 걷은 기록.
- **한 방 뷰(핵심 차별화):** 종목별 필드 배경 + 참가 멤버들이 각자 머피 픽셀 캐릭터로 `mwFieldPlace` 안전영역에 정적 배치(제자리걷기 애니 `mwWalk`). `mwCenterField` 렌더를 스쿼드용으로 파생.
- 멤버 목록: 프로필·캐릭터·출석상태(누가 누군지).
- 채팅: `squads/{id}/chat` 실시간(크루 채팅 재사용).
- 출석: QR 체크인 + 6자리 코드 폴백. 정시/지각(시작+5분). *P0는 QR/코드, 하이파이브는 Phase 2.*
- 공금: 금액·걷은 인원 표시·기록(실이체 X).
- 자동 종료: `endedAt`/`expiresAt` 경과 시 `status='completed'`, 채팅 읽기전용, 운동기록은 프로필·머피월드 유지.

### E. 종목별 필드 (한 방 뷰 배경)
- 종목 → 스쿼드 필드 src 매핑. **와이드 배경**(센터 필드 `field_gym_wide.png` 계열, 캐릭터 하단중앙 안전영역).
- 자산 현황: 헬스=`field_gym_wide.png`(있음). **신규(나노바나나, 대표 생성):** 러닝·클라이밍·하이록스·등산 → `char/fields/squad_<type>.png`. 골프·테니스는 와이드 버전 후보(없으면 기본 폴백).
- **폴백:** 종목 필드 미존재 시 `field_gym_wide.png`(기본)로 렌더 → 에셋 안 기다리고 P0 배포 가능. 필드는 도착하는 대로 매핑에 추가.

### F. 벙주 이코노미 (P0 = 등급/인증 + 호스트 머피 적립)
- **벙주 등급/인증:** `users/{uid}.hostStats = { hosted, completed }`. 개설·완주 실적으로 등급·"인증 벙주" 배지. 스쿼드 카드/프로필에 표시.
- **호스트 머피 적립:** 스쿼드가 정상 완료(출석 N명 이상)되면 호스트에게 머피 크레딧 적립(`users/{host}.credits += reward`). 멱등키(squadId)로 1회.
- **참가비 실정산(③): Phase 2** — PG(토스페이먼츠 등)·사업자 등록 전제. P0 스코프 아님.

## Firestore 데이터 (제안)

```text
squads/{squadId}
  hostUid, memberUids[]                 // 배열 + members 서브컬렉션
  title, exerciseType(gym|running|golf|tennis|climbing|hyrox|hiking)
  centerId|null, location, scheduledAt
  startedAt, endedAt, expiresAt
  capacity(2~8), level, oneLineMemo, thumbUrl
  joinMode(instant|approval)
  feeAmount|0
  status(forming|recruiting|ready|active|completed|cancelled|expired)
  source(manual|match|bamboo|center|highFive|qr)   // P0=manual
  checkinCode, checkinCodeExpiry        // ★값 클라 노출 금지(§보안)
  hostRewarded(bool)                     // 멱등
  createdAt
squads/{squadId}/members/{uid}
  status(invited|accepted|checkedIn|late|noShow|completed|left)
  nickname, character, joinedAt, checkinTime, checkinType
squads/{squadId}/chat/{msgId}           // 크루 chat과 동형
users/{uid}.hostStats { hosted, completed }
```

## 보안 (P0 최소선 + Phase 2 승격)
- **P0:** 보안규칙에서 스쿼드 쓰기=로그인, 멤버등록=본인, 삭제=호스트/관리자. 현재 크루 규칙 패턴 확장.
- **알려진 약점(승격 필요):** 크루식 `submitAttendCode`는 클라가 코드 대조 → 위조 가능. **호스트 머피 적립 등 보상 연동 시 Cloud Functions 서버검증 필수**(Phase 2, 타당성 §16). P0는 보상 금액을 낮게 두고 남용 모니터링.

## 비목표 (YAGNI / 이후 단계)
- 근접 하이파이브(Multipeer/UWB/햅틱) = Capacitor+Swift, Phase 2+.
- 참가비 실결제·정산(PG) = 사업자 후 Phase 2.
- QR/센터/매칭/대숲발 스쿼드 생성 = P1(P0는 수동 생성 + QR 출첵만).
- 걸어다니는 인터랙티브 스쿼드 룸 = 이후.
- 기존 크루 데이터 마이그레이션/삭제 = 하지 않음(휴면 유지).

## 검증
- 배포 후 대표 실앱 확인([[feedback_murpy_push_dont_preview]]): sw 버전업·푸시.
- 확인 포인트: ①'스쿼드' 탭·생성 30초 ②카드에 종목·일시·장소·인원·금액 ③상세에서 참가 캐릭터가 종목 필드에 모여 보임 ④QR/코드 출첵·지각판정 ⑤완료 시 자동종료+호스트 머피 적립 ⑥벙주 등급 표시.

## 관련 기억
[[project_murpy_roadmap]] [[project_murpy_business]] [[project_murpy_character]] [[feedback_murpy_ui_hierarchy]] [[project_murpy_session_resume]] [[feedback_nanobanana_chroma_green]]
