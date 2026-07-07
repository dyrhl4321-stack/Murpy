# 머피월드 꾸미기 전용 화면 + 방 캐릭터 키우기 (1단계) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 폰에서 커스터마이징이 잘 보이도록, "꾸미기"를 누르면 큰 정면 캐릭터(4방향 돌려보기)와 슬롯/아이템을 위아래로 보여주는 전용 화면으로 전환하고, 방 안 캐릭터를 약 1.5배 키운다.

**Architecture:** 단일 `index.html` 안에서 `#page-char`에 `position:fixed` 오버레이 `#mw-dress`를 추가한다. 큰 캐릭터는 기존 레이어 합성(`_charEquippedSheets` + 겹 div, `_charRenderAvatar`와 동일 원리)을 face(방향) 파라미터 + 큰 크기로 렌더하는 `_charRenderHero(face)`로 그린다. 슬롯 탭/아이템 그리드(`charSlot`/`charPick` 등)는 그대로 재사용하고 위치만 옮긴다. 방 크기·캐릭터 비율은 상수 2곳만 조정한다.

**Tech Stack:** 순수 HTML/CSS/JS(모듈 아님, `window.*` 전역), 기존 `.mw-*` 픽셀 UI 킷 + Galmuri 폰트. 검증은 로컬 `python -m http.server` + 헤드리스 크롬 스크린샷.

## Global Constraints

