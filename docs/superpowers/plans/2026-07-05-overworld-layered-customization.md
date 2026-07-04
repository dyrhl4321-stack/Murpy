# 머피월드 오버월드 다층 의상 레이어링 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 머피월드에서 걷는 캐릭터에 머리·상의·하의·모자를 자유 조합으로 실시간 입히는 다층 스프라이트 레이어 엔진을 지금 스택(쌩 JS + CSS) 위에 구현한다.

**Architecture:** `#charworld-avatar` 단일 배경 div를 **컨테이너**로 바꾸고, 내부에 슬롯별 겹 div(body/bottom/top/hair/hat)를 z-order로 쌓는다. `_charApplyPos()`가 지오메트리(w/DH/backgroundSize/backgroundPosition)를 한 번 계산해 **모든 겹에 복사**하므로 런타임에서 어긋날 수 없다. 위치·미러·바운스·스쿼시는 컨테이너에만 적용해 전체 겹이 함께 움직인다.

**Tech Stack:** Vanilla JS, CSS transition, `background-position` 스프라이트, Python/PIL(임시 시트 생성), 로컬 `python -m http.server 8777` 육안 검증.

## Global Constraints

- 대상 파일: `C:\Users\won\Murpy\index.html` (단일 HTML). 테스트 프레임워크 없음 → 검증은 로컬 브라우저 육안 + 스탠드얼론 하니스.
- 스프라이트 규격: **3열(0정지/1걸음A/2걸음B) × 3행(0아래/1위/2옆). 오른쪽 = 옆행 `scaleX(-1)` 미러.**
- 셀 크기 고정 금지: `DH=round(t*3.4)`, `w=round(DH*cw/ch)` (t=타일 픽셀, cw/ch=`_CHAR_BODIES[body]`).
- 슬롯 z순서(뒤→앞): `body → bottom → shoes → top → hair → hat`.
- 사람(human) 몸통만 의상 지원. 헬토리는 통짜 스킨 유지(의상 겹 없음).
- 이 계획 범위 밖: 상점 머피 차감/Firestore 동기화(다음 스펙), 실제 아트, 색 tint, 대숲 가면.
- 로컬 배포 안 함(프로토타입). SW 캐시로 옛화면이면 Ctrl+Shift+R.
- 설계 근거: `docs/superpowers/specs/2026-07-05-overworld-layered-customization-design.md`.

---

### Task 1: 다층 레이어 엔진 (컨테이너화 + `_charApplyPos` 리팩터)

기존 걷기가 **똑같이 보이면서**, 내부적으로 body를 자식 겹으로 렌더하도록 바꾼다(행동 보존). 이후 태스크가 옷 겹을 얹을 토대.

**Files:**
- Modify: `index.html` — `_CHAR_LAYER_ORDER`/`_charBuildLayers`/`_charEquippedSheets` 신설(약 `:1636` 근처, `_charPos` 선언 뒤), `_charApplyPos` 교체(`:1698-1715`), `_charApplySprite` 교체(`:1692-1696`).

**Interfaces:**
- Produces:
  - `window._CHAR_LAYER_ORDER: string[]` = `['body','bottom','shoes','top','hair','hat']`
  - `window._charBuildLayers(): void` — `#charworld-avatar` 안에 `.cw-layer[data-slot]` 겹 생성(멱등), 컨테이너 자체 배경 제거.
  - `window._charEquippedSheets(cfg): {body,bottom,shoes,top,hair,hat}` — 각 값은 시트 URL 또는 null.
  - `window._charApplyPos(): void` — 컨테이너 위치/크기/미러 + 모든 겹에 좌표 복사.
- Consumes: `_charTileGeom()`, `_CHAR_BODIES`, `_charPos`, `_charDraft`, `getMyCharacter`, `CHAR_DEFAULT`, `CHAR_ITEMS`.

- [ ] **Step 1: 기준 동작 확인(회귀 베이스라인)**

