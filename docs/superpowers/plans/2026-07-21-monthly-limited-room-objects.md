# 머피룸 월간 한정 오브젝트 시스템 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매달 그 달에만 얻을 수 있는 한정 오브젝트(기믹 가구·펫·메달)를 히든 조건 달성으로 해금해, 방 꾸미기에 챌린지 동기와 방문 이유를 만든다.

**Architecture:** 기존 `ROOM_ITEMS` 방 시스템 위에 `SEASON_ITEMS` 시즌 카탈로그를 얹는다. 유저 문서에 월별 활동 카운터(`monthly.YYYY-MM.{axis}`)를 적립하고, 클라이언트에서 조건 충족을 판정한다. 공개형은 즉시 축하 연출, 히든형은 `pendingBox`에 조용히 적립 후 방에서 상자로 발견·개봉한다.

**Tech Stack:** 단일 HTML(`index.html`), Firebase Firestore(ES module + `window.*` 브릿지 패턴), Canvas/CSS 픽셀 렌더, PWA(`sw.js`)

## Global Constraints

- **단일 파일 아키텍처:** 모든 JS/CSS/HTML은 `index.html` 안에 작성한다. 새 파일을 만들지 않는다.
- **모듈 스코프 브릿지:** Firestore 함수(`updateDoc`, `doc`, `increment`, `arrayUnion`, `arrayRemove`)는 ES module 스코프에만 있다. onclick에서 접근할 함수는 반드시 `window.xxx`로 등록한다. 신규 함수는 기존 Firestore 코드와 같은 module 블록(대략 6298행 import 이후) 안에 두거나, module 블록 안에서 `window.`에 할당한다.
- **좌표계:** 방 내부 좌표는 768×768 가상 좌표. 화면 표시는 `(값/7.68)%`로 환산한다.
- **이모지 금지:** UI에 이모지를 쓰지 않는다. 아이콘은 머피 전용 라인 SVG 또는 픽셀 PNG만 사용한다.
- **색 시스템:** 블루 `#3D7EFF`=메인/액션, 골드 `#F5C24B`=별점·머피·희소성, 초록=대숲 정체성 전용.
- **폰트:** 픽셀 UI는 `'Galmuri14'`(제목)·`'Galmuri11'`(본문), 일반 UI는 기본 상속.
- **에셋 하드룰:** `char/walk.png` 절대 수정 금지. 정수배 + NEAREST 리샘플만. 신규 방 오브젝트는 `char/rooms/`에 둔다.
- **캐시 버스팅:** 에셋·JS 변경 시 `sw.js`의 `murpy-v177` → 다음 버전으로 **3곳 전부**(`CACHE_NAME`, `STATIC_CACHE`, `CDN_CACHE`) 올린다.
- **배포:** `main` 브랜치 직접 푸시가 곧 배포다.

---

### Task 1: 시즌 카탈로그와 시즌 유틸

**Files:**
- Modify: `index.html` — `ROOM_ITEMS` 배열 직후(대략 2005행, `];` 다음 줄)

**Interfaces:**
- Consumes: 없음
- Produces:
  - `window.SEASON_ITEMS` — `{id, name, src, w, h, flat?, season, kind:'open'|'hidden', axis, hint, title, cond}[]`
  - `window.mwSeasonKey(date?)` → `'YYYY-MM'`
  - `window.mwSeasonDaysLeft()` → `number` (오늘 포함 남은 일수)
  - `window.mwItemDef(id)` → 아이템 정의 객체 또는 `null` (ROOM_ITEMS + SEASON_ITEMS 통합 조회)

- [ ] **Step 1: `SEASON_ITEMS` 카탈로그와 유틸 함수 추가**

`index.html`에서 `window._myRoom = null;` 줄(대략 2006행) **바로 앞**에 아래를 삽입한다.

```javascript
// ===== 월간 한정 오브젝트 =====
// 매달 운영: 에셋 제작 → 이 배열에 항목 추가. 지난 시즌은 남겨둔다(도감 아카이브 표시용).
// kind:'open'   → 도감에 실루엣+힌트 노출, 조건 충족 시 즉시 축하
// kind:'hidden' → 어디에도 노출 안 함, 조건 충족 시 방에 상자로 배달
window.SEASON_ITEMS = [
  { id:'s2608_dumbbell', name:'대왕 덤벨', src:'char/rooms/s2608_dumbbell.png?v=1', w:132, h:96,
    season:'2026-08', kind:'open', axis:'feed',
    hint:'헬스장 지박령의 기운이 느껴지는 자에게', title:'헬스장 지박령', cond:{ feed:8 } },
  { id:'s2608_lamp', name:'숲 요정 램프', src:'char/rooms/s2608_lamp.png?v=1', w:54, h:105,
    season:'2026-08', kind:'open', axis:'bamboo',
    hint:'숲의 요정들에게만 배달되는 선물입니다', title:'숲의 요정', cond:{ bamboo:5 } },
  { id:'s2608_campfire', name:'스쿼드 캠프파이어', src:'char/rooms/s2608_campfire.png?v=1', w:96, h:81,
    season:'2026-08', kind:'open', axis:'squad',
    hint:'혼자 온 자는 받을 수 없습니다', title:'스쿼드의 심장', cond:{ squad:2 } },
  { id:'s2608_dino', name:'아기 공룡', src:'char/rooms/s2608_dino.png?v=1', w:87, h:90,
    season:'2026-08', kind:'hidden', axis:'',
    hint:'', title:'공룡의 친구', cond:{ feed:5, bamboo:3, checkin:3 } },
];
// 현재 시즌 키 (YYYY-MM)
window.mwSeasonKey = function (d) {
  d = d || new Date();
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
};
// 이번 달 남은 일수 (오늘 포함)
window.mwSeasonDaysLeft = function () {
  const n = new Date();
  const last = new Date(n.getFullYear(), n.getMonth() + 1, 0).getDate();
  return last - n.getDate() + 1;
};
// 방에 놓을 수 있는 모든 아이템 통합 조회 (기본 카탈로그 + 한정)
window.mwItemDef = function (id) {
  return window.ROOM_ITEMS.find(r => r.id === id)
      || window.SEASON_ITEMS.find(r => r.id === id)
      || null;
};
```

- [ ] **Step 2: 브라우저 콘솔로 검증**

로컬에서 `index.html`을 열고 콘솔에서 실행:

