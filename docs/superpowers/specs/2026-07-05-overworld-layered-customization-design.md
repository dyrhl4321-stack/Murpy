# 머피월드 오버월드 캐릭터 — 다층 의상 레이어링 설계

- 작성일: 2026-07-05
- 대상 파일: `C:\Users\won\Murpy\index.html` (단일 HTML)
- 관련 메모리/설계: `2026-06-30-murpy-character-phase1-design.md`, `2026-07-02-murpyworld-fields-spec.md`

## 1. 목표 (What & Why)

머피월드에서 걷는 오버월드 캐릭터에 **머리·상의·하의·모자**를 **자유롭게 조합**해 입히고,
장착을 바꾸면 **걷는 애니메이션이 유지된 채 실시간으로 반영**되게 한다.
목적은 "운동 → 머피 적립 → 캐릭터 꾸미기"라는 동적 보상 루프(리텐션)를 뚫는 것.

의사결정 결론(별도 논의에서 확정):
- **게임 엔진(Phaser)을 도입하지 않는다.** 엔진은 이미 정합된 아트를 재생할 뿐,
  아트 생성 단계의 정합성 문제를 풀어주지 못한다. 단일 HTML 구조에 1MB 엔진을 이식할 이유 없음.
- **통짜 시트 교체(①)는 탈락.** 자유 조합이 목표이므로 각 부위가 독립된 겹이어야 한다.
- **지금 스택(쌩 JS + CSS transition) 위에서 다층 `<div>` 레이어 합성으로 구현한다.**

## 2. 비목표 (Out of Scope — 이 스펙에서 안 함)

- 상점 구매 경제(머피 차감)·Firestore 동기화 → **다음 별도 스펙**.
- 실제 완성 아트 → 이 스펙은 정합성 검증용 **임시(placeholder) 시트**로 엔진을 증명한다.
- 헬토리(근방단 한정) 몸통의 레이어드 의상 → 헬토리는 통짜 스킨 유지. 사람(human) 몸통만 의상 지원.
- 런타임 색상 tint → 색 변형은 초기엔 별도 시트로 처리(YAGNI).
- 대숲 가면(mask)/익명 연동 → 별개 관심사, 여기서 안 건드림.

## 3. 현재 코드 사실 (설계 기준, index.html)

- 아바타: `#charworld-avatar` 단일 `<div>` (`index.html:833`). `background-image`로 걷기 시트 표시.
- 몸통 종류: `_CHAR_BODIES` (`:1592`) — `human`(walk.png, cw137×ch224), `heltori`(cw175×ch224).
- 스프라이트 시트 규격: **3열 × 3행 = 9칸.**
  - 열(col): 0=정지, 1=걸음A, 2=걸음B
  - 행(row): 0=아래(정면), 1=위(후면), 2=옆(왼쪽). **오른쪽은 옆 시트를 `scaleX(-1)` 미러.**
  - (게미나이가 말한 "4방향 12프레임"은 틀림. 실제는 3방향 9칸 + 미러.)
- `_charApplyPos()` (`:1698`) — 셀 크기를 매번 동적 계산:
  ```
  DH = round(t * 3.4)                 // 표시 높이 (t=타일 픽셀)
  w  = round(DH * cw / ch)            // 폭 = 몸통 비율
  backgroundSize     = (w*3) × (DH*3)
  backgroundPosition = (-col*w, -row*DH)
  transform          = scaleX(오른쪽이면 -1)
  ```
  → **32px 하드코딩 금지.** 옷 겹도 이 `w/DH/backgroundSize`를 그대로 공유해야 어긋나지 않는다.
- 이동/입력: `charMove` (`:1716`) 타일 스텝 + frame 토글. `_charPos={tc,tr,face,frame}`.
  바운스=`translate`, 스쿼시=`scale`, 미러=`transform:scaleX` — 셋 다 독립 CSS 속성으로 아바타에 적용.