`cd /c/Users/won/Murpy && python -m http.server 8777` 실행(백그라운드). 브라우저에서 `http://localhost:8777` → 로그인 → 머피월드 탭 진입. 방향키/드래그로 상하좌우 걷기. **현재 사람 캐릭터가 정상적으로 걷는 모습**을 기억(스크린샷). 이게 Task 1 후에도 동일해야 한다.

- [ ] **Step 2: 레이어 헬퍼 3종 추가**

`index.html`에서 `window._charPos = { tc: 7, tr: 10, ... };`(약 `:1637`) 바로 아래에 삽입:

```javascript
// ===== 다층 의상 레이어 =====
window._CHAR_LAYER_ORDER = ['body', 'bottom', 'shoes', 'top', 'hair', 'hat']; // 뒤→앞 z순서
window._charBuildLayers = function () {
  const host = document.getElementById('charworld-avatar'); if (!host) return;
  if (host._layersBuilt) return;
  host.style.backgroundImage = 'none';           // 컨테이너화: 자체 배경 제거
  window._CHAR_LAYER_ORDER.forEach(function (slot, i) {
    const d = document.createElement('div');
    d.className = 'cw-layer'; d.dataset.slot = slot;
    d.style.cssText = 'position:absolute;left:0;top:0;background-repeat:no-repeat;image-rendering:auto;pointer-events:none;z-index:' + i;
    host.appendChild(d);
  });
  host._layersBuilt = true;
};
window._charEquippedSheets = function (cfg) {
  cfg = cfg || {};
  const b = window._CHAR_BODIES[cfg.body || 'human'] || window._CHAR_BODIES.human;
  const out = { body: b.src, bottom: null, shoes: null, top: null, hair: null, hat: null };
  ['bottom', 'shoes', 'top', 'hair', 'hat'].forEach(function (slot) {
    const id = cfg[slot]; if (!id) return;
    const item = (window.CHAR_ITEMS || []).find(function (x) { return x.id === id && x.slot === slot; });
    out[slot] = (item && item.sheet) ? item.sheet : null;   // 시트 없는(SVG전용) 아이템은 겹 없음
  });
  return out;
};
```

- [ ] **Step 3: `_charApplyPos` 교체 (컨테이너 + 겹 복사)**

기존 `window._charApplyPos = function () { ... };`(`:1698-1715`) 전체를 아래로 교체:

```javascript
// 타일좌표 → 픽셀 + 방향/프레임을 모든 겹에 복사. 발끝을 타일 바닥 중앙에 정렬.
window._charApplyPos = function () {
  const host = document.getElementById('charworld-avatar'); if (!host) return;
  window._charBuildLayers();
  const g = window._charTileGeom(), t = g.t;
  const cfg = window._charDraft || (window.getMyCharacter ? window.getMyCharacter() : window.CHAR_DEFAULT) || {};
  const b = window._CHAR_BODIES[cfg.body || 'human'] || window._CHAR_BODIES.human;
  const DH = Math.round(t * 3.4), w = Math.round(DH * b.cw / b.ch);
  window._SPR.w = w; window._SPR.h = DH;
  // 컨테이너: 크기/위치/미러 (바운스=translate, 스쿼시=scale 는 charMove가 별도 적용)
  host.style.width = w + 'px'; host.style.height = DH + 'px';
  const feetX = (window._charPos.tc + 0.5) * t, feetY = (window._charPos.tr + 1) * t;
  host.style.left = (feetX - w / 2) + 'px';
  host.style.top = (feetY - DH) + 'px';
  const face = window._charPos.face || 'down';
  host.style.transform = 'scaleX(' + (face === 'right' ? -1 : 1) + ')';
  // 겹: 같은 좌표를 전부 복사 → 절대 안 어긋남
  const row = face === 'up' ? 1 : (face === 'down' ? 0 : 2);
  const col = window._charPos.frame || 0;
  const posX = (-col * w), posY = (-row * DH);
  const sheets = window._charEquippedSheets(cfg);
  host.querySelectorAll('.cw-layer').forEach(function (el) {
    const url = sheets[el.dataset.slot];
    if (!url) { el.style.display = 'none'; return; }
    el.style.display = '';
    el.style.backgroundImage = "url('" + url + "')";
    el.style.width = w + 'px'; el.style.height = DH + 'px';
    el.style.backgroundSize = (w * 3) + 'px ' + (DH * 3) + 'px';
    el.style.backgroundPosition = posX + 'px ' + posY + 'px';
  });
};
```

