# 머피 캐릭터 Phase 1 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 머피로 꾸미는 도트 아바타 캐릭터를 만들어 마이페이지에서 꾸미고, 대숲에 가면 쓴 모습으로 등장시킨다.

**Architecture:** 단일 `index.html`에 캐릭터 카탈로그(코드 상수)·렌더 함수(인라인 SVG 레이어 합성)·상태(window 브릿지)·꾸미기 패널을 추가. 그림은 코드로 만든 단순 도트 SVG 플레이스홀더로 시작하고, 나중에 GPT 도트 PNG로 교체 가능하게 추상화한다. 데이터는 기존 `users/{uid}` 문서에 `character`/`wardrobe` 필드로 저장, 머피는 기존 `credits`/`spendCredit` 재사용.

**Tech Stack:** Vanilla JS (ES module Firebase + 일반 스크립트 혼합), Firestore, 인라인 SVG, GitHub Pages.

## Global Constraints

- 단일 파일 `index.html`. onclick에서 쓰는 함수는 `window.*` 전역 등록 필수(모듈/일반 스코프 분리).
- 아이콘·그림은 이모지 금지, SVG만. [[feedback-murpy-no-emoji]]
- 색: 블루(#3D7EFF)=메인, 초록(#4ADE80)=대숲, 골드(#F5C24B)=별점/코인. 솔리드 꽉찬 색 남발 금지.
- 머피 경제 = 작은 정수. 적립 가입+10/운동+1, 소비 매칭·대숲=1. 꾸미기 단가: 헤어 2·상의 2·가면 3 (색상은 MVP 무료 팔레트, 색상 과금은 후속).
- 대숲은 익명: 캐릭터는 항상 **가면(masked)** 상태로만 노출.
- 자동 테스트 없음 → 각 태스크 검증은 `http://localhost:8000/index.html` 브라우저 + DevTools 콘솔 수동 확인.
- 코드 수정 시 `index.html:2`의 cache-bust 버전을 올린다(마지막 태스크에서 일괄).
- 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

### Task 1: 캐릭터 카탈로그 + 도트 파츠 + renderCharacter()

**Files:**
- Modify: `index.html` — 일반 `<script>` 영역, 기존 `window.murpyTokenSVG`/`renderStreakUI` 근처(예: `index.html:5089` 머피 라인 아이콘 블록 뒤)에 추가

**Interfaces:**
- Produces:
  - `window.CHAR_COLORS = { skin:[...], hair:[...], top:[...] }`
  - `window.CHAR_DEFAULT = { skin, hair, hairColor, top, topColor, mask }`
  - `window.CHAR_ITEMS = [{ id, slot:'hair'|'top'|'mask', name, price }...]`
  - `window.CHAR_SHAPES` (내부 도형 생성기 맵)
  - `window.renderCharacter(cfg, opts) -> string` (opts: `{ size:number, masked:boolean }`)

- [ ] **Step 1: 상수·도형·렌더 함수 추가**

`index.html`의 일반 스크립트 영역(머피 코인/라인아이콘 헬퍼 근처)에 삽입:

```html
<script>
// ===== 머피 캐릭터: 카탈로그 · 도트 파츠 · 렌더 =====
window.CHAR_COLORS = {
  skin: ['#F0C9A0', '#E0A878', '#C68642'],
  hair: ['#2B2B2B', '#6B4226', '#C9A227', '#7C3AED'],
  top:  ['#3D7EFF', '#4ADE80', '#F5C24B', '#FF6B6B', '#E5E7EB']
};
window.CHAR_DEFAULT = { skin:'#F0C9A0', hair:'hair_short', hairColor:'#2B2B2B', top:'top_tee', topColor:'#3D7EFF', mask:null };

// 카탈로그: 모양 아이템(가격은 enforced에서만 차감). 색상은 MVP 무료 팔레트.
window.CHAR_ITEMS = [
  { id:'hair_short', slot:'hair', name:'숏컷',   price:0 },
  { id:'hair_wave',  slot:'hair', name:'웨이브', price:2 },
  { id:'hair_long',  slot:'hair', name:'롱헤어', price:2 },
  { id:'top_tee',    slot:'top',  name:'티셔츠', price:0 },
  { id:'top_tank',   slot:'top',  name:'민소매', price:2 },
  { id:'top_hood',   slot:'top',  name:'후디',   price:2 },
  { id:'mask_simple',slot:'mask', name:'기본 가면', price:0 },
  { id:'mask_band',  slot:'mask', name:'두건',     price:3 }
];
window.CHAR_FREE = ['hair_short', 'top_tee', 'mask_simple']; // 기본 지급

// 도형 생성기 — 64x64 도트 그리드. 나중에 PNG로 교체 가능(같은 좌표계).
window.CHAR_SHAPES = {
  base:      (c) => `<rect x="22" y="30" width="20" height="20" rx="3" fill="${c}"/><rect x="24" y="11" width="16" height="16" rx="3" fill="${c}"/>`,
  hair_short:(c) => `<path d="M23 19a9 9 0 0 1 18 0v2H23z" fill="${c}"/>`,
  hair_wave: (c) => `<path d="M22 20a10 10 0 0 1 20 0v3l-3-2-2 2-3-2-2 2-3-2-2 2-2-1z" fill="${c}"/>`,
  hair_long: (c) => `<path d="M23 19a9 9 0 0 1 18 0v14h-4V21H27v12h-4z" fill="${c}"/>`,
  top_tee:   (c) => `<rect x="22" y="34" width="20" height="16" rx="2" fill="${c}"/><rect x="16" y="34" width="8" height="9" rx="2" fill="${c}"/><rect x="40" y="34" width="8" height="9" rx="2" fill="${c}"/>`,
  top_tank:  (c) => `<rect x="24" y="34" width="16" height="16" rx="2" fill="${c}"/><rect x="26" y="32" width="4" height="6" fill="${c}"/><rect x="34" y="32" width="4" height="6" fill="${c}"/>`,
  top_hood:  (c) => `<rect x="21" y="33" width="22" height="17" rx="3" fill="${c}"/><rect x="16" y="34" width="8" height="10" rx="2" fill="${c}"/><rect x="40" y="34" width="8" height="10" rx="2" fill="${c}"/><rect x="28" y="30" width="8" height="6" rx="2" fill="${c}"/>`,
  mask_simple:() => `<rect x="24" y="15" width="16" height="7" rx="2" fill="#141414"/><rect x="27" y="17" width="3" height="3" fill="#fff"/><rect x="34" y="17" width="3" height="3" fill="#fff"/>`,
  mask_band: () => `<rect x="23" y="13" width="18" height="6" rx="1" fill="#1f2937"/><rect x="24" y="19" width="16" height="5" rx="2" fill="#141414"/><rect x="27" y="20" width="3" height="3" fill="#fff"/><rect x="34" y="20" width="3" height="3" fill="#fff"/>`
};

// cfg → SVG 문자열. masked=true면 가면 강제(대숲용).
window.renderCharacter = function (cfg, opts) {
  opts = opts || {};
  const size = opts.size || 96;
  cfg = cfg || window.CHAR_DEFAULT;
  const S = window.CHAR_SHAPES;
  const layers = [];
  layers.push(S.base(cfg.skin || window.CHAR_DEFAULT.skin));
  if (cfg.top && S[cfg.top]) layers.push(S[cfg.top](cfg.topColor || window.CHAR_DEFAULT.topColor));
  if (cfg.hair && S[cfg.hair]) layers.push(S[cfg.hair](cfg.hairColor || window.CHAR_DEFAULT.hairColor));
  if (opts.masked) {
    const m = cfg.mask || 'mask_simple';
    if (S[m]) layers.push(S[m]());
  }
  return `<svg viewBox="0 0 64 64" width="${size}" height="${size}" style="image-rendering:pixelated;display:block" aria-hidden="true">${layers.join('')}</svg>`;
};
</script>
```

- [ ] **Step 2: 브라우저 콘솔에서 렌더 확인**

`localhost:8000` 열고 콘솔에서:
```js
document.body.insertAdjacentHTML('beforeend', '<div style="position:fixed;bottom:0;left:0;z-index:99999;background:#222">'+window.renderCharacter(window.CHAR_DEFAULT,{size:120})+window.renderCharacter(window.CHAR_DEFAULT,{size:120,masked:true})+'</div>');
```
Expected: 좌하단에 기본 캐릭터 1개 + 가면 쓴 캐릭터 1개가 보인다(머리/몸/헤어/상의 + 가면). 확인 후 새로고침으로 제거.

- [ ] **Step 3: 커밋**

```bash
git -C /c/Users/won/Murpy add index.html
git -C /c/Users/won/Murpy commit -m "feat(캐릭터): 카탈로그·도트 파츠·renderCharacter() 추가

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: 데이터 모델 — 기본 지급 + 상태 로드

**Files:**
- Modify: `index.html:5360` (`window._creditState` 선언 근처)에 `_charState` 추가
- Modify: `index.html:5381` (웰컴 setDoc) — 기본 character/wardrobe 지급
- Modify: `index.html:5387` 부근(유저 문서 로드해 _creditState 채우는 곳) — character/wardrobe 로드

**Interfaces:**
- Consumes: `window.CHAR_DEFAULT`, `window.CHAR_FREE` (Task 1)
- Produces:
  - `window._charState = { character:object, wardrobe:array, ready:boolean }`
  - `window.getMyCharacter() -> object` (없으면 CHAR_DEFAULT 복제)

- [ ] **Step 1: _charState + getMyCharacter 추가**

`index.html:5360` `window._creditState = ...` 줄 바로 아래에 삽입:

```js
window._charState = { character: null, wardrobe: [], ready: false };
window.getMyCharacter = function () {
  return (window._charState.character) ? window._charState.character : { ...window.CHAR_DEFAULT };
};
```

- [ ] **Step 2: 웰컴 지급에 캐릭터 기본값 추가**

`index.html:5381`:
```js
await setDoc(ref, { credits: CREDIT_WELCOME, creditsLastEarned: '' }, { merge: true });
```
를 다음으로 교체:
```js
await setDoc(ref, { credits: CREDIT_WELCOME, creditsLastEarned: '', character: { ...window.CHAR_DEFAULT }, wardrobe: [...window.CHAR_FREE] }, { merge: true });
```

- [ ] **Step 3: 유저 문서 로드 시 _charState 채우기**

`index.html:5387` `window._creditState.lastEarned = d.creditsLastEarned || '';` 가 있는 블록(유저 문서 `d`를 읽는 곳)에서, 같은 블록 안에 추가:
```js
window._charState.character = d.character || { ...window.CHAR_DEFAULT };
window._charState.wardrobe = Array.isArray(d.wardrobe) ? d.wardrobe : [...window.CHAR_FREE];
window._charState.ready = true;
```
(주의: `d`가 해당 스코프의 유저 문서 데이터 변수명과 일치하는지 확인. 다르면 그 변수명 사용.)

- [ ] **Step 4: 콘솔 확인**

로그인 상태에서 `localhost:8000` 새로고침 → 콘솔:
```js
window._charState
```
Expected: `{ character:{skin,hair,...}, wardrobe:['hair_short','top_tee','mask_simple'], ready:true }`

- [ ] **Step 5: 커밋**

```bash
git -C /c/Users/won/Murpy add index.html
git -C /c/Users/won/Murpy commit -m "feat(캐릭터): users 문서 character/wardrobe 기본지급·상태로드

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: 마이페이지 캐릭터 표시 + 꾸미기 진입 버튼

**Files:**
- Modify: `index.html:792-807` (mypage-panel 프로필 영역) — 캐릭터 블록 추가
- Modify: `index.html:6750` (`window.loadMyPageProfile`) — 캐릭터 렌더 주입

**Interfaces:**
- Consumes: `window.renderCharacter`, `window.getMyCharacter` (Task 1·2)
- Produces: `#mypage-character` 컨테이너, `window.refreshMyCharacter()`

- [ ] **Step 1: 마이페이지에 캐릭터 블록 추가**

`index.html:806` `<div id="my-verify-status" style="min-height:16px"></div>` 바로 아래(같은 중앙 정렬 블록 안)에 삽입:

```html
<div style="margin-top:14px;display:flex;flex-direction:column;align-items:center;gap:10px">
  <div id="mypage-character" style="width:120px;height:120px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);border-radius:18px;display:flex;align-items:center;justify-content:center"></div>
  <button onclick="window.openCharCustomize && window.openCharCustomize()" style="display:inline-flex;align-items:center;gap:7px;background:rgba(61,126,255,0.12);border:1px solid rgba(61,126,255,0.3);color:#fff;border-radius:20px;padding:8px 16px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>
    캐릭터 꾸미기
  </button>
</div>
```

- [ ] **Step 2: refreshMyCharacter + loadMyPageProfile 연결**

`index.html:6750` `window.loadMyPageProfile = async () => {` 함수 본문 끝(닫는 `}` 직전)에 추가:
```js
if (window.refreshMyCharacter) window.refreshMyCharacter();
```
그리고 Task 1 스크립트 블록(또는 같은 일반 스크립트)에 함수 추가:
```js
window.refreshMyCharacter = function () {
  const el = document.getElementById('mypage-character');
  if (el) el.innerHTML = window.renderCharacter(window.getMyCharacter(), { size: 104 });
};
```

- [ ] **Step 3: 브라우저 확인**

로그인 → 우상단 아바타/마이페이지 진입 → 프로필 아래 **내 캐릭터(104px)** + "캐릭터 꾸미기" 버튼이 보인다. 버튼은 아직 동작 안 해도 됨(다음 태스크).

- [ ] **Step 4: 커밋**

```bash
git -C /c/Users/won/Murpy add index.html
git -C /c/Users/won/Murpy commit -m "feat(캐릭터): 마이페이지 캐릭터 표시·꾸미기 진입

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: 꾸미기/상점 패널 (착용·구매·저장)

**Files:**
- Modify: `index.html` — 다른 `.panel` 정의들 근처(예: mypage-panel 뒤)에 `char-customize-panel` 추가
- Modify: `index.html` (Task 1 스크립트 블록) — 패널 로직 함수들 추가

**Interfaces:**
- Consumes: `CHAR_ITEMS`, `CHAR_COLORS`, `renderCharacter`, `_charState`, `getMyCharacter`, 기존 `window.spendCredit`, `openPanel`/`closePanel`, `showToast`, Firestore `updateDoc`/`doc`/`db`
- Produces: `window.openCharCustomize()`, `window._charDraft`(작업중 cfg), `window.charSelectSlot(slot)`, `window.charPick(itemIdOrColor)`, `window.charSave()`

- [ ] **Step 1: 패널 마크업 추가**

`index.html`의 mypage-panel 닫는 태그 뒤(다른 패널들과 같은 레벨)에 삽입:

```html
<div class="panel" id="char-customize-panel">
  <div class="panel-header">
    <button class="back-btn" onclick="closePanel('char-customize-panel')">←</button>
    <span style="font-weight:700;font-size:16px">캐릭터 꾸미기</span>
    <button onclick="window.charSave && window.charSave()" style="margin-left:auto;background:var(--accent);border:none;color:#fff;border-radius:10px;padding:7px 14px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit">저장</button>
  </div>
  <div class="panel-body">
    <div id="char-preview" style="width:140px;height:140px;margin:4px auto 16px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);border-radius:20px;display:flex;align-items:center;justify-content:center"></div>
    <div class="tab-bar" style="margin-bottom:14px" id="char-slot-tabs">
      <button class="tab-btn active" onclick="window.charSelectSlot('hair', this)">헤어</button>
      <button class="tab-btn" onclick="window.charSelectSlot('top', this)">상의</button>
      <button class="tab-btn" onclick="window.charSelectSlot('mask', this)">가면</button>
      <button class="tab-btn" onclick="window.charSelectSlot('color', this)">색상</button>
    </div>
    <div id="char-item-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px"></div>
  </div>
</div>
```

- [ ] **Step 2: 패널 로직 추가**

Task 1 스크립트 블록에 추가(모듈 Firestore 함수가 필요하므로 `charSave`는 모듈에서 노출된 `window.updateDoc`/`window.dbDoc`가 없으면 별도 브릿지 필요 — 아래 Step 3 참고):

```js
window._charDraft = null;
window._charSlot = 'hair';

window.openCharCustomize = function () {
  if (!window.currentUser) { if (window.requireLogin) requireLogin('로그인 후 캐릭터를 꾸밀 수 있어요'); return; }
  window._charDraft = { ...window.getMyCharacter() };
  if (window.openPanel) openPanel('char-customize-panel');
  window.charSelectSlot('hair');
  window._charRenderPreview();
};

window._charRenderPreview = function () {
  const el = document.getElementById('char-preview');
  if (el) el.innerHTML = window.renderCharacter(window._charDraft, { size: 124 });
};

window.charSelectSlot = function (slot, btn) {
  window._charSlot = slot;
  if (btn) document.querySelectorAll('#char-slot-tabs .tab-btn').forEach(b => b.classList.toggle('active', b === btn));
  const grid = document.getElementById('char-item-grid');
  if (!grid) return;
  const owned = window._charState.wardrobe || [];
  if (slot === 'color') {
    // 헤어색 + 상의색 팔레트 (MVP 무료)
    const swatch = (kind, color) => `<button onclick="window.charPickColor('${kind}','${color}')" style="height:54px;border-radius:12px;border:1px solid rgba(255,255,255,0.12);background:${color};cursor:pointer"></button>`;
    grid.innerHTML =
      '<div style="grid-column:1/-1;font-size:11px;color:rgba(255,255,255,0.4);font-weight:700">헤어 색</div>' +
      window.CHAR_COLORS.hair.map(c => swatch('hairColor', c)).join('') +
      '<div style="grid-column:1/-1;font-size:11px;color:rgba(255,255,255,0.4);font-weight:700;margin-top:6px">상의 색</div>' +
      window.CHAR_COLORS.top.map(c => swatch('topColor', c)).join('');
    return;
  }
  const items = window.CHAR_ITEMS.filter(i => i.slot === slot);
  grid.innerHTML = items.map(i => {
    const has = i.price === 0 || owned.includes(i.id);
    const equipped = window._charDraft[slot] === i.id;
    const preview = window.renderCharacter({ ...window.CHAR_DEFAULT, [slot]: i.id, mask: slot === 'mask' ? i.id : null }, { size: 56, masked: slot === 'mask' });
    const tag = has ? (equipped ? '<span style="color:var(--accent);font-weight:800">착용중</span>' : '보유') : (i.price + '머피');
    return `<button onclick="window.charPick('${i.id}')" style="display:flex;flex-direction:column;align-items:center;gap:5px;background:rgba(255,255,255,0.04);border:1px solid ${equipped ? 'var(--accent)' : 'rgba(255,255,255,0.1)'};border-radius:14px;padding:10px 6px;cursor:pointer;font-family:inherit">
      <div style="width:56px;height:56px">${preview}</div>
      <span style="font-size:11px;color:#fff;font-weight:600">${i.name}</span>
      <span style="font-size:10px;color:rgba(255,255,255,0.5)">${tag}</span>
    </button>`;
  }).join('');
};

window.charPickColor = function (kind, color) {
  window._charDraft[kind] = color;
  window._charRenderPreview();
};

window.charPick = async function (itemId) {
  const item = window.CHAR_ITEMS.find(i => i.id === itemId);
  if (!item) return;
  const owned = window._charState.wardrobe || [];
  const has = item.price === 0 || owned.includes(itemId);
  if (!has) {
    if (window.creditsEnforcedFor && window.creditsEnforcedFor(window.currentUser.uid)) {
      if (!confirm(`'${item.name}' 구매에 ${item.price}머피를 써요. 살까요?`)) return;
    }
    const ok = await window.spendCredit(window.currentUser.uid, item.price);
    if (!ok) { showToast('머피가 부족해요 · 오늘 운동 인증하면 바로 써요'); return; }
    window._charState.wardrobe = [...owned, itemId];
    await window._charPersistWardrobe(window._charState.wardrobe);
    showToast(`'${item.name}' 구매 완료`);
  }
  window._charDraft[item.slot] = itemId;
  window._charRenderPreview();
  window.charSelectSlot(item.slot, document.querySelector('#char-slot-tabs .tab-btn.active'));
};

window.charSave = async function () {
  await window._charPersistCharacter(window._charDraft);
  window._charState.character = { ...window._charDraft };
  if (window.refreshMyCharacter) window.refreshMyCharacter();
  showToast('캐릭터 저장됨');
  if (window.closePanel) closePanel('char-customize-panel');
};
```

- [ ] **Step 3: Firestore 저장 브릿지 (모듈 스코프)**

캐릭터 저장은 Firestore 쓰기라 모듈 스코프 함수가 필요하다. `window.spendCredit`이 정의된 **모듈 `<script type="module">`** 안(예: `index.html:5451` 근처)에 추가:

```js
window._charPersistCharacter = async (cfg) => {
  if (!window.currentUser) return;
  try { await updateDoc(doc(db, 'users', window.currentUser.uid), { character: cfg }); }
  catch (e) { console.error('character save fail', e); }
};
window._charPersistWardrobe = async (arr) => {
  if (!window.currentUser) return;
  try { await updateDoc(doc(db, 'users', window.currentUser.uid), { wardrobe: arr }); }
  catch (e) { console.error('wardrobe save fail', e); }
};
```

- [ ] **Step 4: 브라우저 확인**

로그인 → 마이페이지 → "캐릭터 꾸미기" → 패널이 열리고 미리보기 표시.
- 헤어/상의 탭에서 다른 모양 탭 → 미리보기 즉시 변경(보유 항목 즉시 착용)
- 가격 있는 항목 탭 → 베타라 바로 구매·착용, "구매 완료" 토스트
- 색상 탭 → 헤어/상의 색 변경 반영
- 저장 → 패널 닫히고 마이페이지 캐릭터 갱신
- 새로고침 후 마이페이지 → 저장한 모습 유지

- [ ] **Step 5: 커밋**

```bash
git -C /c/Users/won/Murpy add index.html
git -C /c/Users/won/Murpy commit -m "feat(캐릭터): 꾸미기/상점 패널 — 착용·구매·색상·저장

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: 대숲 가면 캐릭터 노출

**Files:**
- Modify: `index.html:6896` (`postBambooFirestore` addDoc) — charConfig 스냅샷 저장
- Modify: `index.html:6860` (loadBamboo 글 카드 렌더) — 가면 캐릭터 표시

**Interfaces:**
- Consumes: `renderCharacter`, `getMyCharacter`, post 문서의 `charConfig`
- Produces: 대숲 글 카드 좌상단 가면 캐릭터

- [ ] **Step 1: 글 작성 시 캐릭터 스냅샷 저장**

`index.html:6896` `addDoc(collection(db, 'bamboo'), { text, userId: user.uid, ... })` 의 객체에 필드 추가:
```js
charConfig: (window.getMyCharacter ? window.getMyCharacter() : null),
```
(기존 필드들과 함께. nickname/userPhoto 스냅샷과 같은 방식.)

- [ ] **Step 2: 글 카드에 가면 캐릭터 렌더**

`index.html:6860` `return \`<div class="card bamboo-item">` 바로 다음 줄(카테고리 칩 위)에, 글 본문과 좌측 정렬되는 작은 가면 캐릭터 헤더 추가:
```js
return `<div class="card bamboo-item">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
          <div style="width:34px;height:34px;border-radius:9px;background:rgba(74,222,128,0.08);border:1px solid rgba(74,222,128,0.18);overflow:hidden;flex-shrink:0">${window.renderCharacter(post.charConfig || window.CHAR_DEFAULT, { size: 34, masked: true })}</div>
          <span style="font-size:12px;color:rgba(255,255,255,0.4);font-weight:600">익명의 머피</span>
        </div>
```
(이후 기존 카테고리 칩/본문/액션 줄은 그대로 이어진다.)

- [ ] **Step 3: 브라우저 확인**

대숲 탭 → 글 카드마다 좌상단에 **가면 쓴 캐릭터(34px)** + "익명의 머피". 새 글 작성 → 내 캐릭터가 가면 쓴 모습으로 뜬다(정체는 가려짐). 기존(스냅샷 없는) 글은 기본 가면 캐릭터로 표시.

- [ ] **Step 4: 커밋**

```bash
git -C /c/Users/won/Murpy add index.html
git -C /c/Users/won/Murpy commit -m "feat(캐릭터): 대숲 글에 가면 캐릭터 노출(익명 유지)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: 트렌딩 "인기 캐릭터" 카드

**Files:**
- Modify: `index.html` `window.loadHomeTrending`(약 `index.html:7940`) — 캐릭터 카드 1장 추가

**Interfaces:**
- Consumes: `renderCharacter`, `getMyCharacter`, 기존 `card()` 빌더(트렌딩 내부) 또는 별도 마크업
- Produces: 트렌딩 첫 카드로 "내 캐릭터" 노출(MVP featured)

- [ ] **Step 1: 트렌딩에 캐릭터 카드 추가**

`loadHomeTrending`의 `el.innerHTML = cards.join('');` 직전에, **로그인 사용자면** 캐릭터 카드를 `cards` 앞에 추가:
```js
if (window.currentUser && window.getMyCharacter) {
  const charSvg = window.renderCharacter(window.getMyCharacter(), { size: 92 });
  cards.unshift(`<button onclick="window.openCharCustomize && window.openCharCustomize()" aria-label="내 캐릭터 꾸미기" style="flex:none;width:150px;height:128px;position:relative;border-radius:16px;overflow:hidden;border:1px solid var(--border-subtle);background:linear-gradient(150deg,#3D7EFF22,#10101a);padding:0;cursor:pointer;font-family:inherit;display:flex;align-items:center;justify-content:center;transition:transform .15s ease" onmouseenter="this.style.transform='translateY(-3px)'" onmouseleave="this.style.transform='none'">
    <div style="position:absolute;top:10px;left:10px;font-size:10px;font-weight:800;color:#7aa8ff">내 캐릭터</div>
    <div style="width:92px;height:92px;margin-top:8px">${charSvg}</div>
  </button>`);
}
```

- [ ] **Step 2: 브라우저 확인**

홈 상단 "요즘 뜨는 콘텐츠" 첫 카드 = 내 캐릭터(92px) + "내 캐릭터" 라벨. 탭하면 꾸미기 패널 열림.

- [ ] **Step 3: 커밋**

```bash
git -C /c/Users/won/Murpy add index.html
git -C /c/Users/won/Murpy commit -m "feat(캐릭터): 트렌딩에 내 캐릭터 카드

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Firestore 규칙 확인 + cache-bust + 배포

**Files:**
- Check: `firestore.rules` — users 문서 owner 쓰기에 `character`/`wardrobe` 허용 여부, bamboo 문서에 `charConfig` 허용 여부
- Modify: `index.html:2` cache-bust

**Interfaces:** 없음(마무리)

- [ ] **Step 1: Firestore 규칙 확인**

`firestore.rules` 열어 `users/{uid}` 쓰기 규칙이 본인(`request.auth.uid == uid`)의 임의 필드 업데이트를 허용하는지 확인. 필드 화이트리스트가 없고 owner 전체 쓰기면 추가 작업 불필요. bamboo create가 임의 필드를 허용하면 `charConfig`도 통과.
- 화이트리스트 방식이라 막히면 `character`, `wardrobe`(users), `charConfig`(bamboo)를 허용 목록에 추가하고 콘솔에서 게시(방법 B). [[project-murpy]]

- [ ] **Step 2: 콘솔 권한 확인**

로그인 → 캐릭터 저장/구매·대숲 글쓰기에서 `permission-denied`가 콘솔에 없는지 확인.

- [ ] **Step 3: cache-bust 올리기**

`index.html:2` `<!-- cache-bust: vYYYYMMDDxxx -->` 의 숫자를 +1.

- [ ] **Step 4: 커밋 + 푸시(사용자 확인 후)**

```bash
git -C /c/Users/won/Murpy add index.html
git -C /c/Users/won/Murpy commit -m "chore(캐릭터): cache-bust + 규칙 확인, Phase 1 배포

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
# 사용자 확인 후:
# git -C /c/Users/won/Murpy push origin main
```

- [ ] **Step 5: 배포 확인**

푸시 후 `https://dyrhl4321-stack.github.io/Murpy` 실기기에서 마이페이지 캐릭터·꾸미기·대숲 가면·트렌딩 카드 동작 확인.

---

## 자체 점검 결과

- **스펙 커버리지**: §4 범위(슬롯·무대·피드 프사) → Task 3·5·6 / §5 데이터 → Task 2·4 / §6 경제 → Task 4 / §7 렌더 → Task 1 / §8 UI → Task 3·4 / §6 트렌딩 → Task 6 / §12 규칙 → Task 7. 모두 매핑됨.
- **MVP 의도적 단순화(스펙 대비)**: 색상은 MVP 무료 팔레트(스펙의 "색상 1머피"는 후속). 트렌딩 "인기 캐릭터"는 MVP에서 "내 캐릭터" featured(진짜 인기순 후속). 둘 다 스펙의 "작게 시작·후속 확장" 방침과 일치.
- **타입 일관성**: `renderCharacter(cfg,{size,masked})`, `getMyCharacter()`, `_charState.{character,wardrobe,ready}`, `_charPersistCharacter/_charPersistWardrobe`, slot 값 `hair|top|mask|color`, 아이템 `{id,slot,name,price}` — 태스크 전반 일치.
- **에셋 교체 경로**: 지금은 인라인 SVG(`CHAR_SHAPES`). GPT 도트 PNG 도입 시 `renderCharacter`를 레이어 `<img>` 합성으로 바꾸고 `CHAR_ITEMS`에 `src` 추가하면 됨(별도 후속 작업).