- 몸통 교체: `_charApplySprite(body)` (`:1692`).
- 진입 셋업: `renderCharSpace()` (`:1797`).
- 데이터: `users/{uid}.character = {skin,hair,hairColor,top,topColor,mask,body}` + `wardrobe[]`.
  헬퍼: `getMyCharacter`, `_charState`, `_charPersistCharacter`, `_charPersistWardrobe`.

## 4. 설계

### 4.1 슬롯과 그리는 순서 (뒤→앞 z-index)

```
body(몸통) → bottom(하의) → top(상의) → hair(머리) → hat(모자)
```

- 각 슬롯은 독립된 `<div>` 겹. 안 입은 슬롯은 그 겹을 숨김(`display:none`).
- `hair`가 `top`보다 위(머리가 어깨 위), `hat`이 `hair`보다 위. `bottom`은 `top`보다 아래(하의가 상의 밑단 아래).

### 4.2 HTML 구조 변경

`#charworld-avatar`를 **컨테이너**로 바꾸고, 내부에 순서대로 겹 `<div>`를 둔다.
위치(left/top)·미러(scaleX)·바운스(translate)·스쿼시(scale)는 **컨테이너에만** 적용 → 모든 겹이 함께 움직이고 함께 뒤집힘.

```html
<div id="charworld-avatar"><!-- 위치/미러/바운스/스쿼시 --></div>
<!-- 자식 겹은 _charBuildLayers()가 동적 생성:
     .cw-layer[data-slot="body|bottom|top|hair|hat"], position:absolute; inset:0;
     background-repeat:no-repeat; pointer-events:none; z-index=슬롯 순서 -->
```

### 4.3 렌더링 핵심 함수

- `_CHAR_LAYER_ORDER = ['body','bottom','top','hair','hat']` (그리는 순서 = z 순서)
- `_charBuildLayers()` — 컨테이너 안에 슬롯별 `.cw-layer` 겹을 (없으면) 생성. 멱등.
- `_charEquippedSheets(cfg)` — 현재 character 설정 → `{slot: sheetUrl|null}` 매핑 반환.
  - body: `_CHAR_BODIES[cfg.body].src`
  - hair/top/bottom/hat: `CHAR_ITEMS`에서 장착 id → `item.sheet`(예: `char/items/<id>.png`), 없으면 null.
- `_charApplyPos()` **리팩터**: 지오메트리(`w/DH/backgroundSize/backgroundPosition/row/col`)를 **한 번 계산**한 뒤,
  활성 겹마다 동일 값을 복사 적용:
  ```
  applyLayer(el, url):
    el.backgroundImage    = url ? url('...') : ''
    el.style.display      = url ? '' : 'none'
    el.width/height       = w / DH
    el.backgroundSize     = (w*3) × (DH*3)
    el.backgroundPosition = (-col*w, -row*DH)
  ```
  미러는 종전처럼 컨테이너 `transform: scaleX(...)`로 1회.
- `_charApplySprite`/장착 변경 → `_charRebuild()`로 통일: 몸통이나 장착이 바뀌면 겹 매핑 갱신 후 `_charApplyPos()`.

### 4.4 데이터 모델

`character`에 슬롯 필드 확장(기존 `hair`,`top` 재활용 + `bottom`,`hat` 신설):
```
character = { body, skin, hair, hairColor, top, topColor, bottom, hat, mask }
```
- 값은 각 슬롯의 아이템 id(또는 null=안 입음). id → 시트 URL은 `CHAR_ITEMS`가 갖는다.
- `CHAR_ITEMS` 항목에 `sheet` 필드 추가(오버월드 겹용). 정면 SVG(`CHAR_SHAPES`)는 프리뷰 폴백으로만.
- 저장: 기존 `_charPersistCharacter` 그대로. 신규 유저 지급/기존 백필은 `ensureCreditsInit`에서 슬롯 기본값 처리.

### 4.5 정면 프리뷰(꾸미기 화면)