- [ ] **Step 4: `_charApplySprite` 를 리다이렉트로 교체**

기존 `window._charApplySprite = function (body) { ... };`(`:1692-1696`)를 아래로 교체(몸통은 이제 겹에서 처리):

```javascript
// 캐릭터 종류 변경 시 겹 다시 반영 (몸통 시트는 _charEquippedSheets가 cfg.body로 처리)
window._charApplySprite = function (/* body */) { window._charApplyPos && window._charApplyPos(); };
```

- [ ] **Step 5: 회귀 검증 (걷기 동일해야 함)**

`http://localhost:8777` **Ctrl+Shift+R** → 머피월드 진입 → 상하좌우 걷기. 확인:
- 사람 캐릭터가 Step 1 스크린샷과 **동일하게** 걷는다(정지/걸음A/걸음B 교차, 오른쪽 미러, 위/아래/옆 방향).
- 콘솔 에러 없음. 크롬 DevTools에서 `#charworld-avatar` 안에 `.cw-layer[data-slot="body"]`가 있고 배경이 walk.png인지 확인.

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "머피월드: 다층 레이어 엔진 토대(컨테이너화, body 겹 렌더) — 행동 보존"
```

---

### Task 2: 임시 옷 시트 생성 + 정합 검증 하니스

로그인/Firebase 없이 정합을 눈으로 검증할 스탠드얼론 하니스를 만들고, PIL로 격자에 정확히 맞는 임시 시트 4장을 생성해 엔진이 실제로 겹쳐 걷는지 증명한다.

**Files:**
- Create: `char/build_item_placeholders.py` (임시 시트 생성기)
- Create: `char/items/bottom_ph.png`, `char/items/shoes_ph.png`, `char/items/top_ph.png`, `char/items/hair_ph.png`, `char/items/hat_ph.png` (생성물)
- Create: `char/_layer_preview.html` (스탠드얼론 정합 하니스)
- Modify: `index.html` — `CHAR_ITEMS`에 시트 달린 항목 4개 추가(`:1596-1605`)

**Interfaces:**
- Consumes: Task 1의 `_charEquippedSheets`(하니스에서 규격 참조), `char/walk.png`.
- Produces: `char/items/<slot>_ph.png` 5장(각 walk.png와 동일 픽셀 규격), `CHAR_ITEMS` 신규 5항목(각 `sheet` 필드).

- [ ] **Step 1: 임시 시트 생성기 작성**

`char/build_item_placeholders.py` 생성:

```python
# walk.png 격자에 정확히 맞는 임시 의상 시트 생성(엔진 정합 검증용).
# 각 슬롯은 반투명 색 띠 + 셀마다 col/row 마커(desync 시 어긋남이 보이도록).
from PIL import Image, ImageDraw

SRC = "walk.png"           # char/ 에서 실행
COLS, ROWS = 3, 3
base = Image.open(SRC)
CW, CH = base.width // COLS, base.height // ROWS   # 셀 픽셀(예: 137 x 224)

# 슬롯별: (색 RGBA, 세로 밴드 y비율 start~end, 가로 x비율)
SLOTS = {
    "hat_ph":    ((60, 90, 240, 190), 0.06, 0.18, 0.30, 0.70),
    "hair_ph":   ((30, 30, 40, 170),  0.12, 0.30, 0.28, 0.72),
    "top_ph":    ((240, 80, 80, 175), 0.42, 0.62, 0.24, 0.76),
    "bottom_ph": ((80, 200, 120, 175),0.60, 0.80, 0.30, 0.70),
    "shoes_ph":  ((210, 160, 60, 190),0.82, 0.96, 0.28, 0.72),
}

