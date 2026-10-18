# 크루 기록 1차(웹) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 관리자가 만든 크루에 초대 링크로 가입하고, 러닝 인증샷을 올려 서버가 읽고(미인증 저장), 헬스장 체크인이 크루 출석·성주·챌린지로 쌓이게 한다.

**Architecture:** 판정·집계는 전부 Cloud Functions(Node 22)가 한다 — 순수 로직은 `functions/crew_logic.js`(단위 시험), Firebase 입출력은 `functions/crew.js`. 웹(`index.html`)은 읽기·표시·업로드·callable 호출만. 새 컬렉션은 서버만 쓰고(관리자 메타 예외) 클라이언트는 읽는다.

**Tech Stack:** firebase-functions v2(onCall/onDocumentCreated/onSchedule), firebase-admin 12, Gemini REST(`gemini-2.5-flash-lite`, structured JSON), Firestore rules, 바닐라 JS(index.html classic+module 블록), node:test, playwright(python) 캡처.

**Spec:** `docs/superpowers/specs/2026-10-19-crew-records-design.md`

## Global Constraints

- 앱 안 문구는 "크루"(‘동아리’ 금지). 이모지 금지(라인 SVG), 틴트 칩 금지, 원화 금지, 홍보 문구 "무료" 금지(“무료 PT”만 예외).
- UA/환경 분기 금지(애플 5.6) — 기능 유무 감지만.
- 머피 지급은 서버만, `ledger` 문서 같이(키로 중복 차단).
- 휴면 `crews` 컬렉션·코드는 건드리지 않는다. 새 컬렉션 = `crewsV2`, `runs`, `runStats`, `centerMonth`.
- 라이브 DB 에 시험 데이터 금지. 배포 전 브랜딩 세션에 캡처·문구 보고.
- 설정값(서버·웹 같은 값): 인증 1회 10머피(하루 3회) · 건강 앱 첫 연결 100(2차) · `CREW_CHALLENGE_REWARD` 100(대표 확정 10-19) · 마일스톤 100/500/1000km · 러닝 1인 15km · 헬스 1인 6회 · 기간 14일.
- 카드 거르기: 거리 0.5~100km · 페이스 150~900초/km · 거리×페이스 vs 시간 ±12% · 카드 날짜 7일 이내 · 같은 해시 / 같은 uid+runDay+km(0.01)+sec 중복 거절.
- 하루 경계 = KST 05:00(서버 `earn` 과 같음). 체크인 `day` 는 앱 `mwTodayKey()`(자정 경계) 값을 그대로 쓴다.
- index.html 수정 후: `node tools/module-syntax-check.mjs` + `node tools/dogam-syntax-check.mjs`. 배포 때만 bump/check_version.

## Review Focus

1. 같은 카드를 살짝 잘라 다시 올림(해시 다름) → 같은 uid·같은 날·같은 km·같은 시간 중복으로 거절돼야 한다. (Task 1 시험)
2. 카드에 날짜가 없음(스트라바 스토리 스티커) → 올린 날로 저장, `dayFromCard:false`, 거절 아님. (Task 1 시험)
3. 크루 두 곳 가입자의 체크인 → 두 크루 모두 출석 +1, 같은 날 두 번째 헬스장은 0. (Task 1 시험)
4. 탈퇴했다 재가입 → 그 크루 이전 기록 그대로, members 1명으로 셈(중복 +1 금지). (Task 1 시험)
5. 챌린지 기간 밖 기록·미인증 기록 → progress 변화 없음. 달성 순간 보상은 한 번만. (Task 1 시험)

---

### Task 1: 순수 로직 `crew_logic.js` + 단위 시험

**Files:**
- Create: `functions/crew_logic.js`, `functions/test/crew_logic.test.js`
- Modify: `functions/package.json` (`"scripts": {"test": "node --test test/"}`)