```javascript
mwSeasonKey()                                  // → "2026-07" (오늘 기준)
mwSeasonKey(new Date(2026, 7, 15))             // → "2026-08"
mwSeasonDaysLeft()                             // → 이번 달 남은 일수(양의 정수)
mwItemDef('sofa_pink').name                    // → "핑크 소파"  (기존 카탈로그)
mwItemDef('s2608_dino').title                  // → "공룡의 친구" (시즌 카탈로그)
mwItemDef('없는아이디')                          // → null
SEASON_ITEMS.filter(i=>i.season==='2026-08').length  // → 4
```

기대: 위 6줄이 모두 주석의 값과 일치. 하나라도 `undefined`/에러면 삽입 위치가 `ROOM_ITEMS` 정의보다 앞선 것이므로 순서를 확인한다.

- [ ] **Step 3: 커밋**

```bash
git add index.html
git commit -m "feat(season): 월간 한정 오브젝트 카탈로그 + 시즌 유틸(mwSeasonKey/DaysLeft/mwItemDef)"
```

---

### Task 2: 아이템 조회 통합 (기존 방 렌더·편집기가 한정 아이템을 인식하게)

**Files:**
- Modify: `index.html` — `mwFurnHtml`(대략 2010행), `_reditAdd`(대략 2051행), `_reditBind` 내부 pointermove(대략 2078행)

**Interfaces:**
- Consumes: Task 1의 `window.mwItemDef(id)`
- Produces: 없음 (기존 함수 동작 확장)

`ROOM_ITEMS.find(...)`를 직접 호출하는 3곳을 `mwItemDef(...)`로 교체한다. 이걸 안 하면 한정 아이템을 방에 놓아도 렌더링되지 않는다.

- [ ] **Step 1: `mwFurnHtml`의 조회 교체**

찾을 코드 (`mwFurnHtml` 안):
```javascript
    const def = window.ROOM_ITEMS.find(r => r.id === it.id); if (!def) return '';
```
교체:
```javascript
    const def = window.mwItemDef(it.id); if (!def) return '';
```

- [ ] **Step 2: `_reditAdd`의 조회 교체**

찾을 코드:
```javascript
window._reditAdd = function (id) {
  const def = window.ROOM_ITEMS.find(r => r.id === id); if (!def) return;
```
교체:
```javascript
window._reditAdd = function (id) {
  const def = window.mwItemDef(id); if (!def) return;
```

- [ ] **Step 3: `_reditBind` pointermove의 조회 교체**

찾을 코드 (`room.addEventListener('pointermove', ...)` 안):
```javascript
    const def = window.ROOM_ITEMS.find(r => r.id === it.id); if (!def) return;
```
교체:
```javascript
    const def = window.mwItemDef(it.id); if (!def) return;
```

- [ ] **Step 4: 잔여 직접 조회가 없는지 확인**

```bash
grep -n "ROOM_ITEMS.find" index.html
```
기대 출력: **아무것도 없음.** 남아 있다면 그 줄도 `mwItemDef`로 교체한다.
(`ROOM_ITEMS.map`은 편집기 카탈로그 목록 렌더라 그대로 두는 것이 맞다.)

- [ ] **Step 5: 콘솔로 회귀 검증**

로그인 상태에서 머피월드 → 집 → 방 꾸미기를 연 뒤 콘솔에서:

```javascript
// 기존 가구가 정상 렌더되는지 (회귀 확인)
_reditAdd('sofa_pink'); _reditPaint();
document.querySelectorAll('#mw-redit-room img').length   // → 1 이상
// 한정 아이템도 렌더되는지 (에셋 PNG는 Task 8에서 추가되므로 깨진 이미지로 보이는 게 정상)
_reditAdd('s2608_dino'); _reditPaint();
_reditDraft.f.map(f=>f.id)                               // → [..., "s2608_dino"] 포함
```

기대: `_reditDraft.f`에 `s2608_dino`가 들어가고 콘솔 에러가 없다. 이미지는 파일이 아직 없어 깨져 보이는 것이 정상이다.

- [ ] **Step 6: 커밋**

```bash
git add index.html
git commit -m "refactor(room): 아이템 조회를 mwItemDef로 통합 - 한정 오브젝트 렌더 지원"
```

---

### Task 3: 월간 활동 카운터 적립

**Files:**
- Modify: `index.html` — `_charPersistRoom` 직후(대략 7038행)에 신규 함수, 유저 로드 지점(대략 7073행), 활동 함수 5곳

**Interfaces:**
- Consumes: Task 1의 `window.mwSeasonKey()`
- Produces:
  - `window._seasonState` — `{ season:string, counts:object, inv:string[], titles:string[], box:string[], ready:boolean }`
  - `window.mwBumpMonthly(axis)` — `axis`는 `'feed'|'bamboo'|'matchOk'|'squad'|'checkin'` 중 하나. Firestore `monthly.{season}.{axis}`를 +1 하고 로컬 state를 갱신한 뒤 `mwSeasonCheck()`를 호출한다.

- [ ] **Step 1: 시즌 상태와 적립 함수 추가**

`window._charPersistRoom = ...` 줄(대략 7038행) **바로 다음 줄**에 삽입한다. (이 위치는 module 스코프라 `updateDoc`/`doc`/`increment` 접근이 가능하다.)

```javascript
// ===== 월간 한정 오브젝트: 상태 + 활동 카운터 =====
window._seasonState = { season: '', counts: {}, inv: [], titles: [], box: [], ready: false };
// 활동 1건 적립. axis: 'feed'|'bamboo'|'matchOk'|'squad'|'checkin'
window.mwBumpMonthly = async function (axis) {
  const user = auth.currentUser || window.currentUser;
  if (!user || !axis) return;
  const season = window.mwSeasonKey();
  // 달이 바뀌었으면 로컬 카운터를 새 달로 리셋 (Firestore는 달마다 별도 키라 그대로 둔다)
  if (window._seasonState.season !== season) {
    window._seasonState.season = season;
    window._seasonState.counts = {};
  }
  window._seasonState.counts[axis] = (window._seasonState.counts[axis] || 0) + 1;
  try {
    await updateDoc(doc(db, 'users', user.uid), { ['monthly.' + season + '.' + axis]: increment(1) });
  } catch (e) { console.warn('monthly bump', e); }
  if (window.mwSeasonCheck) window.mwSeasonCheck();
};
```