def build(name, rgba, y0, y1, x0, x1):
    img = Image.new("RGBA", (base.width, base.height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for r in range(ROWS):
        for c in range(COLS):
            ox, oy = c * CW, r * CH
            # 의상 밴드
            d.rectangle([ox + CW * x0, oy + CH * y0, ox + CW * x1, oy + CH * y1], fill=rgba)
            # 디버그 마커: 좌상단에 col개 세로점 + row개 가로점 (프레임 desync 감지)
            for i in range(c + 1):
                d.rectangle([ox + 4 + i * 6, oy + 4, ox + 8 + i * 6, oy + 8], fill=(255, 255, 0, 255))
            for i in range(r + 1):
                d.rectangle([ox + 4, oy + 12 + i * 6, ox + 8, oy + 16 + i * 6], fill=(0, 255, 255, 255))
    img.save(f"items/{name}.png")
    print("saved", name, img.size)

import os
os.makedirs("items", exist_ok=True)
for name, args in SLOTS.items():
    build(name, *args)
```

- [ ] **Step 2: 생성 실행 + 결과 확인**

Run:
```bash
cd /c/Users/won/Murpy/char && python build_item_placeholders.py
```
Expected 출력: `saved hat_ph ...` 등 5줄, 크기 = walk.png와 동일. `char/items/`에 png 5개 존재.

- [ ] **Step 3: 스탠드얼론 정합 하니스 작성**

`char/_layer_preview.html` 생성(로그인 없이 겹 정합만 확인):

```html
<!doctype html><meta charset="utf-8"><title>레이어 정합 하니스</title>
<style>
  body{background:#20272f;color:#ccd;font-family:sans-serif;margin:16px}
  #stage{position:relative;width:220px;height:360px;background:#2c343d;margin:10px 0;outline:1px solid #445}
  #av{position:absolute;left:30px;top:60px}
  .cw-layer{position:absolute;left:0;top:0;background-repeat:no-repeat;image-rendering:auto}
  button{margin:2px}
</style>
<div>방향:
  <button onclick="setFace('down')">아래</button><button onclick="setFace('up')">위</button>
  <button onclick="setFace('left')">왼쪽</button><button onclick="setFace('right')">오른쪽</button>
  · 프레임: <button onclick="setCol(0)">정지</button><button onclick="setCol(1)">A</button><button onclick="setCol(2)">B</button>
</div>
<div id="stage"><div id="av"></div></div>
<script>
const BODY = 'walk.png?v=7', CW = 137, CH = 224;           // human 셀 규격
const SHEETS = ['body', 'bottom', 'shoes', 'top', 'hair', 'hat'];   // 뒤→앞 z순서
const URLS = { body: BODY, bottom: 'items/bottom_ph.png', shoes: 'items/shoes_ph.png', top: 'items/top_ph.png', hair: 'items/hair_ph.png', hat: 'items/hat_ph.png' };
const DH = 300, W = Math.round(DH * CW / CH);
let face = 'down', col = 0;
const av = document.getElementById('av');
SHEETS.forEach((slot, i) => { const d = document.createElement('div'); d.className='cw-layer'; d.dataset.slot=slot; d.style.zIndex=i; av.appendChild(d); });
function apply(){
  const row = face==='up'?1:(face==='down'?0:2);
  av.style.width=W+'px'; av.style.height=DH+'px';
  av.style.transform='scaleX('+(face==='right'?-1:1)+')';
  av.querySelectorAll('.cw-layer').forEach(el=>{
    el.style.backgroundImage="url('"+URLS[el.dataset.slot]+"')";
    el.style.width=W+'px'; el.style.height=DH+'px';
    el.style.backgroundSize=(W*3)+'px '+(DH*3)+'px';
    el.style.backgroundPosition=(-col*W)+'px '+(-row*DH)+'px';
  });
}
window.setFace=f=>{face=f;apply()}; window.setCol=c=>{col=c;apply()}; apply();
</script>
```

- [ ] **Step 4: 하니스로 정합 검증**

`http://localhost:8777/char/_layer_preview.html` 열기. 각 방향·프레임 버튼을 누르며 확인:
- 5장 임시 밴드(모자=파랑/머리=검정/상의=빨강/하의=초록/신발=갈색)가 **몸통과 함께** 이동하고 프레임이 바뀐다.
- **좌상단 마커(노란 세로점=col, 청록 가로점=row)가 몸통 프레임과 모든 겹에서 동일**(예: 걸음B면 노란 점 3개, 모든 겹 일치) → 프레임 desync 없음 확인.
- 오른쪽 방향에서 전체가 함께 미러됨.

문제 있으면 Task 1의 좌표 복사 로직을 수정 후 재확인.

- [ ] **Step 5: `CHAR_ITEMS`에 시트 항목 추가**

`index.html`의 `window.CHAR_ITEMS = [ ... ];`(`:1596-1605`) 배열 끝(`];` 직전)에 4항목 추가:

```javascript
  { id: 'hair_ph', slot: 'hair', name: '머리(샘플)', price: 0, sheet: 'char/items/hair_ph.png' },
  { id: 'top_ph', slot: 'top', name: '상의(샘플)', price: 0, sheet: 'char/items/top_ph.png' },
  { id: 'bottom_ph', slot: 'bottom', name: '하의(샘플)', price: 0, sheet: 'char/items/bottom_ph.png' },
  { id: 'shoes_ph', slot: 'shoes', name: '신발(샘플)', price: 0, sheet: 'char/items/shoes_ph.png' },
  { id: 'hat_ph', slot: 'hat', name: '모자(샘플)', price: 0, sheet: 'char/items/hat_ph.png' },
```

- [ ] **Step 6: Commit**

```bash
git add char/build_item_placeholders.py char/items/ char/_layer_preview.html index.html
git commit -m "머피월드: 임시 의상 시트 생성기 + 정합 검증 하니스 + 시트 카탈로그 항목"
```

---

### Task 3: 꾸미기 UI 슬롯 확장(하의·신발·모자) + 실시간 반영

꾸미기 패널에 하의·신발·모자 탭을 추가하고, 아이템 선택/해제 시 **걷는 캐릭터에 즉시** 반영되게 배선한다.

**Files:**
- Modify: `index.html` — 슬롯 탭 마크업(`:1955-1959`), `CHAR_DEFAULT`(`:1589`), `charPick`(`:1875-1877`), `charSlot`의 "안 입기" 처리(`:1852-1855` 패턴 확장), `charClearMask` 옆에 범용 clear 추가.

**Interfaces:**
- Consumes: Task 1 `_charApplyPos`, Task 2 `CHAR_ITEMS`(sheet).
- Produces: `window.charClearSlot(slot): void` — 해당 슬롯 벗기 + 반영.

- [ ] **Step 1: 슬롯 탭에 하의·모자 추가**

`index.html`의 슬롯 탭 마크업(`:1956-1959`)에서 상의 버튼 뒤에 두 줄 추가하고 순서 정리:

```javascript
      + '<button class="tab-btn active" onclick="window.charSlot(\'hair\',this)">헤어</button>'
      + '<button class="tab-btn" onclick="window.charSlot(\'top\',this)">상의</button>'
      + '<button class="tab-btn" onclick="window.charSlot(\'bottom\',this)">하의</button>'
      + '<button class="tab-btn" onclick="window.charSlot(\'shoes\',this)">신발</button>'
      + '<button class="tab-btn" onclick="window.charSlot(\'hat\',this)">모자</button>'
      + '<button class="tab-btn" onclick="window.charSlot(\'color\',this)">색상</button>'
      + '<button class="tab-btn" onclick="window.charSlot(\'mask\',this)">가면</button></div>'
```

- [ ] **Step 2: `CHAR_DEFAULT`에 슬롯 기본값 추가**

`window.CHAR_DEFAULT = { ... };`(`:1589`)에 `bottom: null, hat: null` 추가:

```javascript
window.CHAR_DEFAULT = { skin: '#F0C9A0', hair: 'hair_short', hairColor: '#2B2B2B', top: 'top_tee', topColor: '#3D7EFF', bottom: null, shoes: null, hat: null, mask: null, body: 'human' };
```

- [ ] **Step 3: 범용 "벗기" 함수 추가 + charSlot에 벗기 버튼**

`window.charClearMask = ...`(`:1857`) 바로 아래에 추가:

```javascript
window.charClearSlot = function (slot) {
  if (!window._charDraft) return;
  window._charDraft[slot] = null;
  window._charRenderAvatar(); window._charApplyPos();   // 프리뷰 + 걷는 캐릭터 반영
  window.charSlot(slot, document.querySelector('#charworld-slot-tabs .tab-btn.active'));
};
```

그리고 `charSlot`의 mask 전용 "안 씀" 블록(`:1852-1855`)을 hair/top/bottom/hat/mask 공용으로 확장. 해당 블록을 아래로 교체:

```javascript
  if (['hair', 'top', 'bottom', 'shoes', 'hat', 'mask'].includes(slot)) {
    const isMask = slot === 'mask';
    const off = isMask ? !window._charDraft.mask : !window._charDraft[slot];
    const onclick = isMask ? 'window.charClearMask()' : "window.charClearSlot('" + slot + "')";
    grid.insertAdjacentHTML('afterbegin', `<button class="mw-card${off ? ' equipped' : ''}" onclick="${onclick}" style="justify-content:center;min-height:96px"><span class="mw-name">안 씀</span><span class="mw-sub${off ? ' on' : ''}">${off ? '착용중' : '벗기'}</span></button>`);
  }
```

- [ ] **Step 4: 아이템 선택 시 걷는 캐릭터 반영**

`charPick`의 끝부분(`:1875-1877`)을 아래로 교체(프리뷰 갱신 뒤 `_charApplyPos` 추가):

```javascript
  window._charDraft[item.slot] = id;
  window._charRenderAvatar();
  window._charApplyPos();     // 걷는 캐릭터에 즉시 반영
  window.charSlot(item.slot, document.querySelector('#charworld-slot-tabs .tab-btn.active'));
```

- [ ] **Step 5: 실기 검증(실시간 조합)**

`http://localhost:8777` Ctrl+Shift+R → 머피월드 → 꾸미기(dress) 탭. 확인:
- 탭에 헤어/상의/하의/신발/모자/색상/가면 7개 보임.
- 하의(샘플)·신발(샘플)·모자(샘플) 등 각 슬롯 아이템 선택 시 **방에서 걷는 캐릭터에 해당 색 밴드가 즉시** 붙는다.
- 여러 슬롯 동시 착용(예: 모자+상의+하의+신발) → 겹이 z순서대로(모자 최상단) 함께 걷는다.
- "안 씀" 누르면 그 겹만 사라짐. 걸어도 정합 유지.

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "머피월드: 꾸미기 5슬롯(하의·모자 추가) + 착용/벗기 걷는 캐릭터 실시간 반영"
```

---

### Task 4: 정면 프리뷰를 시트 합성으로 통일(WYSIWYG)

꾸미기 화면 앞모습 프리뷰를 오버월드와 **같은 시트(정면·정지 프레임)**로 합성해 "보이는 대로 걷는다"를 보장한다. 시트 없는(SVG전용) 아이템은 기존 SVG 폴백 유지.

**Files:**
- Modify: `index.html` — `_charRenderAvatar`(`:1640-1652`), 안내 문구(`:1954`).

**Interfaces:**
- Consumes: Task 1 `_charEquippedSheets`, `_CHAR_LAYER_ORDER`, `_CHAR_BODIES`, `_CHAR_DISPLAY_H`.

- [ ] **Step 1: `_charRenderAvatar` 시트 합성으로 교체**

`window._charRenderAvatar = function () { ... };`(`:1640-1652`) 전체를 교체:

```javascript
// 앞모습 프리뷰 = 오버월드와 동일 시트(down/정지 프레임) 겹 합성 → WYSIWYG.
// 시트가 있는 슬롯은 시트로, 없으면(SVG전용) 아래 renderCharacter 폴백에 맡김.
window._charRenderAvatar = function () {
  const el = document.getElementById('charworld-preview');
  if (!el) return;
  const cfg = window._charDraft || (window.getMyCharacter ? window.getMyCharacter() : window.CHAR_DEFAULT);
  const b = window._CHAR_BODIES[(cfg && cfg.body) || 'human'] || window._CHAR_BODIES.human;
  const H = window._CHAR_DISPLAY_H || 88, w = Math.round(H * b.cw / b.ch);
  const sheets = window._charEquippedSheets(cfg);
  const hasSheet = window._CHAR_LAYER_ORDER.some(function (s) { return s !== 'body' && sheets[s]; });
  if (b.src && (b.body !== 'human' || hasSheet || (cfg && cfg.body !== 'human'))) {
    // 시트 합성(down=row0, col0). 겹을 절대배치로 쌓음.
    const layer = function (url) {
      return "<div style=\"position:absolute;left:0;top:0;width:" + w + "px;height:" + H + "px;background-image:url('" + url + "');background-repeat:no-repeat;background-size:" + (w * 3) + "px " + (H * 3) + "px;background-position:0 0\"></div>";
    };
    let html = "<div style=\"position:relative;width:" + w + "px;height:" + H + "px;margin:0 auto\">";
    window._CHAR_LAYER_ORDER.forEach(function (s) { if (sheets[s]) html += layer(sheets[s]); });
    el.innerHTML = html + "</div>";
  } else if (window.renderCharacter) {
    el.innerHTML = window.renderCharacter(cfg, { size: 76, masked: !!(cfg && cfg.mask) });   // SVG 폴백
  }
};
```

- [ ] **Step 2: 안내 문구 업데이트**

`:1954`의 문구 `'꾸민 모습은 <b ...>앞모습</b>에 반영돼요<br>방에선 도트로 걸어다녀요'`를 아래로 교체:

```javascript
      + '<div style="font-size:12px;color:var(--text-tertiary);line-height:1.5;max-width:180px">고른 아이템이 <b style="color:rgba(255,255,255,0.6)">앞모습과 방 캐릭터</b>에<br>똑같이 반영돼요</div></div>'
```

- [ ] **Step 3: 실기 검증(WYSIWYG)**

`http://localhost:8777` Ctrl+Shift+R → 머피월드 → 꾸미기. 확인:
- 앞모습 프리뷰가 방에서 걷는 캐릭터와 **동일한 조합**(모자/머리/상의/하의 밴드)으로 보인다.
- 시트 없는 기존 SVG 아이템(예: hair_short)만 고르면 SVG 폴백이 뜬다(깨지지 않음).
- 문구가 "앞모습과 방 캐릭터에 똑같이 반영"으로 바뀜.

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "머피월드: 앞모습 프리뷰를 오버월드 시트 합성으로 통일(WYSIWYG) + 안내 문구"
```

---

## Self-Review 결과

- **Spec 커버리지:** 4.1 슬롯/z순서(body→bottom→shoes→top→hair→hat)→Task1 `_CHAR_LAYER_ORDER`. 4.2 HTML 컨테이너화→Task1 `_charBuildLayers`. 4.3 렌더 함수→Task1. 4.4 데이터 모델(bottom/shoes/hat)→Task3 Step2. 4.5 프리뷰 통일→Task4. 4.6 꾸미기 배선→Task3. 5장 아트 파이프라인(임시 시트)→Task2. 6장 검증→각 Task 검증 스텝 + Task2 하니스. 누락 없음.
- **플레이스홀더 스캔:** 모든 코드 스텝에 실제 코드 포함. "적절히 처리" 류 없음. (임시 시트는 의도된 산출물이며 실제 생성 코드 포함.)
- **타입/이름 일관성:** `_charBuildLayers`/`_charEquippedSheets`/`_charApplyPos`/`_charApplySprite`/`charClearSlot`/`_CHAR_LAYER_ORDER`가 정의처와 호출처에서 일치. `sheet` 필드명 일관. 슬롯명 `body/bottom/top/hair/hat` 일관.
- 상점 머피 차감은 범위 밖 → 별도 스펙(설계문서 8장)에서 다룸. 이 계획은 그것 없이도 "조합해 입고 걷는" 완결 프로토타입 산출.
