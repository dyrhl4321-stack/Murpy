# 도감 → 체크인 탭 UX 개편 설계 (2026-07-19)

## 배경 / 문제

머피월드 홈의 메인 트리오는 **지도 · 도감 · 카메라**다. 대표(김현수) 피드백:

1. **콜드스타트 불친절** — 도감 탭 진입 시 "그래서 뭘 어떻게 하라는 거지?"가 됨. 내 센터를 등록하라는 안내가 없고, "자주 가는 센터가 상단에 온다"는 개념이 강조되지 않음.
2. **보상에 M코인 없음** — 도장 랠리 보상이 `+10`/`+50` 맨숫자라 "뭘 +10 주는데?" 느낌. 우리 픽셀 M코인이 빠져 허전.
3. **원정 스탬프 목록이 세로로 너무 김** — 그 아래에 있는 보상 시스템이 제일 마지막에 밀려 발견이 어려움(직관성 없음).
4. **"도감"이라는 라벨 자체가 불명확** — 지도·카메라는 직관적인데 "도감"은 포켓몬 문화 단어라 일반 헬스인 타겟에 낯섦.

**목표:** 체크인 탭 진입 즉시 스크롤 없이 ①내 센터 등록 가능 ②다른 센터도 존재 ③보상 시스템 존재가 직관적으로 인지되게.

## 결정 사항 (대표 확정)

- 내 센터 개념 = **수동 등록(현행) 유지 + 강한 콜드스타트 안내**.
- 전체 레이아웃 = **상단 요약 3타일 + 재배치(보상 위로)** 안.
- 3타일 클릭 = **해당 섹션으로 스무스 스크롤**(목차 역할).
- 원정 스탬프 기본 = **내 홈센터 지역만 펼침**, 나머지 지역 접힘.
- 탭 이름 = `도감` → **`체크인`** (홈 트리오: 지도 · 체크인 · 카메라). 내부 패스포트/도감 화면은 유지.
- 탭 아이콘 = **도장(스탬프) 픽셀 아이콘 신규 제작**(마젠타 배경 → 누끼). 나올 때까지 기존 책 아이콘 임시.

## 대상 코드 (단일 파일 `index.html`)

- 탭 바 버튼: `index.html` ~1025 `window.mwWorldPanel('dogam')` (라벨 "도감", `char/ui/ui_ic_dogam.png`)
- 패널 헤더/타이틀: `window.mwWorldPanel` (~9912) — `title = kind==='dogam' ? '도감'` 및 `icons.dogam`
- 본문 렌더: `window.mwRenderDogam` (~9666–9793) — 전면 재구성 대상
- 보상 계산: `window.dogamBonusDue` (~9873), 뱃지: `window.mwBadgeHtml`/`_mwRenderBadges`
- M코인 에셋: `char/coin.png?v=2` (기존)

## 설계 상세

### A. 네이밍 (도감 → 체크인)

- 탭 바 라벨 "도감" → "체크인".
- `mwWorldPanel`: `kind==='dogam'` 의 `title`을 `'체크인'`으로. (kind 키 값 `dogam`은 그대로 두어 호출부 변경 최소화 — 라벨/타이틀 문자열만 변경.)
- 패널 헤더 아이콘 = 도장 아이콘(`char/ui/ui_ic_stamp.png`) — 나오기 전엔 기존 `ui_ic_dogam.png` 유지.
- 내부 `FITNESS PASSPORT` 서브헤더·"원정 스탬프"·"도장 랠리" 브랜딩은 유지.

### B. 상단 요약 3타일 (신규 — 이정표/목차)

`FITNESS PASSPORT` 헤더 아래 3칸 그리드. 스타일 = 머피월드 메인 UI 위계(사각 픽셀 입체: `#1b2233` + 3px `#05070c` 보더 + `0 0 0 2px #2b3350`).

| 타일 | 라벨 | 값 |
|------|------|-----|
| 내 센터 | "내 센터" | 홈센터명(짧게 말줄임) / 미등록이면 **"미정"** 골드 강조 |
| 원정 | "원정" | 방문한 서로 다른 센터 수 `${distinct}곳` |
| 다음 보상 | "다음 보상" | 🪙(coin.png) + `+${amt}` / 다 받았으면 "완료" |

- 각 타일 `onclick` → 해당 섹션 앵커로 `scrollIntoView({behavior:'smooth', block:'start'})`.
- 스크롤 컨테이너는 `.mw-wpanel-body`(도감 패널 본문). 앵커 id는 각 섹션 최상단 요소에 부여.

### C. 내 센터 카드 (콜드스타트 강화) — 앵커 `id="mw-dg-home"`