- [ ] **Step 2: 유저 문서 로드 시 시즌 상태 채우기**

찾을 코드 (대략 7073행):
```javascript
    window._myRoom = (d.room && Array.isArray(d.room.f)) ? d.room : null;
    if (window.mwRenderFurn) window.mwRenderFurn();
```
교체:
```javascript
    window._myRoom = (d.room && Array.isArray(d.room.f)) ? d.room : null;
    // 월간 한정 오브젝트 상태
    const _season = window.mwSeasonKey();
    window._seasonState.season = _season;
    window._seasonState.counts = (d.monthly && d.monthly[_season]) ? { ...d.monthly[_season] } : {};
    window._seasonState.inv = Array.isArray(d.roomInv) ? d.roomInv.slice() : [];
    window._seasonState.titles = Array.isArray(d.titles) ? d.titles.slice() : [];
    window._seasonState.box = Array.isArray(d.pendingBox) ? d.pendingBox.slice() : [];
    window._seasonState.ready = true;
    if (window.mwRenderFurn) window.mwRenderFurn();
```

- [ ] **Step 3: 피드 인증 적립 지점 삽입**

`window.submitFeedPost`(대략 8304행) 안에서 피드 문서가 성공적으로 추가된 직후를 찾는다. `addDoc(collection(db, 'feed'), ...)` 호출 다음 줄에 삽입한다.

```javascript
    if (window.mwBumpMonthly) window.mwBumpMonthly('feed');
```

> 정확한 위치를 못 찾으면 `grep -n "collection(db, 'feed')" index.html`로 `addDoc` 호출부를 특정한다. 반드시 **업로드 성공 이후**여야 한다(실패 시 적립되면 안 됨).

- [ ] **Step 4: 대숲 글 적립 지점 삽입**

`window.postBambooFirestore`(대략 8635행)에서 찾을 코드:
```javascript
    await addDoc(collection(db, 'bamboo'), { text, userId: user.uid, userName: nickname, userPhoto, category: window._composeCat || '자유', likes: 0, likedBy: [], commentCount: 0, createdAt: serverTimestamp() });
    return true;
```
교체:
```javascript
    await addDoc(collection(db, 'bamboo'), { text, userId: user.uid, userName: nickname, userPhoto, category: window._composeCat || '자유', likes: 0, likedBy: [], commentCount: 0, createdAt: serverTimestamp() });
    if (window.mwBumpMonthly) window.mwBumpMonthly('bamboo');
    return true;
```

- [ ] **Step 5: 대숲 매칭 성사 적립 지점 삽입**

`window._acceptBambooMatch`(대략 9170행) 안, 채팅이 열리고 매칭이 확정 처리되는 성공 경로의 마지막에 삽입한다.

```javascript
    if (window.mwBumpMonthly) window.mwBumpMonthly('matchOk');
```

> 함수 본문을 읽고 `try` 블록의 성공 종료 직전(오류 경로가 아닌 곳)에 넣는다.

- [ ] **Step 6: 스쿼드 완료 적립 지점 삽입**

찾을 코드 (대략 12382행):
```javascript
    try { await updateDoc(doc(db,'users',me), reward
      ? { 'hostStats.completed': increment(1), credits: increment(10) }
      : { 'hostStats.completed': increment(1) }); } catch(e) {}
```
교체:
```javascript
    try { await updateDoc(doc(db,'users',me), reward
      ? { 'hostStats.completed': increment(1), credits: increment(10) }
      : { 'hostStats.completed': increment(1) }); } catch(e) {}
    if (window.mwBumpMonthly) window.mwBumpMonthly('squad');
```

- [ ] **Step 7: 센터 체크인 적립 지점 삽입**

찾을 코드 (대략 10602행, `mwCheckin` 안):
```javascript
  if (window.mwUpdateCoin) try { window.mwUpdateCoin(); } catch(e){}
  // 도감 보너스 판정 (도장 쾅 연출 끝난 뒤 축하가 이어지도록)
  setTimeout(()=>{ if (window._mwDogamBonusCheck) window._mwDogamBonusCheck(); }, 1700);
```
교체:
```javascript
  if (window.mwUpdateCoin) try { window.mwUpdateCoin(); } catch(e){}
  if (window.mwBumpMonthly) window.mwBumpMonthly('checkin');
  // 도감 보너스 판정 (도장 쾅 연출 끝난 뒤 축하가 이어지도록)
  setTimeout(()=>{ if (window._mwDogamBonusCheck) window._mwDogamBonusCheck(); }, 1700);
```

- [ ] **Step 8: 삽입 지점 5곳 확인**

```bash
grep -n "mwBumpMonthly(" index.html
```
기대 출력: 총 6줄 — 정의 1줄(`window.mwBumpMonthly = async function`)과 호출 5줄(`'feed'`, `'bamboo'`, `'matchOk'`, `'squad'`, `'checkin'` 각 1회).

- [ ] **Step 9: 실제 앱에서 적립 검증**

배포 후(또는 로컬 서버 실행 후) 로그인 상태에서 대숲 글을 1개 작성하고 콘솔에서:

```javascript
_seasonState.counts        // → { bamboo: 1 } 처럼 bamboo 카운트가 올라가 있어야 함
_seasonState.ready         // → true
```

Firebase 콘솔에서 `users/{내uid}` 문서를 열어 `monthly` → `2026-07`(현재 월) → `bamboo: 1` 필드가 생겼는지 확인한다.

기대: 로컬 state와 Firestore 양쪽 모두 반영. 한쪽만 되면 `mwBumpMonthly`의 `updateDoc` 경로(권한/필드명)를 확인한다.

- [ ] **Step 10: 커밋**

```bash
git add index.html
git commit -m "feat(season): 월간 활동 카운터(monthly.YYYY-MM.axis) 적립 - 피드/대숲/매칭/스쿼드/체크인"
```

---

### Task 4: 획득 판정 엔진 + 공개형 축하 연출

**Files:**
- Modify: `index.html` — `celebrateMurpy`(대략 6629행) 2줄, `mwBumpMonthly` 직후에 판정 함수 추가

**Interfaces:**
- Consumes: Task 1 `SEASON_ITEMS`/`mwSeasonKey`/`mwItemDef`, Task 3 `_seasonState`
- Produces:
  - `window.mwSeasonCheck()` — 현재 시즌 아이템 중 조건 충족·미보유 건을 처리. 공개형은 `roomInv`+`titles`에 넣고 축하, 히든은 `pendingBox`에 조용히 추가.
  - `celebrateMurpy(balance, opts)`가 `opts.iconHtml`, `opts.amountHtml`를 추가로 지원