**Interfaces — Produces:**
- `CFG` = `{ RUN_REWARD:10, RUN_REWARD_PER_DAY:3, HEALTH_LINK_REWARD:100, CHALLENGE_REWARD:30, MILESTONES:[100,500,1000], RUN_PER_HEAD_KM:15, GYM_PER_HEAD:6, CHALLENGE_DAYS:14, KM_MIN:0.5, KM_MAX:100, PACE_MIN:150, PACE_MAX:900, TIME_TOL:0.12, MAX_AGE_DAYS:7 }`
- `kstDay(ms) -> 'YYYYMMDD'`(05시 경계), `monthKey(day) -> 'YYYYMM'`, `weekKey(day) -> 'YYYY-Www'`(ISO 주)
- `checkCard(ocr, {nowMs}) -> {ok:true, run:{km,sec,paceSec,runDay,dayFromCard,app}} | {ok:false, why}`; why ∈ `not_card|km_range|pace_range|time_mismatch|too_old|unreadable`. paceSec 없으면 sec/km 로 계산, sec 없으면 km×pace.
- `isDupRun(run, existing[]) -> bool` (같은 runDay·|km차|<0.01·|sec차|≤1)
- `matchHealth(run, workouts[]) -> {ok, source|null, why}` — 2차용. workout = `{start,end,km,app,userEntered}`; userEntered 제외, run.runDay 와 같은 날, |km차| ≤ max(0.15, 3%), |duration−sec| ≤ max(60, 5%).
- `applyRun(stats, run, {verified}) -> newStats` (runStats 는 추가로 bestKm·bestPaceSec·weekStreak·lastWeekKey 갱신 — 연속 주 = 인증·미인증 상관없이 기록 있는 주가 이어진 수) / `revertRun(stats, run, {verified}) -> newStats` — 개인·멤버·크루 공용 카운터 객체 `{km,runs,pKm,pRuns,monthKey,monthKm,weekKey,weekActive?}`. 미인증은 pKm/pRuns 만.
- `applyAttend(member, day) -> {member, counted:bool}` — lastAttendDay==day 면 counted:false.
- `weekActiveDelta(member, wk) -> 0|1` (그 멤버의 이번 주 첫 인증 기록/출석이면 1, member.weekKey 갱신)
- `challengeStep(ch, {kind, amount, atMs, verified}) -> {ch, justDone:bool}` — kind 불일치·기간 밖·미인증·이미 done 이면 그대로.
- `newMilestones(prevKm, nextKm, reached[]) -> number[]`
- `duelScore(a, b) -> {a, b}` — 입력 `{members, active, total}`(total=km 또는 출석). 참여율×50 + (1인당 평균 / 둘 중 큰 1인당 평균)×50, 소수 1자리.

- [ ] **Step 1: 실패하는 시험 작성** — `node:test` + `assert/strict`. 최소 케이스:
  - `checkCard({isRunCard:true,km:5.02,sec:1531,paceSec:305,dateISO:'2026-10-19'},{nowMs:Date.parse('2026-10-19T12:00:00+09:00')}).ok === true`, runDay `'20261019'`
  - 날짜 없음 → ok, `dayFromCard:false`, runDay = kstDay(now)
  - km 0.3 → `km_range`; pace 100 → `pace_range`; km5 pace300 sec2000 → `time_mismatch`; dateISO 8일 전 → `too_old`; isRunCard false → `not_card`
  - `isDupRun` 같은 날 5.02/1531 vs 5.02/1532 → true, 다른 날 → false
  - `applyAttend` 같은 날 두 번째 → counted false
  - `challengeStep` 기간 밖·미인증·kind 불일치 → progress 그대로; target 도달 → justDone true, 다시 호출 → justDone false
  - `newMilestones(90, 120, [])` → `[100]`; `(450, 1200, [100])` → `[500,1000]`
  - `matchHealth` userEntered 제외, 거리 3% 안 → ok
  - `duelScore({members:10,active:5,total:50},{members:20,active:20,total:100})` → b=100, a=50
  - `revertRun(applyRun(s,r),r)` 가 s 와 같다(같은 달)
- [ ] **Step 2:** `cd functions && node --test test/` → FAIL(모듈 없음)
- [ ] **Step 3:** `functions/crew_logic.js` 구현(의존성 없음, CommonJS)
- [ ] **Step 4:** `node --test test/` → 전부 PASS
- [ ] **Step 5:** 커밋 `feat(crew): 크루 기록 순수 로직 + 시험`

### Task 2: 서버 함수 `crew.js` (callable·트리거·스케줄러·OCR)

