# 골프 스윙 미니게임 — 설계 (2026-08-29)

> 두 번째 필드 게임(대표 8-19 지시: "출시 전 최소 2개, 시작화면·난이도·캐릭터 선택·캐릭터별 특성까지").
> **덤벨 피하기(dodge)의 뼈대를 그대로 복제한다** — 화면 구조·시작화면 3장·기록·공유·게스트 링크·명예의 전당.
> 바뀌는 것은 **게임 규칙(골프)** 과 **선수(캐릭터) 고르기 장** 하나다.
> 에셋 프롬프트 = `docs/prompts/03-golf-game-assets.txt` (배경 2장 + 오브젝트 5종, 대표가 뽑는다).

## 1. 한 줄

골프 필드(`_FIELDS.golf`)에서 "골프 스윙" 칩을 누르면 폰 화면에 꽉 찬 게임이 뜬다.
**공 뒤로 당겼다 놓으면**(앵그리버드식) 세기·방향이 정해져 공이 페어웨이를 굴러 올라가고, 3홀을 도는 동안의 타수가 점수가 된다.
캐릭터마다 파워·정확·바람 저항이 다르다(쿠키런식). 점수는 명예의 전당 '골프' 종목에 오른다.

## 2. 화면 (dodge 와 동일 구조, id 접두사만 `golf-`)

```
#golf-screen  fixed inset:0 100dvh z2300 max-width:390 overflow:hidden touch-action:none  ← 터치는 여기서만 받는다
 ├ #golf-bg          인게임 배경 golf_bg.jpg (cover, opacity .62, 실패 시 field_golf.png .45)
 ├ #golf-field       공·홀·장애물·조준선·바람 — 매 프레임 innerHTML (pointer-events:none)
 ├ #golf-me          내 캐릭터(고정 DOM, mwMiniCharHtml) — 티박스 옆에 서 있다
 ├ #golf-hud         좌상단: 홀 N/3 · 타수 · 점수 / 우상단: 바람 화살표+세기 (게임 중만)
 ├ 나가기 버튼(우상단, HUD 아래 줄)
 ├ #golf-start-screen (z7)  #golf-art-bg(golf_title.png cover, 확대→축소 등장) + 하단 그라디언트 + from 로고
 │   ├ #golf-pane-title   제목(그림에 있으면 숨김) · 내 최고 N점 · 도전장 · [눌러서 시작] · [내 기록 보기]
 │   ├ #golf-pane-howto   "이렇게 하면 돼요": 공 뒤로 당겼다 놓기 그림 · 홀/벙커/연못 설명 · 난이도(하/중/상) · [선수 고르기 →]
 │   ├ #golf-pane-char    ★새 장: 선수 카드 가로 스크롤(내 캐릭터 몸통별 특성) · [시작!] · [뒤로]
 │   └ #golf-pane-recs    지난 기록 목록 + 공유
 └ #golf-over (z6)       결과: 홀별 타수 · 총점 · 최고 갱신 · 공유(.mw-share) · 게스트 닉/가입 유도 · [다시][난이도][그만]
```

- 시작화면 전환·애니메이션은 dodge 의 `.dodge-pane/.dodge-cta/.dodge-lv-btn` 클래스와 keyframes 를 **그대로 재사용**. CSS 의 id 셀렉터(`#dodge-pane-*.in`, `#dodge-start-screen.in`, `#dodge-art-bg.in`)에 `#golf-*` 를 병기한다.
- howto 장부터는 시작화면 배경을 반투명으로 바꿔 **인게임 배경(golf_bg)이 비친다** — 대표 8-19 "타이틀에서 뜨는 게 아니라 인게임 배경으로 넘어가고 저게 떠야 함". 그래서 배경 2장이 같은 장면이어야 한다.
- 폰 화면 꽉 채우기: dodge 와 같은 `position:fixed; inset:0; height:100dvh` + 배경 `cover`. 안전 여백은 HUD 12px 고정(dodge 와 동일).

## 3. 좌표계 (dodge 와 같은 % 좌표)

