# MURPY 프로젝트

> 이 파일은 세션 종료 시 자동으로 업데이트됩니다.

---

## 1. 서비스 정보

| 항목 | 내용 |
|------|------|
| 서비스명 | Murpy (머피) |
| 슬로건 | Move Together |
| 목적 | 운동하는 사람들을 연결하는 커뮤니티 운영 플랫폼 |
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

## 3. 기술 스택

- **단일 HTML 파일** (`index.html`, 약 4,500줄+)
- Firebase Auth — `signInWithPopup` (구글 로그인)
- Firebase Firestore — SDK 10.12.0 ES module
- imgBB API — 이미지 업로드 (`https://api.imgbb.com/1/upload`)
- GitHub Pages — 배포
- PWA 지원 (manifest.json, apple-mobile-web-app 메타태그)

## 4. 파일 구조

```
Murpy/
├── index.html      # 전체 앱 (CSS + HTML + JS 단일 파일)
├── manifest.json   # PWA 매니페스트
├── icon.svg        # 앱 아이콘
└── .claude/
    └── settings.json  # Claude 훅 설정 (세션 종료 시 CLAUDE.md 자동 업데이트)
```

## 5. 앱 구조 (하단탭 5개)

| 탭 | 페이지 ID | 내용 |
|----|-----------|------|
| 홈 | `page-home` | 운동 인증 피드 (사진 필수, 좋아요/댓글) |
| 매칭 | `page-match` | 이성 매칭 (현재 더미데이터) |
| 대숲 | `page-bamboo` | 익명 게시판 (저에요 버튼, 채팅 연결) |
| 크루 | `page-crew` | 운동 크루 (게시판/사진첩/채팅/정모 Firestore 연동) |
| 센터 | `page-center` | 지역 헬스장 (현재 더미데이터) |

## 6. Firebase 컬렉션 구조

```
feed/                          # 홈 피드 글
  └── {postId}/comments/       # 댓글

bamboo/                        # 대나무숲 익명 게시글
  └── {text, userId, userName, userPhoto, likes, likedBy, requesters, createdAt}

users/                         # 사용자 정보
  └── {uid}/                   # {nickname, photoURL, updatedAt, ...}

notifications/                 # 알림
  └── {toUid, fromUid, fromNickname, type, crewId, read, createdAt}

chats/                         # 1:1 채팅
  └── {chatId}/messages/       # {text, senderId, createdAt}

crews/                         # 크루
  └── {crewId}/
      ├── feed/                # 크루 피드
      ├── schedules/           # 정모 일정
      │   └── {schedId}/applicants/  # 참가 신청
      ├── treasury/            # 회비 내역
      ├── posts/               # 게시판 글
      │   └── {postId}/comments/
      ├── photos/              # 사진첩
      └── chat/                # 크루 채팅

centers/                       # 헬스장/운동센터
  └── {centerId}/
      └── {name, type, location, address, rating, reviewCount,
           photos[], intro, notices[], createdAt}

reports/                       # 리뷰 신고
  └── {targetId, targetType, reason, userId, createdAt}

centerEditRequests/            # 센터 정보 수정 요청
  └── {centerId, centerName, field, currentValue, newValue, reason, userId, createdAt}
```

## 7. 완료된 기능

- 구글 로그인 / 자동로그인 유지
- 닉네임 설정 / 변경
- 프로필 사진 업로드 (원형 크롭, imgBB 저장)
- 스플래시 화면 (2.2초 후 페이드아웃)
- 홈 피드 (사진 크롭, 좋아요/댓글, Firestore 저장)
- 피드 이미지 풀스크린 뷰어
- 대나무숲 (익명 글쓰기, 저에요 신청, 채팅 연결)
- 대나무숲 탭: 전체/인기/내글 3탭 (equal-width, 파란 언더라인)
- 크루 생성 / 참가 (가입비 설정, 가입신청 승인)
- 크루 상세: 게시판 / 사진첩 / 채팅 / 정모 일정 (Firestore 연동)
- 크루 회비 관리 (treasury)
- 크루 홈 탭 소모임 스타일 (크루명 본문, 메타칩, 500자 소개)
- 크루 정모 수정/삭제
- 알림 실시간 연동
- 1:1 채팅 (onSnapshot 실시간)
- 오프라인 배너
- 지역 필터 (강남/마포/성수/송파/용산/관악/영등포/노원/광진)
- PWA 설치 지원
- 캐시 우선 로딩 (stale-while-revalidate) — 피드/크루/센터
- **센터 탭 Firestore 연동** (centers 컬렉션, 강남 15개 + 마포 8개 시딩 완료)
- **센터 지역 필터** (REGION_MAP — 대구→동네 자동 매핑)
- **센터 리뷰 신고** (reports 컬렉션)
- **센터 정보 수정 요청** (centerEditRequests 컬렉션)
- **센터 인스타 스타일 상세 페이지** (커버사진, 소개글, 갤러리, 공지)
- **센터 관리자 편집** (dyrhl4321@gmail.com 전용 — 사진/소개/공지/기본정보)