**Files:**
- Create: `functions/crew.js`
- Modify: `functions/index.js`(exports `Object.assign(exports, require('./crew.js'))`, `compose()` 에 `crew_challenge_done`·`crew_milestone` 문구 — 푸시 문구라 이모지 허용 구역), `functions/test/crew_ocr.test.js`

**Interfaces — Consumes:** Task 1 전부. **Produces (callable, region asia-northeast3):**
- `crewJoin({crewId, code}) -> {ok, crew:{id,name}}` — 코드 불일치 `permission-denied`. 트랜잭션: members/{uid} 없으면 생성(stats.members+1), left 였으면 left=false(+1), 이미 멤버면 변화 없음. users.crewIds arrayUnion.
- `crewLeave({crewId}) -> {ok}` — left=true, leftAt, stats.members−1, users.crewIds arrayRemove.
- `runSubmit({url, health?}) -> {ok:true, run:{id,km,sec,paceSec,runDay,status,app}} | {ok:false, why}` — url 은 `https://firebasestorage.googleapis.com/` 우리 버킷 + 경로 `uploads/{uid}/` 만. sha256 중복 → `dup_image`. Gemini → `checkCard` → `isDupRun`(그 uid 최근 30개) → `dup_run`. health 있으면 `matchHealth` → verified. 저장: runs 문서, runStats(본인), 각 소속 크루 members+crewsV2 stats(미인증은 pKm만), verified 면 챌린지·마일스톤·`RUN_REWARD` 지급(ledger 키 `run_{runId}`, reason `run_verified`, 하루 3회).
- `runDelete({runId}) -> {ok}` — 본인만. runs 삭제 + `revertRun` 으로 runStats·멤버·크루 되돌림, Storage 이미지 삭제.
- `crewCheckinTrigger` = onDocumentCreated(`checkins/{id}`) — users.crewIds 각각 `applyAttend`·weekActive·gym_attend 챌린지, `centerMonth/{centerId}_{YYYYMM}` counts/top(트랜잭션). 모두 멱등: 이벤트 id 를 `crewEvents/{eventId}` create 로 한 번만.
- `crewHourly` = onSchedule('every 60 minutes', Asia/Seoul) — end 지난 active 챌린지 → failed.
- 내부 `payMurpy(tx, uid, amount, reason, key)` — `earn` 과 같은 ledger 모양(mode 'live'), 키 충돌이면 0.
- 내부 `ocrCard(buf, mime) -> ocr` — Gemini REST `generateContent`, `responseMimeType:'application/json'` + `responseSchema`(isRunCard bool, app enum strava|nrc|unknown, km number, sec int, paceSec int, dateISO string nullable), thinking 끔, 시간초과 25초. 프롬프트는 영어, "숫자를 못 읽으면 null".
- Secret: `defineSecret('GEMINI_API_KEY')`, runSubmit 에만 연결.

- [ ] **Step 1:** `crew_ocr.test.js` — Gemini 응답 JSON 을 `parseOcr(text)` 로 정규화하는 순수 함수 시험(문자열 "5.02 km"·"25:31"·"5'05\"" 가 숫자로 와도 처리, 잘못된 JSON → `unreadable`). `parseOcr` 는 crew_logic.js 에 둔다.
- [ ] **Step 2:** `node --test test/` → FAIL
- [ ] **Step 3:** `parseOcr` 구현 + `crew.js` 작성
- [ ] **Step 4:** `node --test test/` PASS, `node -e "require('./functions/crew.js')"` 는 firebase 모듈이 없으면 건너뜀 — 대신 `cd functions && npm ci && node -e "require('./index.js')"` 로 로드 확인
- [ ] **Step 5:** 실제 카드 1장 OCR 수동 확인: `node functions/tools_ocr_try.js <img>`(로컬 키 `~/.config/murpy/gemini.txt`, 저장소에 넣지 않는 스크래치 스크립트) → km·sec·pace 출력
- [ ] **Step 6:** 커밋 `feat(crew): 크루 가입·러닝 카드 판정·체크인 출석 서버 함수`

### Task 3: 규칙·인덱스

**Files:** Modify `firestore.rules`, `firestore.indexes.json`