- 가로 `W=100`, 세로 0~100. 화면 px 변환은 dodge `_dodgePaint` 방식(가로 = v/100×clientWidth, 세로 = y/100×clientHeight).
- **페어웨이는 아래(y 100)에서 위(y 0)로**. 티(공 시작) = (50, 86). 홀은 홀마다 (hx, hy), hy 는 14~30.
- **원근 스케일**: 배경이 뒤로 갈수록 좁아지므로 스프라이트 크기 `scale(y) = 0.55 + 0.45 × (y/100)`. 공·홀·장애물·캐릭터 전부 이 배율. 판정은 논리 좌표로만 하고 그림만 줄인다.
- 가로도 원근에 맞춰 **x 를 화면 중심 쪽으로 모은다**: `sx = 50 + (x − 50) × (0.62 + 0.38 × y/100)`. 위로 갈수록 페어웨이 폭이 62% 로 좁아지는 배경에 공이 얹힌다.

## 4. 규칙

### 4-1. 한 판 = 3홀 (`GOLF_HOLES`)
| 홀 | 홀 위치 | 장애물 | 파 |
|---|---|---|---|
| 1 | (50, 22) | 없음 | 3 |
| 2 | (34, 20) | 벙커 (42, 40) 폭 22 · 나무 (62, 55) | 3 |
| 3 | (66, 16) | 연못 (50, 50) 폭 30 · 벙커 (74, 34) | 3 |
장애물은 논리 좌표의 타원(중심·반폭·반높이). 홀당 **최대 6타**, 6타에 못 넣으면 그 홀은 0점으로 끝.

### 4-2. 샷 (입력)
- 공이 멈춰 있을 때 화면 아무 데나 누르고 **뒤로 당긴다**. 당긴 벡터 `d = start − now`(논리 좌표). 놓으면 공 속도 `v = −d/|d| × power`.
- `power = min(|d|, DRAG_MAX=38) / DRAG_MAX × V_MAX(=3.4 단위/틱@16ms) × char.power`.
- 당기는 동안: 공에서 반대 방향으로 **점선 조준선**(길이 ∝ power, 끝에 작은 표적) + 공 옆 **세기 게이지**(0~100%). 게이지가 80% 넘으면 골드.
- 정확(char.jitter): 놓는 순간 방향에 ±jitter° 난수(헬토리 4°, 나머지 0).
- 공이 구르는 동안 입력은 무시. 버튼 위 터치는 무시(dodge `skip()` 그대로).

### 4-3. 공 물리 (`golfTick`, 순수 함수 — DOM·Firestore 없음)
- 매 틱: `v += wind × char.windMul × dt`; `pos += v × dt`; `v ×= friction^dt`.
- 마찰: 페어웨이 0.982 / 러프(x<8 또는 x>92) 0.95 / **벙커 안 0.86**(빨리 서고 다음 샷 파워 ×0.7).
- 나무: 중심 거리 < 반지름이면 반사(속도 ×0.5, 법선 반전) + `hit:'tree'`.
- 연못에 들어가면(타원 안에서 속도 < 0.6 또는 진입 즉시): **벌타 +1**, 공은 샷 전 위치로 복귀, `hit:'water'`.
- OB(x<2 · x>98 · y<1 · y>99): 벌타 +1, 복귀, `hit:'ob'`.
- 홀인: 홀 중심 거리 < `CUP_R(=2.2) × lv.cup × char.cup` 이고 속도 < 1.2 → `hit:'in'`, 다음 홀. 빠르면 컵을 **튕겨 지나간다**(속도 ×0.6, 방향 유지).
- 정지 판정: |v| < 0.05 → 멈춤(다음 샷 가능). 바람은 굴러갈 때만 작용(정지한 공은 안 밀린다).
- 난수는 dodge 와 같은 LCG(`_dodgeRnd` 재사용, 시드 = 시작 시각) — 바람 방향·지터 재현 가능.

