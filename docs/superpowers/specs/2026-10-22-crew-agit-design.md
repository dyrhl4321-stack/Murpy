# 크루 아지트 설계 (2026-10-22, 아지트 창)

대표 확정 "다 넣기": 큰 방(클럽하우스) · 꾸미기(크루장·운영진) · 변경 기록 한 줄 · 같이 걷기+채팅(정원 30) · 크루 화면 입구.
근거: `바탕화면\머피브랜딩\조사보고_크루아지트_20261019.txt`, 시안 `크루기록_최종캡처_20261019\시안_아지트_바닥벽질감_LimeZu.png`(대표 OK).

## 1. 구조 — 내 방 엔진을 일반화하지 않는다

- 내 방은 16칸이 60곳에 박혀 있고 파티·펫·공룡·상자가 얽혀 있다. 아지트는 크루 코드 쪽에 **전용 무대 한 블록**(`index.html` 모듈 끝 `// ── 크루 아지트 ──`)으로 둔다.
- 빌려 쓰는 것: 소품 정의 `mwDefFor`(방 카탈로그 그대로) · 상판 판정 `_mwRestsOn` · 캐릭터 `mwMiniCharHtml`(시트 겹·`_charLayerOrder` 그대로) · 걷기 애니 `mwWalk4` · 실시간 도우미 `window._rt`.
- 진입 함수 하나: `crewAgitOpen(crewId)`. 크루 화면(`crewPageHtml`)에는 버튼 한 줄만.

## 2. 좌표·크기

| 항목 | 값 | 이유 |
|---|---|---|
| 칸 | 48 단위(방과 같음), 화면 0.5배 = 24px | 내 방과 같은 화면 크기 |
| 판 | 가로 32 × 세로 40칸 | 32×32(768px)은 폰 세로(812~932)보다 짧아 아래가 검게 남았다 |
| 벽 | 위 4칸(192 단위): 어두운 머리 16 · 벽지 · 걸레받이 · 그림자 16 | 시안과 같은 조립 |
| 캐릭터 | 높이 224/3 px(시트 1/3 정수 배율) | 정수 배율 규칙. 약 3.1칸 |
| 카메라 | 내 발끝을 가운데로, 맵 끝에서 멈춤. 위쪽은 버튼 줄(58px)만큼 더 내려옴 | 벽 맨 위 소품이 버튼에 안 깔리게 |

바닥·벽 = LimeZu Modern Interiors 48px 에서 `tools/agit_tiles.py` 가 잘라 `char/crews/agit_floor_club.png`·`agit_wall_club.png`.
**LimeZu 라이선스: 상업 사용 가능 · 원본 재배포 불가 · limezu.itch.io 표기 필요** — 앱 크레딧 자리는 개발 창이 정한다.

## 3. 소품

- 아지트 전용 4종(c4d884f): 깃발 A(바닥, 깃대 쪽만 발자국) · 이름 배너 A(벽, **2배**, 크루 이름을 1~2줄로 얹음) · 코르크 B(벽) · 러닝화 A(벽).
- 방 카탈로그에서 클럽하우스에 맞는 것만 허용(`AG_ROOM_IDS`: 책장·안락의자 3색·탁자·의자·러그·창문·문·선반·화분·램프·덤벨·바벨·요가매트·철봉 등). 핑크·주방·침대 제외.
- 첫 배치 `_agDefault()`: 벽 가운데 배너+깃발 둘, 양쪽 소파 자리, 가운데 모임 탁자, 아래 왼쪽 운동 구석. 꾸민 적 없으면 이걸 보여 준다(저장은 안 한다).
- 충돌: 방과 같은 규칙(아래 밴드만 막음, 러그·벽걸이·상판 위 소품 통과). 사람끼리는 안 막는다(30명이면 길이 막힌다). 시작 칸에 누가 있으면 옆 빈칸.

## 4. 데이터

```
crewsV2/{crewId}                      leaderUid · staff[] · status · test  ← 개발 창 소유, 아지트는 읽기만
crewsV2/{crewId}/hideout/main         { theme:'club', f:[{id,x,y,d?}] ≤120, v, by, at, last:{by,nick,act,item,n,at} }
crewsV2/{crewId}/hideoutLog/{auto}    { by, nick, act:'place'|'move'|'remove'|'mixed', item, n, at }   ← 변경 기록
RTDB crewLive/{crewId}/players/{uid}  { tc,tr,face,t,nick,character,msg:{text,t}? }   onDisconnect 지움
RTDB crewLive/{crewId}/chat/{push}    { uid,nick,text≤60,t }   마지막 60줄만 받음
RTDB crewLive/{crewId}/seen/{uid}     마지막 다녀간 시각(ms) — 흐린 최근 방문자(7일·8명, 의자 뒤 칸)
RTDB crewLive/{crewId}/_m/{uid}       크루원 명단 거울(서버만 씀) — 규칙이 이걸로 크루원 판정
```

- 권한 판정(앱): `uid === (leaderUid || createdBy) || staff.includes(uid)`, 관리자는 지원용으로 허용. 실제로 막는 건 규칙.
- 승인제: `status` 가 있고 `'approved'` 가 아니면 진입 막음(없으면 승인으로 본다).
- 저장 충돌: 저장 직전 서버의 `v` 를 다시 읽어 내가 연 뒤 바뀌었으면 덮지 않고 지금 모습으로 다시 불러온다.
- 다른 사람이 꾸민 것은 `hideout/main` onSnapshot 으로 바로 보인다(꾸미는 중에는 내 편집을 안 덮음).
- 정원 30: 들어갈 때 70초 안에 박동한 사람이 30명이면 구경만(내 노드 안 씀, 말 못 함).