## 8. 미완성 / 진행 중 기능

- [ ] 매칭 탭 Firestore 연동 (현재 더미데이터)
- [ ] 크루 출석 체크
- [ ] 피드 페이지네이션 (현재 전체 로드)
- [ ] imgBB API 키 환경변수 처리 (현재 하드코딩)
- [ ] 사용자 센터 별점 시스템 (centers/{id}/ratings 서브컬렉션 → 평균 업데이트)
- [ ] 리뷰 작성 Firestore 연동 (현재 "준비 중이에요" 토스트)
- [ ] 센터-크루 연결 (크루 생성 시 센터 선택)
- [ ] 대숲 센터 태그 연동 (센터 상세에서 해당 센터 태그 글 필터)

## 9. 주요 함수

| 함수명 | 역할 |
|--------|------|
| `goPage(name)` | 하단탭 페이지 전환 |
| `openPanel(id)` / `closePanel(id)` | 슬라이드 패널 열기/닫기 |
| `openModal(id)` / `closeModal(id)` | 모달 열기/닫기 |
| `showToast(msg)` | 상단 토스트 메시지 |
| `requireLogin(reason)` | 로그인 필요 체크 (미로그인 시 차단) |
| `renderMatch()` | 매칭 카드 렌더링 |
| `handleLike()` / `handlePass()` | 매칭 좋아요/패스 |
| `postBamboo()` | 대나무숲 익명 글쓰기 |
| `toggleBambooLike(id)` | 대나무숲 좋아요 토글 |
| `renderCrews()` | 크루 목록 렌더링 |
| `openCrewDetail(id)` | 크루 상세 패널 열기 |
| `createCrew()` | 크루 생성 (Firestore addDoc) |
| `joinCrew(id)` | 크루 가입 신청 |
| `renderCrewFeed(crewId)` | 크루 피드 렌더링 |
| `renderCrewSchedule(crew)` | 크루 정모 일정 렌더링 |
| `renderCrewMembers(crew)` | 크루 멤버 목록 |
| `openTreasuryModal()` | 회비 관리 모달 |
| `openCreateScheduleModal()` | 정모 일정 생성 모달 |
| `confirmCrop()` | 피드 사진 크롭 확정 |
| `confirmProfileCrop()` | 프로필 사진 크롭 확정 |
| `openCommentPanel(postId)` | 피드 댓글 패널 |
| `registerCenter()` | 센터 등록 (Firestore) |
| `renderCenters()` | 센터 목록 렌더링 |
| `openCenterDetail(centerId)` | 센터 상세 패널 열기 |
| `openCenterAdminEdit(centerId)` | 센터 관리자 편집 패널 (관리자 전용) |
| `saveCenterAdminEdit()` | 센터 편집 저장 → updateCenterFirestore |
| `filterRegion(region, btn)` | 크루 지역 필터 |
| `filterCenterRegion(region, btn)` | 센터 지역 필터 (REGION_MAP 동네 매핑) |
| `openUserProfile(userId, userName, userPhoto)` | 다른 유저 프로필 보기 |
| `window.loadCentersFirestore()` | 센터 Firestore 로드 (모듈 스코프) |
| `window.updateCenterFirestore(id, data)` | 센터 정보 업데이트 (모듈 스코프) |
| `window.uploadCenterPhoto(file)` | imgBB 센터 사진 업로드 (모듈 스코프) |
| `window.seedCenters(list)` | 센터 시딩 (관리자 전용, 모듈 스코프) |
| `window.openEditScheduleModal(crewId, schedId)` | 정모 수정 모달 (모듈 스코프) |

## 10. 작업 시 주의사항

- **단일 파일**: 모든 CSS/HTML/JS가 `index.html` 한 파일에 있음 (300KB+)
- **Firebase 모듈 스코프**: ES module로 import된 Firebase 함수는 일반 `onclick` 핸들러에서 접근 불가 → `window.xxx` 전역 등록 필요
  - 일반 `<script>` (정규 스크립트): DOM 조작, UI 로직, 폼 핸들러
  - `<script type="module">` (모듈): Firebase 함수, Firestore 쿼리, Auth
  - 두 스코프 간 데이터 공유: `window.*` 브릿지 패턴 사용