### 4-4. 난이도 (`GOLF_LV`)
| | 바람 | 컵 크기 | 마찰 보정 | 점수 배율 |
|---|---|---|---|---|
| 하 | 0 | ×1.4 | 페어웨이 0.975(짧게 굴러 통제 쉬움) | ×0.7 |
| 중 | 약(0.004, 홀마다 방향 랜덤) | ×1.0 | 기본 | ×1.0 |
| 상 | 강(0.010, 홀마다 방향·세기 랜덤) | ×0.85 | 기본 | ×2.5 |
저장 `localStorage 'golf_lv'`, 기본 'mid'. dodge 와 같은 버튼 UI(켜진 것만 채움).

### 4-5. 점수 (높을수록 좋음 — 명예의 전당 공통 랭킹과 맞춤)
- 홀 점수 = `max(0, (par + 3 − 타수)) × 10` → 홀인원 50 · 버디 40 · 파 30 · 보기 20 · 더블 10 · 그 이상 0.
- 벌타는 타수에 포함. 한 판 = 3홀 합(최대 150) × `lv.mul`. `MAX_SCORE = 999`.
- 결과 화면: 홀별 타수(⛳ 표기 없이 숫자·이름표), 총점, 최고 갱신 여부, 걸린 시간.

### 4-6. 선수(캐릭터) 특성 (`GOLF_CHARS`) — 게임 안에서만. 매칭·피드에는 영향 없음(공정성 하드룰)
| 몸통(`_CHAR_BODIES` 키) | 이름표 | power | jitter | windMul | cup | 특기 |
|---|---|---|---|---|---|---|
| human / human_f | 기본 머피 | 1.0 | 0 | 1.0 | 1.0 | 균형 |
| heltori | 헬토리 | **1.25** | 4° | 1.0 | 1.0 | 힘은 센데 손이 떨린다 |
| ddungddung | 뚱뚱이 | 0.85 | 0 | **0.4** | 1.0 | 무거워서 바람을 덜 탄다 |
| jaejin | 재진 | 1.1 | 0 | 1.0 | 1.0 | |
| cult(교주) | 교주 | 1.0 | 0 | **0** | 1.0 | 바람이 비켜 간다 |
| somm(소믈리에) | 소믈리에 | 1.0 | 0 | 1.0 | **1.3** | 컵이 넓어 보인다 |
| zombie(좀비) | 좀비 | 1.0 | 2° | 1.0 | 1.0 | **홀당 멀리건 1회**(연못·OB 벌타 없이 다시) |
- 선수 장에는 **내가 가진 몸통만 고를 수 있고**, 못 가진 것은 흐리게 + "해금하면 쓸 수 있어요"(동기 부여). 판정 = 캐릭터 시스템의 보유 판정(`_charFits`/해금 플래그) 재사용 — 새 판정 만들지 않는다.
- 카드 = `mwMiniCharHtml(내 캐릭터 cfg 에 body 만 바꾼 것)` + 이름표 + 특기 한 줄 + 막대 3개(파워/정확/바람). 선택 저장 `localStorage 'golf_char'`.
- 게임 중 `#golf-me` 는 고른 몸통으로 그린다. 샷 순간 0.25초 `scale(1.08)` 튕김 + 방향 전환(왼쪽으로 치면 face left).

## 5. 진입·기록·공유·게스트 (dodge 복제)

- **필드 칩**: `golfFieldBtn(key)` — `key==='golf'` 일 때 `#charworld-room` 에 `.mw-fieldchip`(top 52px) "골프 스윙". `charSetField` 끝(7516 옆)에서 dodge 옆에 한 줄 호출.
- **기록**: `users/{uid}.games.golf = { best, plays, recent:[{s,t,lv,ch,holes:[3,2,4],at}] ≤20, lastAt }`. 저장 함수 `golfSave` = `dodgeSave` 복제(dot path `games.golf.*`, `_hofCache=null`).
- **게스트**: `localStorage 'murpy_golf_guest'`(`dodgeGuestMerge` 순수함수 재사용), 닉은 `murpy_dodge_nick` **공유**. `golfGuestPromote` 를 `onAuthStateChanged` 의 dodge 승격 옆에서 호출.
- **링크**: `?game=golf&s=N&nick=…`. `_dodgeLinkBoot` 와 같은 부트(`game==='golf'`). 알림 라우터의 `q.get('game')` 예외는 이미 전부 통과. 게스트 닉 시트 억제 조건에 `_golfFromLink` 추가.
- **공유 카드**: `_golfCardImg` = dodge 카드 복제(1080×1350, golf_title 위 정렬) — 점수 + "3홀 · 타수 N · 난이도 X" + "골프 스윙 · murpy.app". `_mwStampData/_mwShareMeta` 프로토콜 그대로.
- **명예의 전당**: `HOF_KINDS.golf = { label:'골프', unit:'점', game:'골프 스윙', get: u.games.golf.best }`. 탭이 6개가 되므로 라벨 폭 확인(폰 360px). 월요일 팝업 종목 회전 배열에 추가.
- **뒤로가기**(10623)·`showSplashOnboarding` 미루기 조건에 `#golf-screen` 추가. `golfClose` 는 raf 취소·overflow 복원·미뤄둔 온보딩 재개.