WYSIWYG를 위해 프리뷰도 **같은 시트를 정면·정지 프레임(row0,col0)으로 겹쳐** 보여준다
(`_charRenderAvatar` 확장). 이러면 아트 시스템이 하나로 통일되고 "보이는 대로 걷는다".
임시 시트 단계에선 SVG 폴백과 병행 가능.

### 4.6 꾸미기 UI 배선

- 기존 `charSlot`/`charPick`(`:1832~`)의 슬롯 목록을 5개로 확장.
- 아이템 선택 시 `_charDraft[slot]` 갱신 → `_charRebuild()` 호출 → **걷는 캐릭터에 즉시 반영**.
- 저장 시 `_charPersistCharacter`. (구매/차감 로직은 이 스펙 밖.)

## 5. 아트 정합성 파이프라인 (임시 시트 + 실제 시트 공통 규칙)

정합성은 **런타임이 아니라 아트 생성 단계**에서 강제한다. 코드는 모든 겹에 동일 좌표를 복사하므로,
아트만 규격을 지키면 어긋날 수 없다.

규칙:
1. **기준 시트 고정**: 사람 몸통 3×3 걷기 시트. 칸마다 캐릭터가 정확히 동일 위치·크기.
2. **백지 생성 금지 → img2img(덧그리기)**: 나노바나나에 기준 시트를 넣고
   "포즈·크기·위치 그대로 두고 이 옷만 입혀"로 생성(inpainting). 드리프트 최소화.
3. **`build_walk.py`로 고정 격자 크롭** → 항상 같은 규격 출력.
4. **알파 추출**: 몸통 지우고 옷 픽셀만 투명 배경으로 남김 → `char/items/<id>.png`.
5. 소형 도트라 손보정(픽셀 클린업) 소량 남음. 머리·모자(머리에 얹혀 거의 안 움직임)가 가장 쉬움,
   팔 흔드는 상의가 가장 어려움.

**임시(placeholder) 시트**: 위 파이프라인 전에, PIL로 몸통 격자에 정확히 맞는 단색 반투명 도형
(예: 파란 사각 셔츠, 삼각 모자)을 3×3로 생성해 엔진 정합성부터 증명한다.

## 6. 검증 (Verification)

테스트 프레임워크가 없으므로 로컬 실기 확인:
`cd Murpy && python -m http.server 8777` → 브라우저.

체크리스트:
- 4방향(상/하/좌/우) 걷기에서 모든 겹이 몸통과 **정확히 붙어** 이동 (특히 오른쪽 미러 시).
- 걸음 프레임(정지↔A↔B) 교차 시 겹이 **함께** 프레임 전환, 밀림 없음.
- 슬롯별 아이템 교체 시 걷는 채로 **즉시** 반영, 안 입기(null) 시 해당 겹만 사라짐.
- 창 크기/기종별 타일 크기 변해도(32px 하드코딩 없음) 정합 유지.
- 바운스/스쿼시/미러가 전체 겹에 함께 적용.

## 7. 리스크와 완화

- **아트 정합성**(최대 리스크): img2img+build_walk+고정 기준으로 강제. 남는 손보정은 소형이라 소량.
- **겹 수 증가로 성능**: 겹 최대 5장 `background-position`만 갱신 → 무시 가능(캔버스 재드로 아님).
- **정면 SVG와 시트 이중화**: 프리뷰를 시트 합성으로 통일해 아트 시스템 단일화(4.5).
- **헬토리**: 통짜 스킨 유지로 범위 밖. 추후 필요 시 헬토리 전용 시트 세트로 확장.

## 8. 향후(별도 스펙)

- 상점 BM·Firestore 머피 차감/장착 동기화.
- 실제 아트 시트 프로덕션(img2img 파이프라인 문서화).
- 색상 tint, 헬토리 의상, 대숲 가면 연동, 하의·모자 이상의 슬롯 확장(엔진은 이미 범용).