- [ ] **Step 1: `celebrateMurpy`를 커스텀 아이콘·문구 지원으로 확장**

찾을 코드 (`celebrateMurpy` 안, 대략 6634~6637행):
```javascript
  const tw = el.querySelector('.mc-token');
  if (tw && window.murpyTokenSVG) tw.innerHTML = window.murpyTokenSVG(120);
  const _amt = el.querySelector('.mc-amt');
  if (_amt) _amt.innerHTML = '+' + (opts.amount != null ? opts.amount : 1) + ' <span style="color:#F5C24B">머피</span>';
```
교체:
```javascript
  const tw = el.querySelector('.mc-token');
  if (tw) tw.innerHTML = opts.iconHtml || (window.murpyTokenSVG ? window.murpyTokenSVG(120) : '');
  const _amt = el.querySelector('.mc-amt');
  if (_amt) _amt.innerHTML = opts.amountHtml || ('+' + (opts.amount != null ? opts.amount : 1) + ' <span style="color:#F5C24B">머피</span>');
```

이렇게 하면 축하 애니메이션·닫기 로직을 그대로 재사용하면서 한정 오브젝트용 내용만 바꿔 끼울 수 있다.

- [ ] **Step 2: 판정 엔진과 한정 축하 함수 추가**

Task 3에서 추가한 `mwBumpMonthly` 함수 **바로 다음**에 삽입한다.

```javascript
// 한정 오브젝트 축하 연출 (머피 적립 연출 재사용)
window.mwSeasonCelebrate = function (it) {
  if (!it || !window.celebrateMurpy) return;
  window.celebrateMurpy(0, {
    iconHtml: '<img src="' + it.src + '" alt="" style="width:120px;height:auto;image-rendering:pixelated">',
    amountHtml: '<span style="color:#F5C24B">' + it.name + '</span>',
    title: '이번 달 한정 오브젝트 획득!'
  });
};
// 현재 시즌 아이템 판정. 조건 충족 + 미보유만 처리한다.
window.mwSeasonCheck = async function () {
  const user = auth.currentUser || window.currentUser;
  if (!user || !window._seasonState.ready) return;
  const season = window.mwSeasonKey();
  const st = window._seasonState;
  const counts = st.counts || {};
  const items = window.SEASON_ITEMS.filter(it => it.season === season);
  for (const it of items) {
    if (st.inv.includes(it.id) || st.box.includes(it.id)) continue;
    const ok = Object.keys(it.cond).every(k => (counts[k] || 0) >= it.cond[k]);
    if (!ok) continue;
    if (it.kind === 'hidden') {
      // 히든: 알리지 않고 상자로 배달 — 방에 들어갔을 때 발견하게 한다
      st.box.push(it.id);
      try { await updateDoc(doc(db, 'users', user.uid), { pendingBox: arrayUnion(it.id) }); } catch (e) { console.warn('box grant', e); }
      if (window.mwRenderFurn) window.mwRenderFurn();
    } else {
      st.inv.push(it.id);
      if (it.title && !st.titles.includes(it.title)) st.titles.push(it.title);
      const upd = { roomInv: arrayUnion(it.id) };
      if (it.title) upd.titles = arrayUnion(it.title);
      try { await updateDoc(doc(db, 'users', user.uid), upd); } catch (e) { console.warn('item grant', e); }
      window.mwSeasonCelebrate(it);
    }
  }
};
```

- [ ] **Step 3: 콘솔로 공개형 획득 검증**

로그인 상태에서 콘솔 실행 (실제 활동 없이 카운터만 조작해 판정을 시험한다):

```javascript
// 현재 시즌을 8월 라인업에 맞춰 임시 확인하려면, 시스템 날짜가 7월이면 아래처럼 시즌을 맞춰준다
SEASON_ITEMS.forEach(i => i.season = mwSeasonKey());   // 임시: 전 아이템을 이번 달로
_seasonState.counts.bamboo = 5;                        // 숲 요정 램프 조건 충족
await mwSeasonCheck();
```

기대:
- 화면 중앙에 축하 연출이 뜨고 "이번 달 한정 오브젝트 획득!" + "숲 요정 램프" 표시 (이미지는 Task 8 전이라 깨져 보이는 게 정상)
- `_seasonState.inv` → `["s2608_lamp"]` 포함
- `_seasonState.titles` → `["숲의 요정"]` 포함
- Firebase 콘솔의 `users/{uid}`에 `roomInv`, `titles` 배열 생성

- [ ] **Step 4: 콘솔로 히든 무통지 검증**

이어서 콘솔에서:

```javascript
_seasonState.counts.feed = 5; _seasonState.counts.checkin = 3;   // 히든 조건(feed5+bamboo3+checkin3) 충족
await mwSeasonCheck();
_seasonState.box        // → ["s2608_dino"]
_seasonState.inv        // → 아직 s2608_dino 없음 (상자를 안 뜯었으므로)
```

기대: **축하 연출이 뜨지 않는다.** 조용히 `box`에만 들어가야 한다. 연출이 뜨면 `kind` 분기가 잘못된 것이다.

- [ ] **Step 5: 중복 지급이 없는지 검증**

```javascript
await mwSeasonCheck();       // 한 번 더 실행
_seasonState.inv.filter(x=>x==='s2608_lamp').length   // → 1 (2가 되면 중복 버그)
_seasonState.box.filter(x=>x==='s2608_dino').length   // → 1
```

- [ ] **Step 6: 임시 조작 되돌리기**

페이지를 새로고침해 `SEASON_ITEMS` 임시 수정을 원복한다. 테스트로 지급된 데이터를 지우려면 Firebase 콘솔에서 해당 유저 문서의 `roomInv`, `titles`, `pendingBox`, `monthly` 필드를 삭제한다.

- [ ] **Step 7: 커밋**

```bash
git add index.html
git commit -m "feat(season): 획득 판정 엔진 + 공개형 축하 연출(celebrateMurpy 커스텀 아이콘 지원)"
```

---

### Task 5: 히든 상자 렌더와 개봉