- `crewsV2/{id}`: read true; create/update `isAdmin()` 이고 update 는 `stats`·`milestones` 변경 불가(`!request.resource.data.diff(resource.data).affectedKeys().hasAny(['stats','milestones'])`); delete isAdmin. `members/*` read true, write false. `challenges/*` read true, create isAdmin, update isAdmin 이되 `progress,status,doneAt,rewardPaid` 변경 불가. `private/*` read/write isAdmin.
- `runs/*`, `runStats/*`: read signedIn, write false. `centerMonth/*`: read true, write false. `crewEvents/*`: 전부 false.
- 인덱스: runs (uid ASC, createdAt DESC) · runs (crewIds CONTAINS, createdAt DESC) · runs (imgHash ASC).
- [ ] **Step 1:** 규칙 문법 확인 `firebase deploy --only firestore:rules --dry-run`(또는 기존 `tools/deploy_firestore_rules.py --check` 가 있으면 그것) → 컴파일 OK
- [ ] **Step 2:** 커밋 `feat(crew): crewsV2·runs 규칙과 인덱스`

### Task 4: 웹 — 크루 데이터 계층 + 가입 링크

**Files:** Modify `index.html`(module 블록에 `window.crew*` 함수, classic 쪽 설정값)

**Produces:**
- `window.CREW_CFG` (Global Constraints 값과 동일)
- `window.crewMine() -> Promise<crew[]>` — `users.crewIds` 로 crewsV2 문서들(1분 캐시)
- `window.crewLoad(id) -> Promise<{crew, members[], runs[], challenge|null, past[]}>` — members 는 left=false 만, runs 는 crewIds contains 최근 20, 챌린지 active 1개 + 지난 5개
- `window.crewJoinFlow(id, code)` / `window.crewLeave(id)` — callable 래퍼, 끝나면 캐시 무효화
- 딥링크: 부팅 시 `?crew=&c=` 가 있으면 로그인 확인(`memberGate`) 후 크루 소개 시트 → 가입. 기존 `?sq=` 처리 자리 옆에 붙인다(`murpy_place_sess` 규칙처럼 링크 목적지는 유지).
- [ ] **Step 1:** 구현 후 `node tools/module-syntax-check.mjs && node tools/dogam-syntax-check.mjs` → 통과
- [ ] **Step 2:** 커밋 `feat(crew): 웹 크루 데이터·초대 링크`

### Task 5: 웹 — 크루 페이지·스쿼드 탭 줄·내 기록

**Files:** Modify `index.html`

**Produces:** 순수 문자열 함수(시험·캡처용) `window.crewPageHtml(data, me) -> string`, `window.crewRowHtml(crews) -> string`, `window.myRunStatsHtml(stats) -> string`; 열기 `window.openCrewPage(id)`(기존 `openPanel` 사용).
- 스쿼드 탭: `renderSquadPage` 첫머리에서 `#crew-mine` 에 `crewRowHtml`(크루 없으면 빈 문자열).
- 크루 페이지 구성(스펙 §2-4, §8-1): 헤더(이름·학교·인원) / 주 지표(sport 별) / "인증 대기 n km · n회" 줄 / 진행 중 챌린지 막대(블루, "PT 3회 추가까지 ○○") / 이번 주 참여 n/N / 이번 달 순위 / 최근 카드 피드(카드 이미지 그대로 + 인증됨/미인증 테두리 글자) / 지난 챌린지 / 마일스톤 / [러닝 기록 올리기] / [크루 나가기].
- 프로필 한 줄: 누적 km · 인증 n회(runStats 있을 때만).
- 칭호: `_mwTitleDefs` 에 '크루 100K'·'크루 500K'·'크루 1000K'(kind 일반).
- [ ] **Step 1:** 캡처 하네스 `tools/crew_shot.py` — 로컬 서버로 index.html 을 띄우고 `page.evaluate` 로 `crewPageHtml(가짜데이터)` 를 빈 패널에 꽂아 DPR3 캡처(390×844 + 1280×800). 라이브 DB 쓰기 없음.
- [ ] **Step 2:** 문법 검사 둘 다 통과 + 캡처 눈검수(이모지·틴트 칩·'동아리' 없음 grep: `grep -n "동아리" index.html` 새 줄 0)
- [ ] **Step 3:** 커밋 `feat(crew): 크루 페이지·스쿼드 탭 진입·내 기록`