- **등록됨:** 현행 카드 유지(뱃지·레벨 칭호·방문횟수·진행바·오늘 체크인 버튼).
- **미등록(핵심 개선):**
  - 점선 테두리 뱃지 플레이스홀더 + 큰 "?" 로 "여기에 내 센터가 온다"를 시각화.
  - 큰 안내: "자주 가는 센터를 등록하면 매일 도장 찍고 레벨업!"
  - 혜택 한 줄: 뜨내기 → **터줏대감** 레벨업 · 도장 랠리 보상 연동.
  - 큰 CTA 버튼: `내 센터 등록하기` → `window.mwPickHome()`.

### D. 도장 랠리 보상 (홈카드 바로 아래로 이동 + M코인) — 앵커 `id="mw-dg-rally"`

- 기존 `bonusBar`를 **passport(원정 목록) 위로** 이동 → 스크롤 없이 노출.
- M코인 픽셀 표시:
  - 미션 헤더의 `보상 +${amt} 머피` → `🪙(coin.png 14px, image-rendering:pixelated) +${amt}`.
  - 3개 티어 칩의 `+${amt}` → 코인 + 숫자. 이미 받은 칸은 `✓ 받음` 유지.
- 계산 로직(`tiers`, `next`, `distinct`, `claimed`)은 변경 없음. 표시만 개선.

### E. 원정 스탬프 (압축) — 앵커 `id="mw-dg-expedition"`

- 라벨: `원정 스탬프` 옆에 **`발견 ${discovered}/${total}`** 요약 추가 (discovered = byCenter 키 수 중 others에 속한 수, total = others 수).
- 지역 아코디언 `open` 조건 변경: 기존 `got>0면 open` → **홈센터 지역만 open**.
  - 홈센터 지역 = `home.loc.split(/\s+/)[0]`.
  - 홈 미등록 시 fallback: 발견 센터가 가장 많은 지역 1개만 open(없으면 전부 접힘).

## 신규 에셋

### 도장(스탬프) 픽셀 아이콘 — `char/ui/ui_ic_stamp.png`

지도/도감 아이콘과 동일 화풍(두툼한 남색 테두리·소프트 상단광·드롭섀도우). 대상이 다색이므로 배경은 형광 마젠타(#FF00FF) → 누끼.

제미나이/나노바나나 프롬프트(레퍼런스: ui_ic_map.png, ui_ic_dogam.png 첨부):

```
A single chunky pixel-art icon of a rubber ink stamp (the kind used
for loyalty punch cards), in the exact same art style as the two
reference images: same thick dark-navy outline, same soft top-left
lighting, same bold retro 16-bit game-icon look with a subtle drop
shadow underneath.

Subject: a wooden-handled round rubber stamp pressing down, with a
small freshly-stamped ink mark (a star or check) on a surface beneath
it. Warm wood-brown handle, dark stamp base, a pop of blue or gold ink
mark. Friendly, clean, iconic — reads clearly at small size.

Composition: one icon centered, generous empty margin, no text, no
letters, no numbers.

Background: solid flat FLUORESCENT HOT PINK / MAGENTA (#FF00FF),
completely uniform single color, NO gradient, NO shadow on the
background, NO texture — a pure chroma-key backdrop. The stamp must
NOT contain any pink or magenta color.

Square canvas, crisp pixel edges (nearest-neighbor look), high resolution.
```

- 처리: 마젠타 despill(`r>g+12 & b>g+12` 경계픽셀 R·B를 G로) + alpha>40 타이트 크롭 → `char/ui/ui_ic_stamp.png` (대나무 아이콘과 동일 파이프라인).

## 비목표 (YAGNI)

- 자동 홈센터 추천/추론 없음(수동 등록 유지).
- 원정 목록을 가로 스크롤/카드덱으로 바꾸지 않음(아코디언 유지, open 기본값만 변경).
- 보상 계산·지급 로직·컬렉션 구조 변경 없음(표시 개선만).
- 체크인 코어(Geolocation/haversine) 등 master-brief 항목은 이 스펙 범위 밖.

## 검증

- 배포 후 대표 실앱 확인([[feedback_murpy_push_dont_preview]]): sw 버전 올려 푸시.
- 확인 포인트: ①미등록 상태에서 "내 센터 등록하기" 안내가 크게 보임 ②3타일이 보이고 탭하면 각 섹션 스크롤 ③보상바가 원정 목록 위에 M코인과 함께 보임 ④원정 목록이 짧아짐(내 지역만 펼침) ⑤탭·헤더가 "체크인".

## 관련 기억
[[project-murpy-session-resume]] [[feedback_murpy_ui_hierarchy]] [[feedback_nanobanana_chroma_green]] [[feedback_murpy_color_system]] [[project_murpy_roadmap]]