**Files:**
- Modify: `index.html` — CSS 블록(`.mw-` 스타일 근처, 대략 543행 뒤), `mwRenderFurn`(대략 2015행), `mwSeasonCheck` 다음에 개봉 함수 추가

**Interfaces:**
- Consumes: Task 1 `mwItemDef`, Task 3 `_seasonState`, Task 4 `mwSeasonCelebrate`
- Produces:
  - `window.mwBoxHtml(boxArr, clickable)` → 상자 `<img>` HTML 문자열 (빈 배열이면 `''`)
  - `window.mwOpenBox()` — 상자 1개를 열어 `pendingBox` → `roomInv`로 옮기고 축하

- [ ] **Step 1: 상자 둥실 애니메이션 CSS 추가**

`index.html`의 CSS에서 `#mw-redit-room img.sel { ... }` 줄(대략 543행) **바로 다음**에 삽입한다.

```css
  @keyframes mwBoxBob { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-7px) } }
  .mw-sbox { animation: mwBoxBob 1.7s ease-in-out infinite; filter: drop-shadow(0 0 10px rgba(245,194,75,.55)) }
```

- [ ] **Step 2: 상자 HTML 생성 함수 추가**

Task 4에서 추가한 `mwSeasonCheck` 함수 **바로 다음**에 삽입한다.

```javascript
// 미개봉 상자 렌더 (방 중앙 하단). clickable=true면 본인 방 → 탭해서 개봉
window.mwBoxHtml = function (boxArr, clickable) {
  if (!Array.isArray(boxArr) || !boxArr.length) return '';
  const x = 318, y = 306, w = 132;   // 768 좌표계
  return '<img src="char/rooms/season_box.png?v=1" alt="" draggable="false" class="mw-sbox"'
    + (clickable ? ' onclick="window.mwOpenBox()"' : '')
    + ' style="position:absolute;left:' + (x / 7.68).toFixed(2) + '%;top:' + (y / 7.68).toFixed(2) + '%;'
    + 'width:' + (w / 7.68).toFixed(2) + '%;z-index:900;'
    + (clickable ? 'cursor:pointer;pointer-events:auto;' : 'pointer-events:none;') + '">';
};
// 상자 개봉: pendingBox 맨 앞 1개 → roomInv로 이동 + 축하
window.mwOpenBox = async function () {
  const user = auth.currentUser || window.currentUser;
  if (!user) return;
  const st = window._seasonState;
  const id = (st.box || [])[0];
  if (!id) return;
  const it = window.mwItemDef(id);
  if (!it) { st.box.shift(); return; }
  st.box.shift();
  st.inv.push(id);
  if (it.title && !st.titles.includes(it.title)) st.titles.push(it.title);
  const upd = { pendingBox: arrayRemove(id), roomInv: arrayUnion(id) };
  if (it.title) upd.titles = arrayUnion(it.title);
  try { await updateDoc(doc(db, 'users', user.uid), upd); } catch (e) { console.warn('open box', e); }
  if (navigator.vibrate) navigator.vibrate([12, 40, 30]);
  if (window.mwRenderFurn) window.mwRenderFurn();
  window.mwSeasonCelebrate(it);
};
```

- [ ] **Step 3: 내 방 렌더에 상자 포함**

찾을 코드 (대략 2015행):
```javascript
window.mwRenderFurn = function () {
  const el = document.getElementById('mw-furn'); if (!el) return;
  el.innerHTML = (window._curField === 'home') ? window.mwFurnHtml(window._myRoom) : '';
};
```
교체:
```javascript
window.mwRenderFurn = function () {
  const el = document.getElementById('mw-furn'); if (!el) return;
  if (window._curField !== 'home') { el.innerHTML = ''; return; }
  const box = (window._seasonState && window._seasonState.box) || [];
  el.innerHTML = window.mwFurnHtml(window._myRoom) + window.mwBoxHtml(box, true);
};
```

- [ ] **Step 4: 남의 방에도 상자가 보이게 (구경거리)**

`mwVisitRoom`(대략 10284행)에서 찾을 코드:
```javascript
        ${window.mwFurnHtml(p.room)}
```
교체:
```javascript
        ${window.mwFurnHtml(p.room)}${window.mwBoxHtml(p.pendingBox, false)}
```

- [ ] **Step 5: 상자 개봉 흐름 검증**

배포 후 로그인 → 콘솔에서 상자 상태를 만든다:

```javascript
_seasonState.box = ['s2608_dino'];
mwRenderFurn();
document.querySelectorAll('#mw-furn .mw-sbox').length   // → 1
```

기대: 머피월드 집 화면 중앙에 상자가 둥실거리며 나타난다. 상자를 탭하면:
- 축하 연출에 "아기 공룡" 표시
- `_seasonState.box` → `[]`
- `_seasonState.inv`에 `s2608_dino` 추가
- 상자가 화면에서 사라짐

`_curField`가 `'home'`이 아니면 상자가 안 보이는 것이 정상이다(필드 이동 → 집으로 이동해 확인).

- [ ] **Step 6: 커밋**

```bash
git add index.html
git commit -m "feat(season): 히든 상자 렌더 + 개봉 연출 (본인 방 탭 개봉, 남의 방은 구경만)"
```

---

### Task 6: 방 편집기 "한정" 섹션

**Files:**
- Modify: `index.html` — `mwRoomEdit`의 카탈로그 렌더(대략 2035행), `_reditAdd`의 개수 제한(대략 2053행)

**Interfaces:**
- Consumes: Task 1 `SEASON_ITEMS`, Task 3 `_seasonState.inv`
- Produces: 없음

- [ ] **Step 1: 편집기에 보유 한정 아이템 섹션 추가**

찾을 코드 (`mwRoomEdit` 안, 대략 2035~2037행):
```javascript
      <div class="mw-redit-cat">${window.ROOM_ITEMS.map(r =>
        `<button onclick="window._reditAdd('${r.id}')"><img src="${r.src}" draggable="false"><span>${r.name}</span></button>`).join('')}
      </div>
```
교체:
```javascript
      <div class="mw-redit-cat">${window.ROOM_ITEMS.map(r =>
        `<button onclick="window._reditAdd('${r.id}')"><img src="${r.src}" draggable="false"><span>${r.name}</span></button>`).join('')}
      </div>
      ${(() => {
        const inv = (window._seasonState && window._seasonState.inv) || [];
        const owned = window.SEASON_ITEMS.filter(s => inv.includes(s.id));
        if (!owned.length) return '';
        return `<div style="font-family:'Galmuri11',sans-serif;font-size:11.5px;color:#F5C24B;margin:16px 2px 8px">한정 오브젝트</div>
          <div class="mw-redit-cat">${owned.map(r =>
            `<button onclick="window._reditAdd('${r.id}')"><img src="${r.src}" draggable="false"><span>${r.name}</span></button>`).join('')}
          </div>`;
      })()}
```