### Task 6: 웹 — 러닝 카드 올리기 + 스캔 연출

**Files:** Modify `index.html`

**Produces:** `window.runUploadOpen(crewId?)` — 파일 고르기(`accept="image/*"`, capture 없음) → 미리보기 → `uploadImgbb`(Storage) → `runSubmit` callable. `window.runScanFx(el, result)` — 스캔선 1.5초 + 거리→페이스→날짜 체크 순차(각 350ms), 결과 문구:
  - unverified: "개인 기록에 저장됐어요" / 보조 "건강 앱 인증이 열리면 크루 점수에 들어가요"
  - 거절 why → 문구 표(`dup_image` "이미 올린 카드예요", `dup_run` "같은 기록이 이미 있어요", `too_old` "7일 안의 기록만 올릴 수 있어요", `not_card` "스트라바·나이키 기록 카드가 아니에요", `km_range|pace_range|time_mismatch` "숫자가 이상해요 — 카드 원본을 올려 주세요", `unreadable` "숫자를 못 읽었어요")
  - 올리기 화면 안내 한 줄: "지도에 집이 보이면 스트라바 개인정보 구역을 켜고 올려 주세요"
- [ ] **Step 1:** 하네스에 스캔 연출 프레임 3장 캡처(시작·중간·결과) 추가
- [ ] **Step 2:** 문법 검사 + 캡처 눈검수
- [ ] **Step 3:** 커밋 `feat(crew): 러닝 인증샷 올리기와 스캔 연출`

### Task 7: 웹 — 성주·관리자 크루 관리·탈퇴 정리

**Files:** Modify `index.html`, `functions/crew.js`(탈퇴 정리 callable `runPurgeMine()` — deleteMyAccount 가 부른다)

- 성주: 체크인 시트(`mwCheckin` 이 띄우는 도장 전 화면)에 `centerMonth/{id}_{YYYYMM}.top` 한 줄 "이번 달 성주 ○○ · n회"(없으면 숨김).
- 관리자(isAdmin) 메뉴에 "크루 관리": 크루 만들기(이름·학교·종목·소개) → crewsV2 + private/join(6자리 코드, `crypto.getRandomValues`) → 초대 링크 복사. 크루별 챌린지 만들기(종류·시작일 기본 다음 월요일 00:00 KST·14일·1인 목표 기본값, target=1인×현재 members, run_km 이면 "건강 앱 인증이 열린 뒤 시작 권장" 안내).
- `deleteMyAccount` 에서 `runPurgeMine` 호출(실패해도 탈퇴는 계속) — 내 runs·이미지 삭제, 소속 크루 left 처리.
- [ ] **Step 1:** 문법 검사 + 하네스 캡처(성주 줄·관리자 시트)
- [ ] **Step 2:** `cd functions && node --test test/` 여전히 PASS
- [ ] **Step 3:** 커밋 `feat(crew): 헬스장 성주·관리자 크루 관리·탈퇴 시 기록 정리`

### Task 8: 보고 → 배포

- [ ] **Step 1:** 브랜딩 세션에 캡처·문구·남은 결정(챌린지 보상 30 임시) SendMessage, 배포 허락 대기
- [ ] **Step 2:** 허락 뒤 순서: 규칙·인덱스(`python tools/deploy_firestore_rules.py`, 인덱스 `firebase deploy --only firestore:indexes`) → 함수(`firebase deploy --only functions:default`; GEMINI_API_KEY secret 접근 권한 확인) → 웹(문법 검사·`node tools/bump-version.mjs <N>`·`python tools/check_version.py`·add+commit+`git push origin feat/crew-records:main` 한 호출, 푸시 전 `git diff origin/main HEAD --stat`)
- [ ] **Step 3:** 라이브 확인: 관리자 계정으로 시험 크루 1개 만들고(대표 확인 뒤 실제 유치 크루로 이름 변경 또는 삭제) 실제 카드 1장 올려 미인증 저장·스캔 연출 확인 — 가짜 기록 금지, 대표 본인 실제 러닝 카드로
- [ ] **Step 4:** 다른 창(머피 창들)에 index.html 푸시 공지, 메모리 갱신