- **작업 후 반드시 git push** (`gh-pages`가 별도 배포 브랜치 없이 main 직접 배포)
- **Firestore 보안 규칙 만료**: 2026년 6월 26일 만료 예정 → 갱신 필요
- imgBB API 키가 코드에 하드코딩되어 있음 (`d12b915d2ed184170a0fd4aff714234d`)
- `cache-bust` 주석 (`v20260612001`)을 수정할 때마다 버전 업데이트
- **관리자 이메일**: `dyrhl4321@gmail.com` — 센터 편집, 시딩 버튼 표시
- **센터 데이터 우선순위**: Firestore `centers` 컬렉션 > `CENTERS` 더미 배열 (getCentersList() 헬퍼)
- **색상 시스템**: 블랙 70% / 화이트 20% / 블루(#3D7EFF) 7% / 골드(#F5C24B) 3%
  - 블루 = 액션/CTA/활성 상태/LIVE 뱃지
  - 골드 = 별점(★), VERIFIED/파트너 뱃지

## 11. 다음 작업 목록 (우선순위 순)

- [ ] **사용자 센터 별점** — 별 1-5 탭, centers/{id}/ratings 서브컬렉션, 평균 자동 업데이트
- [ ] **리뷰 작성 Firestore 연동** — 현재 "준비 중이에요" 토스트만 뜸
- [ ] **매칭 탭 Firestore 실연동** — 유저 프로필 카드 실데이터, matches 컬렉션
- [ ] **크루 출석 체크** — 정모 일정에 출석확인 버튼 + attendees 서브컬렉션
- [ ] **피드 페이지네이션** — 무한스크롤 (limit(10) + startAfter)
- [ ] **Firestore 보안 규칙 갱신** — 2026-06-26 만료

## 12. 실사용화 로드맵

> 기준: 2026-06-09 / 목표: GBD CREW 247명 실제 배포

### Week 1 (6/9~6/15) — 긴급 안정화

**6/9**
- [ ] Firestore 보안 규칙 갱신 (6/26 만료)
- [ ] 피드 페이지네이션 — 무한스크롤 (limit(10) + startAfter)

**6/10**
- [ ] 크루 출석 체크 구현 (정모 일정 출석확인 버튼 + attendees 서브컬렉션)

**6/11**
- [ ] 매칭 탭 Firestore 실연동 — 유저 프로필 카드 실데이터
- [ ] 매칭 좋아요/패스 결과 저장 (matches 컬렉션)

**6/12**
- [ ] 매칭 — 상호 좋아요 시 1:1 채팅 자동 개설
- [ ] 센터 탭 Firestore 연동 — 헬스장 등록/목록 실데이터

**6/13**
- [ ] 센터 — 크루와 센터 연결 (크루 생성 시 센터 선택)
- [ ] 전체 QA (피드/대숲/크루/매칭/센터 실기기 테스트)

**6/14~6/15**
- [ ] 발견된 버그 수정 + git push

### Week 2 (6/16~6/22) — UX 완성도

**6/16**
- [ ] 푸시 알림 (Firebase Cloud Messaging) — 좋아요/댓글/크루가입
- [ ] 알림 읽음 처리 개선

**6/17**
- [ ] 피드 글 삭제/수정
- [ ] 댓글 삭제

**6/18**
- [ ] 프로필 페이지 — 내 피드 모아보기
- [ ] 유저 차단/신고 기능

**6/19**
- [ ] 크루 멤버 강퇴 (운영자 전용)
- [ ] 크루 공지 고정

**6/20**
- [ ] 대숲 신고/운영자 삭제권한
- [ ] 이미지 로딩 스켈레톤 UI

**6/21~6/22**
- [ ] 전체 QA + 버그 수정

### Week 3 (6/23~6/29) — 배포 준비

**6/23**
- [ ] imgBB API 키 보안 처리 (Firebase Functions 프록시)
- [ ] index.html 성능 최적화 (272KB 경량화)

**6/24**
- [ ] 온보딩 화면 (첫 로그인 시 운동 관심사 선택)
- [ ] 비로그인 접속 시 랜딩 페이지

**6/25**
- [ ] GBD CREW 베타 테스트 (10~20명)
- [ ] 피드백 수집

**6/26**
- [ ] Firestore 보안 규칙 재확인/갱신

**6/27~6/29**
- [ ] 베타 피드백 반영 + 전체 배포

### Week 4+ — 성장 기능

- [ ] 운동 루틴 공유
- [ ] 크루 랭킹 (출석률 기반)
- [ ] 지역 기반 크루 추천
- [ ] 앱스토어 등록 (PWA Builder)

---
*마지막 업데이트: 2026-06-12 — 센터 Firestore 연동/관리자 편집/인스타 스타일 페이지/지역 필터 반영*