## 6. 에셋 (대표가 뽑는다 — `docs/prompts/03-golf-game-assets.txt`)
| 파일 | 규격 | 없으면 |
|---|---|---|
| `char/game/golf_bg.jpg` | 720×1290 | `field_golf.png` 폴백(opacity .45) |
| `char/game/golf_title.png` | 720×1290 | 제목을 CSS 글자로(`#golf-title-txt`) |
| `golf_ball.png` 160×160 · `golf_hole.png` 160×240 · `golf_bunker.png` 240×160 · `golf_pond.png` 240×160 · `golf_tree.png` 160×200 | 형광초록 누끼 → `char/nukki.py` | CSS 도형(흰 원·빨간 삼각 깃발·모래색/물색 타원·초록 원)으로 그린다 — **에셋 없이도 게임은 돈다** |
캐시버스터 `?v=1`. 배경 로딩은 dodge 의 "그냥 새 배경 쓰고 onerror 로만 폴백" 패턴.

## 7. 코드 배치 (단일 파일)
- HTML: `#dodge-screen` 블록(2873~2966) **바로 뒤**에 `#golf-screen` 블록.
- CSS: dodge 게임 CSS(9900~9980) 뒤에 `#golf-*` 병기 셀렉터 + 조준선/게이지/바람 화살표 스타일.
- JS: dodge JS(16178~17258) **바로 뒤**에 골프 블록 — `GOLF`, `GOLF_LV`, `GOLF_HOLES`, `GOLF_CHARS`, `golfNew/golfShot/golfTick`(순수), `_golfPaint`, `golfOpen/golfHowto/golfChars/golfGo/golfClose`, `_golfBind`, `_golfEnd`, `golfSave/golfGuest*`, `_golfCardImg/_golfShowShare`, `golfFieldBtn`, `_golfLinkBoot`.
- `HOF_KINDS.golf` 추가(17299 근처). `charSetField`(7516)·뒤로가기(10623)·게스트 시트(14681)·auth 승격(17099) 네 곳에 한 줄씩.

## 8. 테스트
- **순수 로직 단위 테스트** `tools/tests/golf.test.mjs`(기존 tests 형식): (1) 파워·방향 → 첫 틱 속도 (2) 마찰로 멈춤 (3) 벙커 진입 시 감속·다음 샷 파워 (4) 연못·OB 벌타+복귀 (5) 홀인 판정(컵 반경·속도) (6) 3홀 점수 합·난이도 배율 (7) 캐릭터 windMul/power 반영 (8) 좀비 멀리건 1회.
- 배포 전: `node tools/module-syntax-check.mjs` + `node tools/dogam-syntax-check.mjs`, `python tools/check_version.py`.
- 실기기(대표): 화면 꽉 참(주소창 접힘 포함)·당겼다 놓기 감도·홀인 손맛·선수 장 잠금 표시·명예의 전당 골프 탭·공유 카드·게스트 링크.

## 9. 범위 밖 (YAGNI)
- 캐릭터가 클럽을 휘두르는 별도 스프라이트(스윙은 튕김 연출로 대신), 퍼팅 그린 확대 뷰, 홀 9개, 실시간 대전, 코스 에디터. 두 번째 판(테니스 핀볼 등)은 이 뼈대를 세 번째로 복제하면 된다.