- **근본 자산 불변:** `char/walk.png`·`char/heltori.png` 등 스프라이트는 표시 스케일만 조정. 이미지 파일·색 변경 금지.
- **픽셀 UI 킷 유지:** `.mw-btn`·`.tab-bar`·`.tab-btn`·`.mw-hud`·`.mw-coin`·`.mw-num` 재사용. 라인 SVG·이모지 금지. 색: 블루(#3D7EFF)=메인/액션, 골드(#F5C24B)=머피/별점.
- **단일 파일:** 모든 변경은 `index.html` 안. Firebase 모듈/일반 스코프 브릿지는 `window.*` 규칙 준수.
- **이미지 미변경:** 1단계는 새 이미지 없음 → `_ITEM_V` 불변. 배포 시 `index.html` 2행 `cache-bust: v20260706002` 주석 +1, `sw.js` 버전 +1(가이드 규칙). `MW_DEV_ALWAYS`는 건드리지 않음.
- **고정 캐릭터:** `_charDraft.body !== 'human'`(헬토리 등)이면 꾸미기 잠금 안내 표시.
- **검증 우선:** "고쳤다" 말하기 전 헤드리스 크롬 렌더로 눈 확인.

---

## File Structure

- **Modify only:** `C:\Users\won\Murpy\index.html`
  - CSS: 신규 CSS 거의 없음(인라인 스타일 + 기존 킷 재사용).
  - HTML: `#page-char` 안(라인 854 `</div>` 직전)에 `#mw-dress` 오버레이 추가.
  - JS: `#page-char` 스크립트 영역에 신규 함수(`mwOpenDress`/`mwCloseDress`/`_charRenderHero`/`mwHeroFace`/`_charRefreshPreview`) 추가 + 기존 함수 6곳 소폭 수정.
- **Temp (작업용, 마지막에 제거):** URL 해시 `#dressdemo` 데모 훅(로그인 없이 헤드리스 스크린샷용).

---

## Task 1: 방·캐릭터 크기 키우기 (B-1)

새 그림 없이 상수 2곳만 바꿔 방과 캐릭터를 약 1.5배로. 독립 배포 가능한 작은 승리.

**Files:**
- Modify: `index.html` (라인 831 `.mw-stage` 인라인 스타일, 라인 1751 `_charApplyPos`)

**Interfaces:**
- Consumes: 없음
- Produces: 없음(시각 크기만 변경). `_charApplyPos`의 캐릭터 높이 `DH` 계산식만 바뀜.

- [ ] **Step 1: 방(무대) 표시 크기 확대**

라인 831을 찾는다(현재):
```html
    <div class="mw-stage" style="max-width:min(100%,42vh);margin:0 auto">
```
다음으로 바꾼다:
```html
    <div class="mw-stage" style="max-width:min(100%,54vh);margin:0 auto">
```

- [ ] **Step 2: 방 캐릭터 키비율 확대**

라인 1751을 찾는다(현재):
```js
  const DH = Math.round(t * 3.4), w = Math.round(DH * b.cw / b.ch);
```
다음으로 바꾼다:
```js
  const DH = Math.round(t * 4.0), w = Math.round(DH * b.cw / b.ch);
```

- [ ] **Step 3: 로컬 서버 확인(이미 떠 있으면 생략)**

Run:
```bash
cd /c/Users/won/Murpy && (curl -s -o /dev/null -w "%{http_code}" http://localhost:8777/index.html || python -m http.server 8777 &)
```
Expected: `200` (또는 백그라운드 기동)

- [ ] **Step 4: 헤드리스 크롬으로 JS 콘솔 에러 없이 로드되는지 확인**

Run:
```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu --dump-dom "http://localhost:8777/index.html" 2>/dev/null | grep -c "page-char"
```
Expected: `1` 이상(페이지가 정상 파싱되어 `page-char`가 DOM에 존재). 0이면 로드 실패 → 원인 조사.

- [ ] **Step 5: 대표 로컬 확인 요청(육안)**

머피월드 진입 → 방 안 캐릭터가 이전보다 뚜렷이 커졌는지, 걷기/벽 충돌 정상인지 폰/브라우저에서 확인. (숫자 2곳 변경이라 리스크 낮음. 너무 크면 4.0을 3.7~3.8로, 방을 50vh로 미세조정.)

- [ ] **Step 6: 커밋**

```bash
cd /c/Users/won/Murpy && git add index.html && git commit -m "feat(murpyworld): 방·캐릭터 크기 ~1.5배 확대 (B-1)"
```

---

## Task 2: 꾸미기 전용 화면 (큰 캐릭터 + 돌려보기 + 슬롯)

"꾸미기" → `#page-char` 위 전체 오버레이로 전환. 위: 큰 정면 캐릭터(앞/좌/뒤/우 돌려보기), 아래: 기존 슬롯 탭·아이템 그리드. 옷 바꾸면 큰 프리뷰 즉시 반영. "뒤로"로 방 복귀.

**Files:**
- Modify: `index.html`
  - HTML 추가: 라인 854(`#page-char`의 닫는 `</div>`) 직전에 `#mw-dress` 오버레이.
  - JS 추가: 라인 2043(`window.charHubTab = function`) 직전에 신규 함수 블록.
  - JS 수정: `charHubTab`의 `dress` 분기, `charPick`, `charClearSlot`, `charClearMask`, `charPickColor`.

**Interfaces:**
- Consumes(기존 전역): `window._charDraft`, `window._CHAR_BODIES`, `window._CHAR_LAYER_ORDER`, `window._charEquippedSheets(cfg)`, `window.CHAR_ITEMS`, `window.CHAR_DEFAULT`, `window.getMyCharacter()`, `window._iv(url)`, `window.charSlot(slot, btn)`, `window.charSave()`, `window.getCredits()`, `window._charApplyPos()`, `window._charRenderAvatar()`, `window.charHubTab(name)`.
- Produces(신규 전역):
  - `window._charHeroFace: 'down'|'up'|'left'|'right'` — 큰 프리뷰 현재 방향.
  - `window._charRenderHero(face?)` — `#mw-dress-hero`에 큰 캐릭터 합성.
  - `window.mwHeroFace(face, btn?)` — 방향 전환 + 회전 탭 active.
  - `window.mwOpenDress()` / `window.mwCloseDress()` — 꾸미기 모드 열기/닫기.
  - `window._charRefreshPreview()` — 앞모습 프리뷰(작은) + (열려있으면)큰 프리뷰 동시 갱신.

- [ ] **Step 1: `#mw-dress` 오버레이 HTML 추가**

`index.html` 라인 854(아래 `</div>`가 `#page-char`를 닫음) **직전**에 삽입:
```html
  <!-- 꾸미기 전용 화면 (1단계): page-char 위 전체 오버레이 -->
  <div id="mw-dress" style="display:none;position:fixed;top:0;bottom:0;left:50%;transform:translateX(-50%);width:100%;max-width:390px;z-index:1500;background:#0b0e16;flex-direction:column;font-family:'Galmuri11','Pretendard Variable',sans-serif;image-rendering:pixelated">
    <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px 8px">
      <button class="mw-btn mw-btn-sm" onclick="window.mwCloseDress()">← 뒤로</button>
      <div class="mw-hud"><span class="mw-coin" title="머피"><img src="char/coin.png?v=1" alt="머피" style="width:17px;height:17px;image-rendering:pixelated;display:block"><b class="mw-num" id="mw-dress-coin">0</b></span></div>
    </div>
    <div id="mw-dress-stage" style="flex:1 1 auto;min-height:0;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;padding:6px 0 2px;position:relative">
      <div id="mw-dress-hero"></div>
      <div style="width:56%;max-width:200px;height:12px;margin-top:4px;background:radial-gradient(ellipse at center, rgba(0,0,0,0.45), transparent 70%)"></div>
      <div class="tab-bar" id="mw-dress-rotate" style="margin-top:10px;width:90%;max-width:280px">
        <button class="tab-btn active" onclick="window.mwHeroFace('down',this)">앞</button>
        <button class="tab-btn" onclick="window.mwHeroFace('left',this)">좌</button>
        <button class="tab-btn" onclick="window.mwHeroFace('up',this)">뒤</button>
        <button class="tab-btn" onclick="window.mwHeroFace('right',this)">우</button>
      </div>
    </div>
    <div style="flex:0 0 auto;padding:12px 16px calc(14px + env(safe-area-inset-bottom));background:#0e1320;box-shadow:0 -3px 0 #05070c;max-height:46vh;overflow-y:auto">
      <div class="tab-bar" id="charworld-slot-tabs" style="margin-bottom:12px;flex-wrap:nowrap;overflow-x:auto">
        <button class="tab-btn active" onclick="window.charSlot('hair',this)">헤어</button>
        <button class="tab-btn" onclick="window.charSlot('top',this)">상의</button>
        <button class="tab-btn" onclick="window.charSlot('bottom',this)">하의</button>
        <button class="tab-btn" onclick="window.charSlot('shoes',this)">신발</button>
        <button class="tab-btn" onclick="window.charSlot('hat',this)">모자</button>
        <button class="tab-btn" onclick="window.charSlot('acc',this)">악세사리</button>
        <button class="tab-btn" onclick="window.charSlot('color',this)">색상</button>
      </div>
      <div id="charworld-items" style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px"></div>
      <div id="mw-dress-lock" style="display:none;text-align:center;margin-top:12px;font-size:12px;color:#8a93a8;line-height:1.6"></div>
      <button class="mw-btn" style="width:100%;margin-top:16px" onclick="window.charSave()">저장</button>
    </div>
  </div>
```

- [ ] **Step 2: 신규 JS 함수 블록 추가**

라인 2043 `window.charHubTab = function (name, btn) {` **직전**에 삽입:
```js
// ===== 꾸미기 전용 화면 (1단계) =====
window._charHeroFace = 'down';
// 큰 정면/방향 캐릭터: 기존 레이어 합성을 face(행) + 큰 크기로. #mw-dress-hero에 그림.
window._charRenderHero = function (face) {
  face = face || window._charHeroFace || 'down';
  window._charHeroFace = face;
  const el = document.getElementById('mw-dress-hero'); if (!el) return;
  const cfg = window._charDraft || (window.getMyCharacter ? window.getMyCharacter() : window.CHAR_DEFAULT) || {};
  const b = window._CHAR_BODIES[(cfg && cfg.body) || 'human'] || window._CHAR_BODIES.human;
  const stage = document.getElementById('mw-dress-stage');
  const availH = (stage && stage.clientHeight) ? stage.clientHeight : Math.round(window.innerHeight * 0.5);
  const availW = (stage && stage.clientWidth) ? stage.clientWidth : window.innerWidth;
  let H = Math.round(availH * 0.72);                 // 회전탭·받침대 여백 감안
  let w = Math.round(H * b.cw / b.ch);
  const maxW = Math.round(availW * 0.8);
  if (w > maxW) { w = maxW; H = Math.round(w * b.ch / b.cw); }   // 폭이 넘치면 폭 기준
  const row = face === 'up' ? 1 : (face === 'left' ? 2 : (face === 'right' ? 3 : 0)); // 시트 4행[아래0/위1/좌2/우3]
  const sheets = window._charEquippedSheets(cfg);
  const layer = function (url) {
    return "<div style=\"position:absolute;left:0;top:0;width:" + w + "px;height:" + H + "px;"
      + "background-image:url('" + url + "');background-repeat:no-repeat;"
      + "background-size:" + (w * 3) + "px " + (H * 4) + "px;background-position:0 " + (-row * H) + "px;"
      + "image-rendering:pixelated\"></div>";
  };
  let html = "<div style=\"position:relative;width:" + w + "px;height:" + H + "px;margin:0 auto;"
    + "filter:drop-shadow(0 4px 3px rgba(0,0,0,0.4))\">";
  window._CHAR_LAYER_ORDER.forEach(function (s) { if (sheets[s]) html += layer(sheets[s]); });
  el.innerHTML = html + "</div>";
  el.style.width = w + 'px'; el.style.height = H + 'px';
};
window.mwHeroFace = function (face, btn) {
  if (btn) document.querySelectorAll('#mw-dress-rotate .tab-btn').forEach(function (b) { b.classList.toggle('active', b === btn); });
  window._charRenderHero(face);
};
// 앞모습(작은) + 큰 프리뷰 동시 갱신 — 옷 바꿀 때 호출
window._charRefreshPreview = function () {
  window._charRenderAvatar && window._charRenderAvatar();
  const dress = document.getElementById('mw-dress');
  if (dress && dress.style.display !== 'none') window._charRenderHero(window._charHeroFace);
};
window.mwOpenDress = function () {
  const src = window._charDraft || (window.getMyCharacter ? window.getMyCharacter() : window.CHAR_DEFAULT);
  window._charDraft = Object.assign({}, src || {});
  if (!window._charDraft.body) window._charDraft.body = 'human';
  const dress = document.getElementById('mw-dress'); if (!dress) return;
  const amt = document.getElementById('mw-dress-coin');
  if (amt) amt.textContent = (window.getCredits ? window.getCredits() : 0);
  const isHuman = ((window._charDraft.body || 'human') === 'human');
  const lock = document.getElementById('mw-dress-lock');
  const tabs = document.getElementById('charworld-slot-tabs');
  const items = document.getElementById('charworld-items');
  if (isHuman) {
    if (lock) lock.style.display = 'none';
    if (tabs) tabs.style.display = '';
    if (items) items.style.display = '';
  } else {
    const nm = ((window._CHAR_BODIES[window._charDraft.body] || {}).name || '이 캐릭터');
    if (lock) { lock.innerHTML = nm + '는 <b style="color:#cfd6e6">고정 캐릭터</b>예요 · 꾸미기는 사람 캐릭터에서!'; lock.style.display = ''; }
    if (tabs) tabs.style.display = 'none';
    if (items) items.style.display = 'none';
  }
  window._charHeroFace = 'down';
  document.querySelectorAll('#mw-dress-rotate .tab-btn').forEach(function (b, i) { b.classList.toggle('active', i === 0); });
  dress.style.display = 'flex';
  requestAnimationFrame(function () {
    window._charRenderHero('down');
    if (isHuman) window.charSlot('hair', document.querySelector('#charworld-slot-tabs .tab-btn'));
  });
};
window.mwCloseDress = function () {
  const dress = document.getElementById('mw-dress'); if (dress) dress.style.display = 'none';
  window.charHubTab && window.charHubTab('me');
  window._charApplyPos && window._charApplyPos();
};
// 오리엔테이션/리사이즈 시 큰 프리뷰 재계산
window.addEventListener('resize', function () {
  const dress = document.getElementById('mw-dress');
  if (dress && dress.style.display !== 'none') window._charRenderHero(window._charHeroFace);
});
```

- [ ] **Step 3: `charHubTab`의 `dress` 분기를 오버레이 오픈으로 교체**

라인 2052~2069의 `else if (name === 'dress') { ... }` 블록 전체(현재는 슬롯탭/아이템 마크업을 `#charworld-hub-panel`에 채우고 `_charRenderAvatar`/`charSlot('hair')` 호출)를 다음으로 교체:
```js
  } else if (name === 'dress') {
    window.mwOpenDress();
    return;
```
(주의: `#charworld-slot-tabs`·`#charworld-items` 마크업은 이제 Step 1의 `#mw-dress` 안에만 존재. 기존 hub-panel 버전은 이 교체로 사라짐.)

- [ ] **Step 4: 옷 변경 시 큰 프리뷰도 갱신되도록 4개 함수 수정**

`charClearMask`(라인 1953): `window._charRenderAvatar();` → `window._charRefreshPreview();`
```js
window.charClearMask = function () { if (!window._charDraft) return; window._charDraft.mask = null; window._charRefreshPreview(); window.charSlot('mask', document.querySelector('#charworld-slot-tabs .tab-btn.active')); };
```

`charClearSlot`(라인 1957): `window._charRenderAvatar(); window._charApplyPos();` → `window._charRefreshPreview(); window._charApplyPos();`
```js
  window._charRefreshPreview(); window._charApplyPos();   // 프리뷰(작은/큰) + 걷는 캐릭터 반영
```

`charPickColor`(라인 1960): `window._charRenderAvatar();` → `window._charRefreshPreview();`
```js
window.charPickColor = function (kind, c) { if (!window._charDraft) return; window._charDraft[kind] = c; window._charRefreshPreview(); };
```

`charPick`(라인 1978): `window._charRenderAvatar();` → `window._charRefreshPreview();`
```js
  window._charRefreshPreview();
  window._charApplyPos();     // 걷는 캐릭터에 즉시 반영
```

- [ ] **Step 5: 헤드리스 스크린샷용 데모 훅 추가(임시, Step 10에서 제거)**

Step 2에서 추가한 JS 블록의 **맨 끝**(`window.addEventListener('resize'...)` 다음)에 삽입:
```js
// [임시] 헤드리스 스크린샷용: index.html#dressdemo 또는 #dressdemo:left 로 로그인 없이 꾸미기 화면 미리보기
if (location.hash.indexOf('dressdemo') !== -1) {
  window.addEventListener('load', function () {
    setTimeout(function () {
      window._charDraft = { body: 'human', hair: null, hairColor: null, top: 'top_redhood', topColor: null, bottom: 'bottom_bermuda', shoes: 'shoes_black', hat: 'hat_gbd', acc: null, mask: null };
      const pc = document.getElementById('page-char'); if (pc) pc.classList.add('active');
      window.mwOpenDress();
      const f = (location.hash.split(':')[1] || 'down');
      if (f !== 'down') setTimeout(function () { window._charRenderHero(f); }, 350);
    }, 400);
  });
}
```

- [ ] **Step 6: 로컬 서버 확인 + 정면 스크린샷**

Run:
```bash
cd /c/Users/won/Murpy && curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8777/index.html
OUT="/c/Users/won/AppData/Local/Temp/claude/C--Users-won/c55b385e-426a-402f-a5d6-17344dd9b835/scratchpad"
"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu --hide-scrollbars --window-size=390,780 --force-device-scale-factor=2 --screenshot="$OUT/dress_front.png" "http://localhost:8777/index.html#dressdemo" 2>/dev/null
```
Expected: `200`, `dress_front.png` 생성.

- [ ] **Step 7: 정면 스크린샷 육안 확인**

`dress_front.png`를 Read로 열어 확인:
- 위쪽에 **큰 캐릭터**(레드후드 + 회색 버뮤다 + 검정 신발 + GBD 캡)가 정면으로 크게.
- 아래에 슬롯 탭(헤어/상의/…/색상)과 아이템 그리드, 저장 버튼.
- 상단 "← 뒤로", 우측 머피 코인 HUD.
- 가로 스크롤 없음, 겹침 없음.
문제 있으면 원인 조사 후 수정(레이어 어긋남=배경위치/크기 계산 재확인).

- [ ] **Step 8: 4방향 돌려보기 스크린샷**

Run:
```bash
OUT="/c/Users/won/AppData/Local/Temp/claude/C--Users-won/c55b385e-426a-402f-a5d6-17344dd9b835/scratchpad"
for f in left up right; do
  "/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu --hide-scrollbars --window-size=390,780 --force-device-scale-factor=2 --screenshot="$OUT/dress_$f.png" "http://localhost:8777/index.html#dressdemo:$f" 2>/dev/null
done
```
Expected: `dress_left.png`, `dress_up.png`, `dress_right.png` 생성.

- [ ] **Step 9: 4방향 육안 확인**

`dress_left.png`(좌측면), `dress_up.png`(뒷모습), `dress_right.png`(우측면)를 Read로 확인:
- 각 방향의 정지 프레임이 맞게 뜨는지(뒤=머리 뒤통수, 좌/우=옆모습).
- 착용 아이템이 모든 방향에서 캐릭터에 정합(신발·바지·상의·모자 안 어긋남).
어긋나면 `row` 매핑(`up=1,left=2,right=3`) 또는 배경 위치 재확인.

- [ ] **Step 10: 데모 훅 제거**

Step 5에서 추가한 `if (location.hash.indexOf('dressdemo') !== -1) { ... }` 블록 전체를 삭제.

- [ ] **Step 11: 훅 제거 후 회귀 확인(정상 로드)**

Run:
```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu --dump-dom "http://localhost:8777/index.html" 2>/dev/null | grep -c "mw-dress"
```
Expected: `1` 이상(`#mw-dress` 마크업 존재, JS 파싱 정상). 0이면 문법 오류 → 조사.

- [ ] **Step 12: 대표 로컬 확인 요청(실사용 흐름)**

로그인 상태에서 머피월드 → "꾸미기" → 큰 캐릭터 화면 뜨는지, 앞/좌/뒤/우 돌려보기, 옷 바꾸면 **큰 화면에 즉시 반영**되는지, 저장/뒤로가 정상인지, 고정 캐릭터(헬토리) 선택 시 잠금 안내 뜨는지 확인.

- [ ] **Step 13: 캐시버스트 주석 갱신**

`index.html` 2행 `cache-bust: v20260706002` → `v20260707001` 로 수정.

- [ ] **Step 14: 커밋**

```bash
cd /c/Users/won/Murpy && git add index.html && git commit -m "feat(murpyworld): 꾸미기 전용 화면(큰 캐릭터+4방향 돌려보기) 1단계"
```

---

## Self-Review (작성자 점검 결과)

**1. Spec coverage:**
- A. 꾸미기 전용 화면(위 큰 캐릭터/아래 슬롯) → Task 2 (Step 1~4).
- 돌려보기(앞/좌/뒤/우) → Task 2 (`_charRenderHero(face)`, `mwHeroFace`, Step 8~9).
- 옷 변경 즉시 반영 → Task 2 Step 4(`_charRefreshPreview`).
- 진입/이탈(꾸미기 버튼 트리거, 2단계에서 옷장이 `mwOpenDress` 호출) → Task 2 Step 3 + `mwOpenDress` 함수 경계.
- 고정 캐릭터 잠금 → `mwOpenDress`의 isHuman 분기.
- B. 방 캐릭터 ~1.5배 → Task 1.
- 새 이미지 없음/캐시버스트·sw.js/`MW_DEV_ALWAYS` 불변 → Global Constraints + Task 2 Step 13.
- 검증(헤드리스, 좁은/큰 폭) → Task 2 Step 6~9, 390px 창. (큰 폭은 max-width:390 고정이라 데스크톱서도 폰폭으로 렌더 = 겹침 위험 낮음.)
누락 없음.

**2. Placeholder scan:** "TBD/TODO/적절히" 등 없음. 모든 코드 스텝에 실제 코드 포함.

**3. Type consistency:** 신규 전역 이름 일관 확인 — `_charHeroFace`, `_charRenderHero`, `mwHeroFace`, `mwOpenDress`, `mwCloseDress`, `_charRefreshPreview`. `charHubTab`/`charSlot`/`charSave`/`_charEquippedSheets`/`_CHAR_LAYER_ORDER` 시그니처 기존과 일치. `#mw-dress`·`#mw-dress-hero`·`#mw-dress-stage`·`#mw-dress-rotate`·`#mw-dress-coin`·`#mw-dress-lock`·`#charworld-slot-tabs`·`#charworld-items` id 일관.

**주의 사항(구현자용):** 라인 번호는 편집으로 밀리므로 각 스텝의 **코드 스니펫(현재→변경)** 을 기준으로 위치를 찾을 것. 라인 번호는 참고용.