- [ ] **Step 2: 가구 개수 제한 문구 확인**

찾을 코드 (`_reditAdd` 안, 대략 2053행):
```javascript
  if (f.length >= 15) { showToast('가구는 15개까지 놓을 수 있어요'); return; }
```
그대로 둔다. 한정 오브젝트도 같은 15개 제한을 공유한다(별도 슬롯을 만들지 않는다 — YAGNI).

- [ ] **Step 3: 검증**

로그인 후 콘솔에서 보유 상태를 만들고 편집기를 연다:

```javascript
_seasonState.inv = ['s2608_lamp','s2608_dino'];
mwRoomEdit();
document.querySelectorAll('.mw-redit-cat').length   // → 2 (기본 카탈로그 + 한정)
```

기대: 편집기 하단에 골드색 "한정 오브젝트" 제목과 함께 보유 2종만 표시된다. 미보유 한정 아이템은 나타나지 않는다.

이어서 보유가 없을 때도 확인:
```javascript
_seasonState.inv = [];
mwRoomEdit();
document.querySelectorAll('.mw-redit-cat').length   // → 1 (한정 섹션 자체가 안 나옴)
```

- [ ] **Step 4: 커밋**

```bash
git add index.html
git commit -m "feat(season): 방 편집기에 보유 한정 오브젝트 섹션 추가"
```

---

### Task 7: 도감 "이번 달" 섹션 + 지난 시즌 아카이브

**Files:**
- Modify: `index.html` — `mwSeasonCheck` 이후에 섹션 렌더 함수 추가, `mwRenderDogam`의 최종 assembly(대략 9844행)

**Interfaces:**
- Consumes: Task 1 `SEASON_ITEMS`/`mwSeasonKey`/`mwSeasonDaysLeft`, Task 3 `_seasonState`
- Produces: `window.mwSeasonSectionHtml()` → 도감에 삽입할 HTML 문자열

- [ ] **Step 1: 도감 섹션 렌더 함수 추가**

Task 5에서 추가한 `mwOpenBox` 함수 **바로 다음**에 삽입한다.

```javascript
// 도감 "이번 달" 섹션 + 지난 시즌 아카이브
window.mwSeasonSectionHtml = function () {
  const season = window.mwSeasonKey();
  const st = window._seasonState || { inv: [] };
  const inv = st.inv || [];
  const cur = window.SEASON_ITEMS.filter(it => it.season === season);
  const past = window.SEASON_ITEMS.filter(it => it.season < season);
  const days = window.mwSeasonDaysLeft();
  const mLabel = Number(season.split('-')[1]) + '월';

  // 이번 달: 공개형은 항상 노출(미보유는 실루엣), 히든은 획득자에게만 노출
  const cells = cur.filter(it => it.kind === 'open' || inv.includes(it.id)).map(it => {
    const got = inv.includes(it.id);
    const isHidden = it.kind === 'hidden';
    const art = got
      ? `<img src="${it.src}" alt="" style="width:100%;height:56px;object-fit:contain;image-rendering:pixelated">`
      : `<img src="${it.src}" alt="" style="width:100%;height:56px;object-fit:contain;image-rendering:pixelated;filter:brightness(0) opacity(.45)">`;
    const name = got ? it.name : (isHidden ? '???' : '???');
    const sub = got
      ? `<span style="color:#F5C24B">${it.title}</span>`
      : `<span style="color:#8a93a8">${it.hint}</span>`;
    return `<div class="mw-panel" style="padding:11px 10px;text-align:center">
        <div style="height:56px;display:flex;align-items:center;justify-content:center;margin-bottom:7px">${art}</div>
        <div style="font-family:'Galmuri11',sans-serif;font-size:11.5px;color:${got ? '#fff' : '#4a5266'};margin-bottom:4px">${name}</div>
        <div style="font-size:10.5px;line-height:1.5">${sub}</div>
      </div>`;
  }).join('');

  const pastCells = past.map(it => {
    const got = inv.includes(it.id);
    return `<div class="mw-panel" style="padding:9px 8px;text-align:center;opacity:${got ? '1' : '.55'}">
        <img src="${it.src}" alt="" style="width:100%;height:40px;object-fit:contain;image-rendering:pixelated;${got ? '' : 'filter:brightness(0) opacity(.4);'}">
        <div style="font-family:'Galmuri11',sans-serif;font-size:10.5px;color:${got ? '#cfd6e6' : '#3b465e'};margin-top:5px">${got ? it.name : '???'}</div>
      </div>`;
  }).join('');

  return `
    <div style="display:flex;align-items:baseline;justify-content:space-between;margin:22px 2px 10px">
      <span style="font-family:'Galmuri14',sans-serif;font-size:13px;color:#F5C24B;letter-spacing:1px">${mLabel} 한정</span>
      <span style="font-size:11px;color:#8a93a8">${days}일 남음</span>
    </div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:9px">${cells}</div>
    <div style="font-size:10.5px;color:#4a5266;text-align:center;margin-top:9px;line-height:1.6">이번 달이 지나면 다시 만날 수 없어요</div>
    ${past.length ? `
      <div style="font-family:'Galmuri14',sans-serif;font-size:12px;color:#4a5266;letter-spacing:1px;margin:20px 2px 9px">지난 시즌</div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:7px">${pastCells}</div>` : ''}`;
};
```

- [ ] **Step 2: 도감 본문에 섹션 삽입**

`mwRenderDogam`의 최종 assembly(대략 9844행)에서 찾을 코드:
```javascript
    ${tiles}
    <div id="mw-dg-home" style="scroll-margin-top:8px">${homeCard}</div>
```
교체:
```javascript
    ${tiles}
    <div id="mw-dg-home" style="scroll-margin-top:8px">${homeCard}</div>
    ${window.mwSeasonSectionHtml ? window.mwSeasonSectionHtml() : ''}
```

- [ ] **Step 3: 검증 — 미보유 상태**