## 5. 규칙 초안(개발 창이 승인·신고 규칙과 합쳐 배포)

Firestore — `match /crewsV2/{crewId}` 안:
```
function crewMod(crewId) {
  let c = get(/databases/$(database)/documents/crewsV2/$(crewId)).data;
  return signedIn() && (request.auth.uid == c.get('leaderUid', c.get('createdBy', ''))
                        || request.auth.uid in c.get('staff', []) || isAdmin());
}
match /hideout/{docId} {
  allow read: if true;
  allow write: if docId == 'main' && crewMod(crewId)
    && request.resource.data.keys().hasOnly(['theme', 'f', 'v', 'by', 'at', 'last'])
    && request.resource.data.by == request.auth.uid
    && request.resource.data.f is list && request.resource.data.f.size() <= 120
    && request.resource.data.v == (resource == null ? 1 : resource.data.get('v', 0) + 1);   // 앞지른 저장 막기
}
match /hideoutLog/{logId} {
  allow read: if true;
  allow create: if crewMod(crewId) && request.resource.data.by == request.auth.uid;
  allow update, delete: if false;
}
```

RTDB `database.rules.json`:
```
"crewLive": { "$crew": {
  ".read": "auth != null && root.child('crewLive/' + $crew + '/_m/' + auth.uid).exists()",
  "_m": { ".write": false },
  "players": { "$uid": {
    ".write": "auth != null && auth.uid == $uid && root.child('crewLive/' + $crew + '/_m/' + auth.uid).exists()" } },
  "seen": { "$uid": {
    ".write": "auth != null && auth.uid == $uid && root.child('crewLive/' + $crew + '/_m/' + auth.uid).exists()",
    ".validate": "newData.isNumber()" } },
  "chat": { "$mid": {
    ".write": "auth != null && !data.exists() && newData.child('uid').val() == auth.uid && root.child('crewLive/' + $crew + '/_m/' + auth.uid).exists()",
    ".validate": "newData.child('text').isString() && newData.child('text').val().length <= 60 && newData.child('nick').isString() && newData.child('nick').val().length <= 24" } }
} }
```
명단 거울 `_m`: `crewJoin` → set `crewLive/{id}/_m/{uid}=true`, `crewLeave` → remove, 기존 크루원 1회 채우기. 관리자 지원 입장이 필요하면 `_m` 대신 `|| root.child('admins/'+auth.uid)` 같은 줄을 따로. 채팅 정리(14일·200줄)는 `crewHourly` 에 붙이면 된다.

## 6. 시험

- `tools/agit_shot.py <폴더>` — 실서비스 크루를 **읽기만** 해서 아이폰 390·375(WebKit)·갤럭시 320(Chromium) 기본·대화·꾸미기 화면 + 방 전체.
- `tools/agit_live_test.py` — `window._rt` 를 메모리 가짜(BroadcastChannel)로 바꿔 두 탭: 서로 보임 · 걸음 반영 · 말풍선 6초 · 대화 줄 · HTML 주입 차단 · 정원 30 · 나가면 흐린 방문자 · 7일 넘은 방문자 숨김 · 저장 거부 시 편집 유지 · 취소 원복 · 역할 판정 · 로그인 전 차단. 실서비스 DB 에 아무것도 안 쓴다.

## 6-1. 점검표 (10-22, 규칙 배포 전 — 가짜 RTDB·실데이터 읽기)

| 항목 | 결과 | 근거 |
|---|---|---|
| 아이폰 390·375 (WebKit), 갤럭시 320 (Chromium) | 통과 | `agit_shot.py` 기본·대화·크루원·꾸미기 화면. 첫 화면에 반쯤 걸친 캐릭터 없음(카메라 가로 비켜 서기) |
| 로그인 전 | 통과 | `crewAgitOpen` → 로그인 안내, 아지트 안 열림 |
| 로그인 후 | 통과(앱 흐름) | 실데이터로 그리기까지. **실서비스 입장은 규칙·명단 거울 배포 뒤** |
| 역할: 크루 없음 / 크루원 / 운영진 / 크루장 / 관리자 | 통과 | `crewAgitGate`·`crewAgitCanEdit` — 크루원 아님 막힘, 크루원 꾸미기 없음, 운영진·크루장 꾸미기, 승인 대기·닫힘 막힘 |
| 동시 접속 여러 명 | 통과(가짜) | 두 탭 서로 보임·걸음·말풍선·대화, 29명 더 채워 31번째 구경만 |
| 잘못된 입력 | 통과 | 빈 말·공백 안 보냄, 60자 자름, 1.2초 연타 막음, 대화·크루 이름 HTML 글자로만, 크루 이름 8자 넘으면 자름, 저장된 배치의 모르는 소품·이상한 좌표·120개 초과·모르는 테마 걸러 그림 |
| 꾸미기 저장 성공 · 변경 기록 쓰기·읽기 | **미점검** | 규칙이 없어 지금은 거부됨(거부 시 편집 유지·안내 문장만 확인). 규칙 배포 뒤 시험 크루로 |
| 실기기 두 계정 동시 접속 | **미점검** | 규칙·명단 거울 배포 뒤 |

## 7. 남은 것

- 규칙 배포 + `_m` 거울(개발 창) → 그 뒤 실기기 두 계정 동시 접속 점검
- 크루장·운영진 임명 화면(`crewSetStaff`) — 개발 창 쪽 크루 화면
- 테마 2종(창고 체육관·러닝 라운지) 바닥·벽: `agit_tiles.py THEMES` 에 칸만 추가하면 된다(시안 좌표 있음)
- 트로피 자동 진열(조사 보고 4번)은 이번 범위 밖