배포 후 콘솔에서:

```javascript
_seasonState.inv = [];
SEASON_ITEMS.forEach(i => i.season = mwSeasonKey());   // 임시: 이번 달로 맞춤
mwWorldPanel('dogam');
```

기대 (도감 패널 확인):
- "N월 한정" 제목 + "N일 남음"
- 공개형 3종이 **검은 실루엣**으로 표시, 이름은 `???`, 아래에 힌트 카피("숲의 요정들에게만 배달되는 선물입니다" 등)
- **히든(아기 공룡)은 목록에 아예 없다** — 있으면 필터가 잘못된 것
- "이번 달이 지나면 다시 만날 수 없어요" 문구

- [ ] **Step 4: 검증 — 보유 상태**

```javascript
_seasonState.inv = ['s2608_lamp','s2608_dino'];
mwWorldPanel('dogam');
```

기대:
- 숲 요정 램프가 **컬러**로 바뀌고 이름 "숲 요정 램프", 하단에 골드색 칭호 "숲의 요정"
- 아기 공룡이 **이제 목록에 등장**(획득자에게만 보임), 이름 "아기 공룡", 칭호 "공룡의 친구"
- 나머지 2종은 여전히 실루엣

- [ ] **Step 5: 검증 — 지난 시즌 아카이브**

```javascript
SEASON_ITEMS[0].season = '2026-06';   // 임시로 한 개를 과거 시즌으로
mwWorldPanel('dogam');
```

기대: 하단에 "지난 시즌" 영역이 나타나고 해당 아이템이 실루엣으로 표시된다. 새로고침해 임시 조작을 원복한다.

- [ ] **Step 6: 커밋**

```bash
git add index.html
git commit -m "feat(season): 도감에 이번 달 한정 섹션(실루엣+힌트) + 지난 시즌 아카이브"
```

---

### Task 8: 칭호 표시 (방 구경·방명록)

**Files:**
- Modify: `index.html` — `mwVisitRoom` 헤더(대략 10281행)

**Interfaces:**
- Consumes: Task 3 `titles` 필드 (유저 문서)
- Produces: 없음

- [ ] **Step 1: 방 구경 패널에 대표 칭호 표시**

찾을 코드 (`mwVisitRoom` 안, 대략 10279~10281행):
```javascript
  const nick = p.nickname || '머피';
  el.innerHTML = `
    <div class="mw-wpanel-head"><b>${nick}의 방</b><button class="mw-wclose" onclick="document.getElementById('mw-wpanel').remove()">✕</button></div>
```
교체:
```javascript
  const nick = p.nickname || '머피';
  const _titles = Array.isArray(p.titles) ? p.titles : [];
  const _title = _titles.length ? _titles[_titles.length - 1] : '';   // 가장 최근 획득 칭호
  const _titleHtml = _title
    ? `<span style="font-family:'Galmuri11',sans-serif;font-size:10.5px;color:#F5C24B;border:2px solid #05070c;background:#1a2233;padding:3px 7px;margin-left:8px;flex-shrink:0">${_title}</span>`
    : '';
  el.innerHTML = `
    <div class="mw-wpanel-head"><b>${nick}의 방</b>${_titleHtml}<button class="mw-wclose" onclick="document.getElementById('mw-wpanel').remove()">✕</button></div>
```

- [ ] **Step 2: 검증**

칭호를 가진 계정의 방을 구경한다. 머피월드 → 지도 → 다른 머피 선택 → 방 구경.

기대: 패널 제목이 "OO의 방  [숲의 요정]" 형태로, 칭호가 골드색 픽셀 배지로 닉네임 옆에 표시된다. 칭호가 없는 유저는 배지 없이 기존과 동일하게 보인다.

칭호 없는 경우도 확인하려면 Firebase 콘솔에서 대상 유저의 `titles` 필드를 잠시 지우고 다시 열어본다.

- [ ] **Step 3: 커밋**

```bash
git add index.html
git commit -m "feat(season): 방 구경 패널에 대표 칭호 배지 표시"
```

---

### Task 9: 에셋 5종 제작·등록 + 배포

**Files:**
- Create: `char/rooms/s2608_dumbbell.png`, `char/rooms/s2608_lamp.png`, `char/rooms/s2608_campfire.png`, `char/rooms/s2608_dino.png`, `char/rooms/season_box.png`
- Modify: `sw.js` — 캐시 버전 3곳
- Modify: `index.html` — 필요 시 `SEASON_ITEMS`의 `w`/`h` 실측값 보정

**Interfaces:**
- Consumes: Task 1의 `SEASON_ITEMS` id·경로 규약
- Produces: 없음

- [ ] **Step 1: 대표에게 에셋 시안 확인 받기**

**이 단계는 건너뛸 수 없다.** 아이템을 앱에 등록하기 전, 합성 미리보기로 정렬·비율을 증명하고 대표 승인을 받는다.

생성할 5종:

| 파일 | 내용 | 기준 크기(768 좌표계) |
|---|---|---|
| `s2608_dumbbell.png` | 방 안에 뜬금없이 놓인 사람만 한 대왕 덤벨 | w132 × h96 |
| `s2608_lamp.png` | 숲 요정이 깃든 듯한 초록빛 스탠드 램프 | w54 × h105 |
| `s2608_campfire.png` | 실내용 미니 캠프파이어 (스쿼드 상징) | w96 × h81 |
| `s2608_dino.png` | 앉아 있는 아기 공룡 펫 | w87 × h90 |
| `season_box.png` | 골드 리본 달린 선물 상자 (개봉 전 상태) | w132 × h132 |

제작 규약:
- 나노바나나로 생성 시 **배경은 반드시 `#00FF00` 단색**으로 요청한다(투명 배경은 생성 불가). 이후 형광초록 누끼.
- 기존 `char/rooms/*.png`와 같은 픽셀 밀도·아웃라인 두께를 유지한다. 특히 `sofa_brown.png`, `plant_palm.png`를 참고 기준으로 삼는다.
- 정수배 + NEAREST로만 리샘플한다.

- [ ] **Step 2: 실제 PNG 크기에 맞춰 `SEASON_ITEMS` 보정**

에셋 확정 후 실제 픽셀 크기를 확인한다.

```bash
python -c "from PIL import Image; import glob; [print(f, Image.open(f).size) for f in sorted(glob.glob('char/rooms/s2608_*.png')) + ['char/rooms/season_box.png']]"
```

출력된 `(width, height)` 비율이 `SEASON_ITEMS`의 `w`/`h`와 어긋나면(가로세로 비율이 다르면 찌그러져 보인다), `index.html`의 `SEASON_ITEMS` 항목에서 `w`, `h`를 실제 비율에 맞게 수정한다. `w`는 방 안에서 차지할 폭(768 기준), `h`는 `w × (실제높이/실제너비)`로 계산한다.

`season_box.png` 크기를 바꿨다면 `mwBoxHtml`의 `w` 상수(132)와 중앙 정렬용 `x`(318 = (768-132)/2)도 함께 맞춘다.

- [ ] **Step 3: 서비스워커 캐시 버전 올리기**

`sw.js`에서 3곳을 모두 `v177` → `v178`로 바꾼다.

```javascript
const CACHE_NAME = 'murpy-v178';
const STATIC_CACHE = 'murpy-static-v178';
const CDN_CACHE = 'murpy-cdn-v178';
```

확인:
```bash
grep -n "murpy-v\|murpy-static-v\|murpy-cdn-v" sw.js
```
기대: 3줄 모두 `v178`. 하나라도 `v177`이 남아 있으면 캐시가 갱신되지 않아 유저에게 새 에셋이 전달되지 않는다.

> `sw.js`는 PowerShell로 편집하면 인코딩이 깨진 전례가 있다. 반드시 Edit 도구로 수정한다.

- [ ] **Step 4: 배포 후 실제 앱에서 최종 검증**

```bash
git add char/rooms/s2608_dumbbell.png char/rooms/s2608_lamp.png char/rooms/s2608_campfire.png char/rooms/s2608_dino.png char/rooms/season_box.png sw.js index.html
git commit -m "feat(season): 2026-08 한정 오브젝트 에셋 4종 + 상자 (sw v178)"
git push
```

배포된 앱(https://dyrhl4321-stack.github.io/Murpy)에서 확인한다:

1. 도감 → "8월 한정" 섹션에 공개형 3종이 실루엣으로 보이는가 (에셋 실루엣이 형태를 알아볼 수 있는가)
2. 콘솔에서 `_seasonState.inv = ['s2608_dumbbell']; mwWorldPanel('dogam');` → 대왕 덤벨이 컬러로 정상 표시되는가
3. 콘솔에서 `_seasonState.box = ['s2608_dino']; mwRenderFurn();` → 집 화면에 상자가 둥실거리는가, 탭하면 공룡이 나오는가
4. 방 꾸미기에서 한정 아이템을 배치했을 때 다른 가구와 픽셀 밀도가 어울리는가, 캐릭터와 앞뒤(z-index)가 자연스러운가

기대: 4개 항목 모두 통과. 픽셀 밀도가 어긋나 보이면 Step 1로 돌아가 에셋을 다시 만든다(코드 수정으로 해결하지 않는다).

- [ ] **Step 5: 조건 수치 최종 조정**

베타 규모(GBD 초기 인원)를 감안해 `SEASON_ITEMS`의 `cond` 값이 한 달 안에 달성 가능한지 대표와 검토한다. 현재 초안값:

| 아이템 | 조건 | 검토 포인트 |
|---|---|---|
| 대왕 덤벨 | `feed:8` | 주 2회 인증이면 달성 |
| 숲 요정 램프 | `bamboo:5` | 대숲 글 5개 |
| 스쿼드 캠프파이어 | `squad:2` | **스쿼드 완료는 호스트만 카운트됨** — 참여자도 카운트하려면 별도 작업 필요, 이번 범위 밖 |
| 아기 공룡(히든) | `feed:5, bamboo:3, checkin:3` | 3개 축 모두 활동해야 하는 복합 조건 |

수치를 바꾸면 `index.html`만 수정하고 커밋한다(에셋 재작업 불필요).

```bash
git add index.html
git commit -m "chore(season): 2026-08 한정 오브젝트 획득 조건 수치 조정"
git push
```

---

## Self-Review 결과

**스펙 커버리지 확인:**

| 스펙 요구사항 | 담당 Task |
|---|---|
| 월 3~4종 (공개 2~3 + 히든 1) | Task 1 (카탈로그 4종) |
| 공개형 실루엣 + 세계관 힌트 | Task 7 |
| 히든 완전 미노출 | Task 7 (필터 `kind==='open' \|\| inv.includes`) |
| 기믹 가구·펫 중심 | Task 9 (덤벨/공룡/캠프파이어) |
| 칭호 동반 부여 | Task 4, 5 (`titles` arrayUnion), Task 8 (표시) |
| 진짜 한정판 (월 지나면 소멸) | Task 4 (`filter(it => it.season === season)`) |
| 지난 시즌 실루엣 아카이브 | Task 7 |
| 공개형 즉시 축하 | Task 4 |
| 히든 상자 배달·개봉 | Task 5 |
| 미개봉 상자 방문자에게도 보임 | Task 5 Step 4 |
| 클라이언트 판정 | Task 4 |
| monthly 카운터 5축 | Task 3 |
| 방 편집기 한정 섹션 | Task 6 |
| sw.js 캐시 갱신 | Task 9 Step 3 |

**알려진 제약 (스펙 범위 밖으로 확정):**
- 스쿼드 축은 **호스트 완료 시에만** 카운트된다(기존 코드에 참여자 완료 훅이 없음). 참여자도 카운트하려면 별도 스펙이 필요하다 — Task 9 Step 5에 명시했다.
- 칭호는 가장 최근 획득분 1개만 자동 표시한다(선택 UI 없음 — 스펙의 범위 제외 항목).
- 판정이 클라이언트에서 일어나므로 콘솔 조작으로 획득이 가능하다. 공개 런칭 전 Cloud Functions 이관 대상이며, 이는 `MURPY_사업_설명서_최종본.md`의 기존 로드맵 항목과 동일하다.

**타입 일관성 확인:** `mwItemDef`(Task 1) → Task 2·5에서 동일 시그니처 사용. `_seasonState`(Task 3) 필드명 `counts/inv/titles/box/ready/season` → Task 4·5·6·7에서 동일하게 참조. `mwSeasonCelebrate(it)`(Task 4) → Task 5에서 동일 호출. `mwBoxHtml(arr, clickable)`(Task 5) → Task 5 Step 3·4에서 동일 인자 순서.
