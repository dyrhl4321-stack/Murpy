# 필드 히든 오브젝트(헬스장 합판 → 아우라) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 헬스장 필드의 바닥 합판을 밟고 두드려 열면, 발밑 아우라(캐릭터 이펙트)를 얻고 꾸미기에서 켜고 끌 수 있다.

**Architecture:** 앱 전체가 단일 `index.html` 이다. 새 화면은 만들지 않는다. 이미 있는 것에 얹는다 — 아우라 렌더(`_mwAurApply`)·타자기(`mwTypewriter`)·텍스트 박스 스킨(`.mw-dossier`)·획득 모달(`mwSeasonCelebrate`)·필드 오버레이(`#mw-furn`)·users 문서 쓰기(`_seasonWrite`) 전부 그대로 쓴다. 순수 판정 함수는 `window.` 에 따로 빼서 node 로 테스트한다(기존 `tools/tests/*.test.mjs` 방식).

**Tech Stack:** 바닐라 JS + Firebase(Firestore/RTDB) + CSS. 빌드 없음. 테스트는 node 내장 `assert`.

**Spec:** `docs/superpowers/specs/2026-08-18-field-hidden-artifact-design.md`

## Global Constraints

- **저장소:** `C:\Users\allys\Murpy` / 브랜치 `main`. 앱 전체가 `index.html` 한 파일.
- **★다른 창이 같은 `index.html` 을 만진다.** 매 커밋 직전 `git status` 를 보고, 내가 안 만진 변경이 보이면 **그 창이 먼저 커밋할 때까지 기다린다.** 파일을 지정해 커밋할 땐 `git commit --only <path>`.
- **배포 전 필수 2종:** ①`<script>` 6블록 전부 `node --check` 통과 ②`index.html` 의 `_SW_V` 와 `sw.js` 의 버전 숫자 일치.
- **`sw.js` 는 PowerShell 로 편집 금지.** Edit 도구로만 (인코딩이 깨진다).
- **이모지 금지.** 머피 전용 라인 SVG 아이콘만. 블록·기하문자(`▓`, `▼`)도 금지 — 픽셀폰트에서 깨진다. 화살표가 필요하면 CSS 삼각형으로 그린다.
- **틴트 칩 금지.** 반투명 색면 배지를 쓰지 말 것. `background:none` + 테두리 + 글자색.
- **인라인 style 을 `''` 로 지우지 말 것.** `cssText` 의 `inset:0` 까지 날아가 요소가 엉뚱한 자리에 앉는다.
- **색:** 파랑 `#7AA4FF` = 메인/액션. 골드 `#F5C24B` = 별점·코인·칭호 전용(다른 데 쓰지 말 것).
- **픽셀폰트(`Galmuri*`)는 머피월드 전용.** 이 작업은 전부 머피월드 안이라 픽셀폰트가 맞다.
- **캐릭터 렌더 경로를 새로 만들지 말 것.** 아우라는 캐릭터의 **형제 DOM** 으로만 얹는다.
- **점프 금지.** `walk.png` 에 점프 프레임이 없다. 좌우·상하 걷기로만 만든다.
- **★`index.html` 은 인라인 `<script>` 가 6개고, 그중 하나만 모듈이다.** 이걸 어기면 실행 중에 터진다.
  - **블록 3 (2362~4647행)** = **모듈이 아니다.** `arrayUnion`·`updateDoc`·`doc`·`db` 를 **못 쓴다.**
    Firestore 를 만져야 하면 `window.` 에 붙은 브릿지를 부른다(예: `window._mwGrantRoomItem`,
    `window._seasonWrite`). 코드에 주석으로도 남아 있다(index.html:3286).
    여기 사는 것: `_FIELDS` · `charSetField` · `charMove` · `_charApplyPos` · `_initRoomJoy` ·
    `mwRenderFurn` · `mwRoomEdit`
  - **블록 5 (9726~24648행)** = 모듈. Firebase 임포트가 여기 있다.
    여기 사는 것: `_seasonState` · `_seasonWrite` · `mwSeasonCelebrate` · `mwTypewriter` ·
    `_mwAurApply` · `_mwAurOf` · `_MW_AUR_COLORS` · `_sqCharEl` · 프레즌스
  - **블록을 넘는 호출은 `window.` 를 통해 런타임에만** 한다. 정의 순서는 상관없다 —
    함수가 실제로 불리는 건 로드가 다 끝난 뒤다.
  - **★단, 로드 중에 불리는 것은 순서가 상관있다.** `mwRenderFurn` 은 users 문서 로드
    직후(12469행, 블록 5)에 한 번 불린다. 그때 이미 있어야 하는 상수는 **블록 3** 에 둬야 한다.
- **에셋은 이미 다 있다.** `char/fields/gym_plate_{closed,floor,ajar,open,hole}.png` (커밋 `f183080`). 새로 뽑지 않는다.

---

### Task 1: 카탈로그 + 순수 판정 함수

밟기 판정과 색 화이트리스트를 순수 함수로 빼서 node 로 검증한다. 화이트리스트는 **보안 자리**다 — 아우라 색 이름이 그대로 파일 경로에 들어가고, 그 값이 남의 프레즌스로 실려 온다.

**Files:**
- Modify: `index.html:3450` 부근 — **블록 3** 의 `window._FIELDS = {` **바로 위**에 새 블록 추가
- Test: `tools/tests/field-aura.test.mjs` (신규)

**★어디에 두는가:** `_MW_AUR_COLORS`(23265행, 블록 5) 옆이 아니라 **`_FIELDS` 옆(블록 3)** 이다.
①이 상수들은 Firebase 를 안 쓰므로 블록 3 에서도 된다 ②`mwRenderFurn` 이 **로드 중에**
(users 문서 로드 직후, 12469행) 한 번 불리는데, 블록 5 뒷부분에 두면 그때 아직 정의가 없어
헬스장에 들어가 있어도 합판이 안 그려진다 ③필드 상수 옆이라 읽기도 좋다.
`_mwAurColor` 가 읽는 `window._MW_AUR_COLORS` 는 **호출 시점**에만 필요하므로 블록 5 에 있어도 된다.

**Interfaces:**
- Produces: `window.FIELD_AURAS` (객체), `window._FIELD_SPOTS` (객체), `window._PLATE_TAPS_1`/`_PLATE_TAPS_2` (숫자), `window._mwPlateHit(fieldKey, tc, tr) -> string` (스팟 id 또는 `''`), `window._mwAurColor(seasonKey) -> string` (색 이름 또는 `''`)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tools/tests/field-aura.test.mjs` 를 만든다.

```js
// 필드 히든 오브젝트 순수함수 테스트 — index.html에서 추출해 검증
// 실행: node tools/tests/field-aura.test.mjs
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');

function grab(re, name) {
  const m = src.match(re);
  assert(m, `index.html에서 ${name}를 찾지 못함`);
  return m[0];
}

const w = {};
new Function('window', grab(/window\.FIELD_AURAS = \{[\s\S]*?\n\};/, 'FIELD_AURAS'))(w);
new Function('window', grab(/window\._FIELD_SPOTS = \{[\s\S]*?\n\};/, '_FIELD_SPOTS'))(w);
new Function('window', grab(/window\._MW_AUR_COLORS = \[[^\]]*\];/, '_MW_AUR_COLORS'))(w);
new Function('window', grab(/window\._mwPlateHit = function[\s\S]*?\n\};/, '_mwPlateHit'))(w);
new Function('window', grab(/window\._mwAurColor = function[\s\S]*?\n\};/, '_mwAurColor'))(w);
new Function('window', grab(/window\._PLATE_TAPS_1 = \d+;/, '_PLATE_TAPS_1'))(w);
new Function('window', grab(/window\._PLATE_TAPS_2 = \d+;/, '_PLATE_TAPS_2'))(w);

// 1) 합판 칸을 밟으면 'plate', 아니면 ''
assert.strictEqual(w._mwPlateHit('gym', 11, 7), 'plate');
assert.strictEqual(w._mwPlateHit('gym', 12, 7), 'plate');
assert.strictEqual(w._mwPlateHit('gym', 10, 7), '', '왼쪽 옆 칸이 걸림');
assert.strictEqual(w._mwPlateHit('gym', 13, 7), '', '오른쪽 옆 칸이 걸림');

// 2) ★물러서는 칸(tr 8)은 절대 트리거가 아니어야 한다 — 아니면 물러서자마자 재발동해 무한루프
assert.strictEqual(w._mwPlateHit('gym', 11, 8), '', '물러서는 칸이 트리거다 → 무한루프');
assert.strictEqual(w._mwPlateHit('gym', 12, 8), '', '물러서는 칸이 트리거다 → 무한루프');

// 3) 다른 필드엔 합판이 없다
assert.strictEqual(w._mwPlateHit('home', 11, 7), '');
assert.strictEqual(w._mwPlateHit('tennis', 11, 7), '');
assert.strictEqual(w._mwPlateHit('golf', 11, 7), '');

// 4) 트리거 칸과 물러설 칸이 둘 다 걸을 수 있는 칸이어야 한다 (_FIELDS.gym.map 과 대조)
const fm = grab(/gym: \{ name: '헬스장'[\s\S]*?\] \},/, '_FIELDS.gym');
const rows = fm.match(/"[.#]{16}"/g).map(s => s.slice(1, -1));
const sp = w._FIELD_SPOTS.gym.plate;
for (let tc = sp.tc[0]; tc <= sp.tc[1]; tc++) {
  assert.strictEqual(rows[7][tc], '.', `트리거 칸 tc${tc},tr7 이 벽이다`);
  assert.strictEqual(rows[8][tc], '.', `물러설 칸 tc${tc},tr8 이 벽이다`);
}

// 5) 색은 카탈로그 + 화이트리스트를 둘 다 통과해야 한다 (경로 주입 방지)
const key = Object.keys(w.FIELD_AURAS)[0];
assert.strictEqual(w._mwAurColor(key), 'blue');
assert.strictEqual(w._mwAurColor('2099-01'), '', '없는 시즌이 색을 돌려줌');
assert.strictEqual(w._mwAurColor(''), '');
assert.strictEqual(w._mwAurColor('../../etc/passwd'), '', '경로 주입이 통과함');
assert.strictEqual(w._mwAurColor(null), '');

// 6) 카탈로그의 모든 색이 화이트리스트 안에 있어야 한다 (에셋 없는 색 등록 방지)
for (const k in w.FIELD_AURAS) {
  assert(w._MW_AUR_COLORS.includes(w.FIELD_AURAS[k].color), `화이트리스트에 없는 색: ${k}`);
  assert(w.FIELD_AURAS[k].name && w.FIELD_AURAS[k].title, `이름/칭호 누락: ${k}`);
}

// 7) 탭 수 상수
assert(w._PLATE_TAPS_1 > 0 && w._PLATE_TAPS_2 > 0);

console.log('field-aura.test.mjs: 밟기 판정·물러설 칸·색 화이트리스트 전부 통과 ✓');
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `node tools/tests/field-aura.test.mjs`
Expected: FAIL — `index.html에서 FIELD_AURAS를 찾지 못함`

- [ ] **Step 3: index.html 에 최소 구현을 넣는다**

`window._FIELDS = {` 줄을 찾아, **그 줄 바로 위**(블록 3)에 넣는다.

```js
// ===== 필드 히든 오브젝트 (헬스장 바닥 합판) =====
// 스펙: docs/superpowers/specs/2026-08-18-field-hidden-artifact-design.md
// 합판을 밟으면 말이 걸리고, 두드려서 열면 발밑 아우라를 얻는다.
// ★상자 시스템(mwSeasonCheck)을 타지 않는다. 규칙 위반이 아니라 **적용 대상이 다르다** —
//   상자는 '방에 배달되는 가구'용이고 이건 캐릭터에 붙는 이펙트라 방에 놓을 물건이 아니다.
//   공룡(cond 비우고 직접 지급)과도 다른 경우다. 헷갈리지 말 것.
window.FIELD_AURAS = {
  '2026-08': { color: 'blue', name: '바닥의 불', title: '합판을 연 자',
               desc: '헬스장 바닥 아래에서 꺼내온 불꽃. 발밑에서 조용히 돈다.' }
};
// ★이번 달 키가 여기 없으면 합판은 안 열린다("그냥 낡은 합판이다"로 끝난다).
//   첫 노출 시점은 코드가 아니라 이 줄로 정해진다.

// 필드 핫스팟. x/y/w/h 는 field_gym.png(1024x1024) 좌표계 실측값 — 합판 그림이 박힌 자리다.
// ★tr 은 [7,7] 하나여야 한다. 다 열릴 때 캐릭터가 tr 8 로 물러서는데,
//   tr 8 도 트리거면 물러서자마자 다시 발동해 무한루프가 된다.
window._FIELD_SPOTS = {
  gym: { plate: { tc: [11, 12], tr: [7, 7], x: 727, y: 494, w: 103, h: 73 } }
};
window._PLATE_TAPS_1 = 10;   // 여기까지 두드리면 살짝 열린다
window._PLATE_TAPS_2 = 30;   // 살짝 열린 뒤 여기서 다 열린다 (누적 40)

// 밟은 칸이 핫스팟인가. 순수함수 (tools/tests/field-aura.test.mjs)
window._mwPlateHit = function (fieldKey, tc, tr) {
  const spots = (window._FIELD_SPOTS || {})[fieldKey];
  if (!spots) return '';
  for (const id in spots) {
    const s = spots[id];
    if (tc >= s.tc[0] && tc <= s.tc[1] && tr >= s.tr[0] && tr <= s.tr[1]) return id;
  }
  return '';
};
// 시즌 키 -> 아우라 색. ★반드시 화이트리스트를 통과시킨다 —
//   이 값이 그대로 파일 경로에 들어가고, 남의 프레즌스로 실려 오는 자리다.
window._mwAurColor = function (key) {
  const meta = (window.FIELD_AURAS || {})[key];
  if (!meta) return '';
  return (window._MW_AUR_COLORS || []).indexOf(meta.color) >= 0 ? meta.color : '';
};
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run: `node tools/tests/field-aura.test.mjs`
Expected: PASS — `밟기 판정·물러설 칸·색 화이트리스트 전부 통과 ✓`

- [ ] **Step 5: 문법 검사**

Run: `node tools/dogam-syntax-check.mjs`
Expected: 통과

- [ ] **Step 6: 커밋**

```bash
git status --short
git add index.html tools/tests/field-aura.test.mjs
git commit -m "feat(field): 합판 카탈로그 + 밟기 판정 순수함수"
```

---

### Task 2: 소유·장착 상태를 users 문서에서 읽어온다

**Files:**
- Modify: `index.html:11032` — `window._seasonState` 초기값
- Modify: `index.html:12457` 부근 — users 문서 로드
- Test: `tools/tests/field-aura.test.mjs` (검증 추가)

**Interfaces:**
- Consumes: Task 1 `window._mwAurColor`
- Produces: `window._seasonState.auras` (string[]), `window._seasonState.auraOn` (string)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tools/tests/field-aura.test.mjs` 의 `console.log` **바로 위**에 붙인다.

```js
// 8) 상태 그릇에 아우라 자리가 있어야 한다
const stLine = grab(/window\._seasonState = \{[^}]*\};/, '_seasonState');
assert(/auras:\s*\[\]/.test(stLine), '_seasonState 에 auras 배열이 없다');
assert(/auraOn:\s*''/.test(stLine), '_seasonState 에 auraOn 이 없다');

// 9) users 문서에서 fieldAuras / aura 를 읽어와야 한다
assert(/_seasonState\.auras = Array\.isArray\(d\.fieldAuras\)/.test(src),
  'users 문서의 fieldAuras 를 읽지 않는다');
assert(/_seasonState\.auraOn = \(typeof d\.aura === 'string'\)/.test(src),
  'users 문서의 aura 를 읽지 않는다');
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `node tools/tests/field-aura.test.mjs`
Expected: FAIL — `_seasonState 에 auras 배열이 없다`

- [ ] **Step 3: 상태 그릇을 넓힌다**

`index.html:11032` 을 이렇게 바꾼다.

```js
window._seasonState = { season: '', counts: {}, inv: [], titles: [], box: [], auras: [], auraOn: '', ready: false };
```

- [ ] **Step 4: users 문서 로드에 두 줄을 붙인다**

`window._seasonState.box = Array.isArray(d.pendingBox) ? d.pendingBox.slice() : [];` **바로 아래**.

```js
      // 필드 아우라 — 소유(fieldAuras)와 장착(aura)을 나눈다. 얻은 걸 꾸미기에서 골라 켠다.
      window._seasonState.auras = Array.isArray(d.fieldAuras) ? d.fieldAuras.slice() : [];
      window._seasonState.auraOn = (typeof d.aura === 'string') ? d.aura : '';
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

Run: `node tools/tests/field-aura.test.mjs`
Expected: PASS

- [ ] **Step 6: 문법 검사 + 커밋**

```bash
node tools/dogam-syntax-check.mjs
git status --short
git add index.html tools/tests/field-aura.test.mjs
git commit -m "feat(field): 아우라 소유/장착 상태를 users 문서에서 로드"
```

---

### Task 3: `_mwAurOf` 를 시험 스위치에서 실제 소유 판정으로 바꾼다

지금 `_mwAurOf` 는 `?aur=1` 만 본다. 코드 주석에 "히든 오브젝트 흐름이 붙으면 users 문서를 보게 바꾼다"고 적혀 있는 자리다.

**Files:**
- Modify: `index.html` — `window._mwAurOf = function (uid) {...}` 블록 통째로 교체
- Test: `tools/tests/field-aura.test.mjs`

**Interfaces:**
- Consumes: Task 1 `_mwAurColor`, Task 2 `_seasonState.auraOn`
- Produces: `window._mwAurOf(uid, fromPresence) -> string` (색 이름 또는 `''`)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`console.log` **바로 위**에 붙인다.

```js
// 10) _mwAurOf — 내 것은 내 문서에서, 남의 것은 프레즌스에서
const w2 = { _MW_AUR_COLORS: ['blue'], currentUser: { uid: 'me' },
             _seasonState: { auraOn: '2026-08' }, _AUR_TEST: '' };
new Function('window', grab(/window\.FIELD_AURAS = \{[\s\S]*?\n\};/, 'FIELD_AURAS'))(w2);
new Function('window', grab(/window\._mwAurColor = function[\s\S]*?\n\};/, '_mwAurColor'))(w2);
new Function('window', grab(/window\._mwAurOf = function[\s\S]*?\n\};/, '_mwAurOf'))(w2);

assert.strictEqual(w2._mwAurOf('me', ''), 'blue', '내 장착값을 안 본다');
assert.strictEqual(w2._mwAurOf('other', '2026-08'), 'blue', '남의 프레즌스 값을 안 본다');
assert.strictEqual(w2._mwAurOf('other', ''), '', '안 켠 남에게 아우라가 뜬다');
assert.strictEqual(w2._mwAurOf('other', '2099-01'), '', '카탈로그에 없는 값이 통과함');
assert.strictEqual(w2._mwAurOf('other', '../fx/x'), '', '경로 주입이 통과함');
w2._seasonState.auraOn = '';
assert.strictEqual(w2._mwAurOf('me', ''), '', '껐는데도 내 아우라가 뜬다');
// 시험 스위치도 화이트리스트를 통과해야 한다
w2._AUR_TEST = 'nosuch';
assert.strictEqual(w2._mwAurOf('me', ''), '', '시험 스위치가 화이트리스트를 안 탄다');
w2._AUR_TEST = '1';
assert.strictEqual(w2._mwAurOf('me', ''), 'blue');
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `node tools/tests/field-aura.test.mjs`
Expected: FAIL — `내 장착값을 안 본다`

- [ ] **Step 3: `_mwAurOf` 를 통째로 바꾼다**

기존 블록(위 주석 포함)을 이걸로 교체한다.

```js
// 누구에게 어떤 색 아우라를 그릴지. ★내 것과 남의 것을 다른 데서 읽는다.
//   내 캐릭터 = 내 users 문서에서 읽어둔 장착값(_seasonState.auraOn)
//   남        = 스쿼드 프레즌스에 실려 온 값(fromPresence)
// 어느 쪽이든 _mwAurColor 를 반드시 통과시킨다 — 색 이름이 파일 경로로 들어가는 자리라
// 카탈로그·화이트리스트를 안 거치면 남이 보낸 문자열로 경로가 만들어진다.
// 시험 스위치(murpy.app/?aur=1)는 남겨둔다. 색을 바꾸려면 ?aur=blue 처럼.
window._mwAurOf = function (uid, fromPresence) {
  if (window._AUR_TEST) {
    const c = (window._AUR_TEST === '1') ? 'blue' : window._AUR_TEST;
    return (window._MW_AUR_COLORS || []).indexOf(c) >= 0 ? c : '';
  }
  const me = (window.currentUser || {}).uid;
  const key = (uid && me && uid === me)
    ? ((window._seasonState || {}).auraOn || '')
    : (fromPresence || '');
  return window._mwAurColor(key);
};
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run: `node tools/tests/field-aura.test.mjs`
Expected: PASS

- [ ] **Step 5: 문법 검사 + 커밋**

```bash
node tools/dogam-syntax-check.mjs
git status --short
git add index.html tools/tests/field-aura.test.mjs
git commit -m "feat(field): 아우라 소유 판정 (시험 스위치 -> users 문서/프레즌스)"
```

---

### Task 4: 스쿼드 필드에서 남에게도 보이게 한다

`_sqCharEl` 이 `_mwAurOf(uid)` 를 인자 하나로 부르고 있다. 프레즌스 값을 넘기도록 고친다.

**Files:**
- Modify: `index.html` — 프레즌스 `send()` 페이로드 (`R.set(meRef, { x: ...`)
- Modify: `index.html` — `window._sqCharEl = function (uid, nick, cfg, dir, title) {`
- Modify: `index.html` — `_sqCharEl` 호출부 4곳

**Interfaces:**
- Consumes: Task 3 `_mwAurOf(uid, fromPresence)`
- Produces: `_sqCharEl(uid, nick, cfg, dir, title, aura)` — 6번째 인자 `aura` (시즌 키 문자열)

- [ ] **Step 1: 프레즌스에 aura 한 줄을 싣는다**

`R.set(meRef, {...})` 안, `title: ...` 줄 **바로 아래**에 넣는다.

```js
      aura: ((window._seasonState || {}).auraOn) || '',
```

- [ ] **Step 2: `_sqCharEl` 이 aura 를 인자로 받게 한다**

시그니처를 바꾼다.

```js
window._sqCharEl = function (uid, nick, cfg, dir, title, aura) {   // uid별 캐릭터 DOM 재사용
```

캐시 비교값에 aura 를 넣는다. **이걸 빼먹으면 아우라만 바뀐 경우 리렌더가 안 걸려 안 바뀐다.**

```js
  const cj = JSON.stringify(cfg || null) + '|' + (aura || '');
```

아우라 적용 줄을 바꾼다.

```js
    window._mwAurApply && window._mwAurApply(c.el.querySelector('.sq-body'), window._mwAurOf(uid, aura));
```

- [ ] **Step 3: 호출부 4곳에 값을 넘긴다**

```js
// (1) 내 캐릭터
  const c = window._sqCharEl(me, window._mwMyNick || '머피', window.getMyCharacter ? window.getMyCharacter() : null, dir, window._myTitle, (window._seasonState || {}).auraOn || '');
// (2) 내 캐릭터 (입장, dir 'up')
  const c = window._sqCharEl(me, window._mwMyNick || '머피', window.getMyCharacter ? window.getMyCharacter() : null, 'up', window._myTitle, (window._seasonState || {}).auraOn || '');
// (3) 정적 폴백 — 남의 장착값을 알 길이 없으므로 빈 문자열
  const c = window._sqCharEl(uid, mem[uid].nickname, mem[uid].character, 'down', '', '');
// (4) 원격(RTDB) — 프레즌스에 실려 온 값
  const c = window._sqCharEl(uid, p.nick, p.character, p.dir || 'down', p.title, p.aura);
```

- [ ] **Step 4: 문법 검사**

Run: `node tools/dogam-syntax-check.mjs`
Expected: 통과

- [ ] **Step 5: 커밋**

```bash
git status --short
git add index.html
git commit -m "feat(field): 스쿼드 프레즌스에 aura 싣기 (남에게도 보인다)"
```

---

### Task 5: 내 머피월드 필드 캐릭터에도 아우라를 붙인다

지금 아우라는 스쿼드 워킹룸에만 있다. 혼자 다닐 땐 안 보인다 — 스펙에 "혼자 다닐 때 항상 보이고"로 확정돼 있다.

**Files:**
- Modify: `index.html:3606` `window._charApplyPos` 끝

**Interfaces:**
- Consumes: Task 3 `_mwAurOf`
- Produces: 없음 (렌더만)

- [ ] **Step 1: `_charApplyPos` 끝에 아우라를 얹는다**

`_charApplyPos` 의 마지막 `host.querySelectorAll('.cw-layer').forEach(...)` 블록이 끝난 **직후**, 함수 닫는 `};` **바로 위**에 넣는다.

```js
  // ★아우라 — 캐릭터 겹을 다 그린 **뒤에** 얹는다(형제 DOM). 렌더 경로를 새로 만들지 않는다.
  //   스쿼드 필드(_sqCharEl)와 같은 _mwAurApply 를 쓰므로 두 곳의 모양이 갈라지지 않는다.
  window._mwAurApply && window._mwAurApply(host, window._mwAurOf((window.currentUser || {}).uid, ''));
```

- [ ] **Step 2: `.mw-aur` 가 이 상자에서도 맞는지 확인한다**

Run: `grep -n "\.mw-aur" index.html`

`.mw-aur` 는 `width:103%` + `left:50%` + `translateX(-50%)` 라 부모 폭을 따라간다. `#charworld-avatar` 는 `_charApplyPos` 가 `width`/`height` 를 px 로 잡아주므로 그대로 따라간다. **CSS 를 고치지 말고 먼저 실앱에서 본다** — 어긋나면 검증된 식을 건드리지 말고 덧붙여 보정한다.

- [ ] **Step 3: 문법 검사 + 커밋 + 푸시**

```bash
node tools/dogam-syntax-check.mjs
git status --short
git add index.html
git commit -m "feat(field): 머피월드 내 필드 캐릭터에도 아우라 (혼자 다닐 때도 보인다)"
git push origin main
```

- [ ] **Step 4: 실앱 확인 요청**

대표에게 `murpy.app/?aur=1` 로 **머피월드 내 필드**(스쿼드 아님)에서 발밑 고리가 도는지, 크기·위치가 스쿼드 필드와 같은지 확인받는다. 어긋나면 다음 태스크로 넘어가기 전에 여기서 잡는다.

---

### Task 6: 합판을 필드에 그린다

`#mw-furn` 은 지금 `home` 이 아니면 비운다. 여기에 헬스장 분기를 넣는다.

**Files:**
- Modify: `index.html:3060` `window.mwRenderFurn` (위에 새 함수 추가 + 분기 한 줄)
- Test: `tools/tests/field-aura.test.mjs`

**Interfaces:**
- Consumes: Task 1 `_FIELD_SPOTS`
- Produces: `window._PLATE_H` (객체), `window.mwPlateHtml(state) -> string` (state = `'closed'|'ajar'|'open'`), `window.mwPlateSet(state)` (그림만 갈아끼움)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`console.log` **바로 위**에 붙인다.

```js
// 11) 합판 HTML — 세 상태 모두 **밑변이 같은 자리**여야 한다(발자국이 안 흔들린다)
const w3 = {};
new Function('window', grab(/window\._FIELD_SPOTS = \{[\s\S]*?\n\};/, '_FIELD_SPOTS'))(w3);
new Function('window', grab(/window\._PLATE_H = \{[^}]*\};/, '_PLATE_H'))(w3);
new Function('window', grab(/window\.mwPlateHtml = function[\s\S]*?\n\};/, 'mwPlateHtml'))(w3);
const bottomOf = (html) => {
  const m = html.match(/id="mw-plate"[\s\S]*?top:([\d.]+)%[\s\S]*?height:([\d.]+)%/);
  assert(m, 'mw-plate 의 top/height 를 못 읽음');
  return +m[1] + +m[2];
};
const b1 = bottomOf(w3.mwPlateHtml('closed'));
for (const st of ['ajar', 'open']) {
  assert(Math.abs(bottomOf(w3.mwPlateHtml(st)) - b1) < 0.01, `${st} 의 밑변이 어긋난다`);
}
// 폭은 셋 다 같다
const widthOf = h => +h.match(/id="mw-plate"[\s\S]*?width:([\d.]+)%/)[1];
assert.strictEqual(widthOf(w3.mwPlateHtml('ajar')), widthOf(w3.mwPlateHtml('closed')));
// 배경에 박힌 합판을 덮는 바닥 가리개가 항상 같이 나온다
assert(/gym_plate_floor/.test(w3.mwPlateHtml('closed')), '바닥 가리개가 없다');
// 탭을 받아야 하므로 pointer-events 가 살아 있어야 한다
assert(/pointer-events:auto/.test(w3.mwPlateHtml('closed')), '합판이 탭을 못 받는다');
// 모르는 상태는 closed 로 떨어진다
assert(/gym_plate_closed/.test(w3.mwPlateHtml('nonsense')));
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `node tools/tests/field-aura.test.mjs`
Expected: FAIL — `index.html에서 _PLATE_H를 찾지 못함`

- [ ] **Step 3: `mwPlateHtml` / `mwPlateSet` 을 만든다**

`window.mwRenderFurn = function () {` **바로 위**에 넣는다.

```js
// ---- 헬스장 바닥 합판 (필드 히든 오브젝트) ----
// 그림 세 장의 높이가 다르다(closed 73 / ajar 89 / open 122). 셋 다 **밑변을 바닥선에 붙여**
// 발자국이 안 흔들리게 한다 — 위쪽으로만 커진다.
// ★합판은 배경(field_gym.png)에 이미 그려져 있다 → gym_plate_floor 로 덮은 위에 올린다.
//   안 덮으면 흔들 때 원본이 밑에서 비친다. field_gym.png 원본은 안 건드린다.
window._PLATE_H = { closed: 73, ajar: 89, open: 122 };
window.mwPlateHtml = function (state) {
  const s = ((window._FIELD_SPOTS || {}).gym || {}).plate;
  if (!s) return '';
  const F = 1024;                                   // field_gym.png 좌표계
  const pc = function (v) { return (v / F * 100).toFixed(3) + '%'; };
  const st = window._PLATE_H[state] ? state : 'closed';
  const h = window._PLATE_H[st];
  const top = s.y + s.h - h;                        // 밑변 = s.y + s.h (바닥선)
  return '<img src="char/fields/gym_plate_floor.png?v=1" alt="" style="position:absolute;'
       + 'left:' + pc(s.x) + ';top:' + pc(s.y) + ';width:' + pc(s.w) + ';height:' + pc(s.h)
       + ';z-index:4;pointer-events:none">'
       + '<img id="mw-plate" class="mw-plate" src="char/fields/gym_plate_' + st + '.png?v=1" alt=""'
       + ' onclick="window.mwPlateTap&&window.mwPlateTap()" style="position:absolute;'
       + 'left:' + pc(s.x) + ';top:' + pc(top) + ';width:' + pc(s.w) + ';height:' + pc(h)
       + ';z-index:5;pointer-events:auto;cursor:pointer">';
};
// 그림만 갈아끼운다. 통째로 다시 그리면 탭 카운트 중에 깜빡이고 onclick 이 새로 붙는다.
window.mwPlateSet = function (state) {
  const el = document.getElementById('mw-plate'); if (!el) return;
  const s = ((window._FIELD_SPOTS || {}).gym || {}).plate; if (!s) return;
  const st = window._PLATE_H[state] ? state : 'closed';
  const h = window._PLATE_H[st], F = 1024;
  el.src = 'char/fields/gym_plate_' + st + '.png?v=1';
  el.style.top = ((s.y + s.h - h) / F * 100).toFixed(3) + '%';
  el.style.height = (h / F * 100).toFixed(3) + '%';
};
```

- [ ] **Step 4: `mwRenderFurn` 에 헬스장 분기를 넣는다**

`const el = document.getElementById('mw-furn'); if (!el) return;` **바로 아래**에 한 줄 넣는다.

```js
  // 헬스장 = 바닥 합판(히든 오브젝트). 필드를 떠나면 _plateState 가 초기화된다.
  if (window._curField === 'gym') { el.innerHTML = window.mwPlateHtml(window._plateState || 'closed'); return; }
```

- [ ] **Step 5: 테스트 + 문법 검사 + 커밋**

`#mw-furn` 은 `pointer-events:none` 이지만 자식 `<img>` 가 `auto` 라 탭을 받는다. 부모는 건드리지 않는다.

```bash
node tools/tests/field-aura.test.mjs
node tools/dogam-syntax-check.mjs
git status --short
git add index.html tools/tests/field-aura.test.mjs
git commit -m "feat(field): 헬스장 바닥 합판 렌더 (바닥 가리개 + 3단 그림)"
```

---

### Task 7: 합판이 탭을 받게 한다 (조이스틱 예외)

★이걸 빼먹으면 **탭해도 아무 일도 안 일어난다.** 방 전체가 조이스틱이고 `touchstart` 에서 `preventDefault` 를 부르면 합성 click 이 취소된다. 예전에 상자가 무반응이던 원인이고 코드에 주석으로 남아 있다.

**Files:**
- Modify: `index.html` — `_initRoomJoy` 안 `const onS = (e) => { if (e.target.closest(...))`
- Test: `tools/tests/field-aura.test.mjs`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```js
// 12) ★합판이 조이스틱 예외 목록에 있어야 탭이 통한다 (상자가 무반응이던 그 버그)
const joy = grab(/const onS = \(e\) => \{ if \(e\.target\.closest\([^)]*\)\) return;/, '조이스틱 제외 선택자');
assert(/\.mw-plate/.test(joy), '합판이 조이스틱 예외 목록에 없다 → 탭해도 무반응');
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `node tools/tests/field-aura.test.mjs`
Expected: FAIL — `합판이 조이스틱 예외 목록에 없다 → 탭해도 무반응`

- [ ] **Step 3: 선택자에 `.mw-plate` 를 추가한다**

```js
    const onS = (e) => { if (e.target.closest('.mw-fieldchip, .mw-sbox, .mw-plate, #charworld-avatar, #mw-charmenu')) return;
```

- [ ] **Step 4: 테스트 + 문법 검사 + 커밋**

```bash
node tools/tests/field-aura.test.mjs
node tools/dogam-syntax-check.mjs
git status --short
git add index.html tools/tests/field-aura.test.mjs
git commit -m "fix(field): 합판을 조이스틱 예외에 추가 (탭 무반응 방지)"
```

---

### Task 8: 하단 대화창 `#mw-fieldtalk`

★새 시각 언어를 만들지 않는다. `.mw-dossier`(index.html:922) 가 이미 환세취호전·포켓몬식 텍스트 박스 스킨이다 — 지금은 히든 캐릭터 연출이 그걸 화면 **한가운데**에 띄워 쓰고 있을 뿐이다. 같은 클래스를 **필드 하단**에 붙인다.

**Files:**
- Modify: `index.html:923` 부근 — `.mw-dossier` 정의 아래에 위치 CSS 추가
- Modify: `index.html:17258` 부근 — `mwTypewriter` 에 `stop` 옵션 + 아래에 `mwFieldTalk` 추가

**Interfaces:**
- Produces: `window.mwFieldTalk(lines) -> Promise<void>` — `lines` 는 **화면 단위** 배열(한 항목이 한 화면). 탭하면 다음 화면, 마지막에서 탭하면 닫히고 resolve.

- [ ] **Step 1: CSS 를 추가한다** (`.mw-dossier` 정의 **바로 아래**)

```css
  /* 필드 하단 대화창 — 환세취호전/포켓몬식. 상자 스킨(.mw-dossier)을 그대로 쓰고 자리만 잡는다.
     ★#charworld-room 안쪽 아래에 붙는다(화면 전체가 아니다). 필드를 벗어나지 않는다. */
  #mw-fieldtalk { position:absolute; left:8px; right:8px; bottom:8px; z-index:60;
    min-height:0; padding:11px 12px 12px; font-size:12px; line-height:1.7; cursor:pointer;
    animation:mwFtIn .12s steps(2) }
  @keyframes mwFtIn { from { transform:translateY(6px); opacity:0 } }
  /* 다음 줄 표시 — ▼ 같은 기하문자는 픽셀폰트에서 깨진다. CSS 삼각형으로 그린다. */
  #mw-fieldtalk .mw-ft-caret { position:absolute; right:10px; bottom:8px; width:0; height:0;
    border-left:5px solid transparent; border-right:5px solid transparent;
    border-top:6px solid #7AA4FF; animation:mwFtBob .7s steps(2) infinite }
  @keyframes mwFtBob { 50% { transform:translateY(3px) } }
```

- [ ] **Step 2: `mwTypewriter` 에 건너뛰기(stop)를 붙인다**

지금은 중간에 멈출 수가 없다. 기존 호출부(`mwHiddenReveal`)는 `stop` 을 안 넘기므로 동작이 그대로다. `setInterval` 콜백 **첫 줄**에 넣는다.

```js
    const t = setInterval(() => {
      if (opts.stop && opts.stop()) { el.textContent = text; clearInterval(t); res(); return; }
      el.textContent = text.slice(0, ++i);
```

- [ ] **Step 3: `mwFieldTalk` 을 만든다** (`mwTypewriter` 정의 **바로 아래**)

```js
// 필드 하단 대화창. lines = 화면 단위 배열(한 항목이 한 화면, 안에서 '\n'로 줄바꿈).
// 타자기가 도는 중에 탭하면 그 화면을 즉시 다 보여주고, 다 나온 뒤 탭하면 다음 화면으로 간다.
// ★상자 스킨은 .mw-dossier 를 그대로 쓴다. 새 박스를 만들지 않는다.
window.mwFieldTalk = function (lines) {
  return new Promise(function (resolve) {
    const room = document.getElementById('charworld-room');
    if (!room || !lines || !lines.length) return resolve();
    const old = document.getElementById('mw-fieldtalk'); if (old) old.remove();
    const el = document.createElement('div');
    el.id = 'mw-fieldtalk'; el.className = 'mw-dossier';
    el.innerHTML = '<span class="mw-ft-body"></span><i class="mw-ft-caret" style="display:none"></i>';
    room.appendChild(el);
    const body = el.querySelector('.mw-ft-body'), caret = el.querySelector('.mw-ft-caret');
    let i = 0, typing = false, skip = false;
    const show = async function () {
      typing = true; caret.style.display = 'none'; skip = false;
      await window.mwTypewriter(body, [lines[i]], { tick: true, speed: 45, stop: function () { return skip; } });
      typing = false; caret.style.display = '';
    };
    el.addEventListener('click', function () {
      if (typing) { skip = true; return; }            // 타자기 건너뛰기
      i++;
      if (i >= lines.length) { el.remove(); resolve(); return; }
      show();
    });
    show();
  });
};
```

- [ ] **Step 4: 문법 검사 + 커밋**

```bash
node tools/dogam-syntax-check.mjs
git status --short
git add index.html
git commit -m "feat(field): 하단 대화창 (.mw-dossier 스킨 재사용, 새 박스 안 만듦)"
```

---

### Task 9: 밟기 → 두드리기 → 열림 → 지급

**Files:**
- Modify: `index.html` — **블록 3**: Task 6 의 `mwPlateSet` **아래**에 연출 함수들
- Modify: `index.html` — **블록 5**: `window._seasonWrite` **아래**에 `mwPlateGrant` (Firestore 를 만진다)
- Modify: `index.html:3681` 부근 — `window.charMove` (첫 줄 잠금 + 이동 성공 뒤 밟기 훅)
- Modify: `index.html:3496` 부근 — `window.charSetField` (필드 떠나면 초기화)
- Create: `char/fx/aur_blue_preview.png` (획득 모달용 정지 그림)

**Interfaces:**
- Consumes: Task 1 `_mwPlateHit`/`_PLATE_TAPS_1`/`_PLATE_TAPS_2`, Task 6 `mwPlateSet`, Task 8 `mwFieldTalk`
- Produces: `window.mwPlateStep()`, `window.mwPlateTap()`, `window.mwPlateShake()`, `window.mwPlateOpen(seasonKey, meta)`, `window.mwPlateFlash() -> Promise`, `window.mwPlateGrant(seasonKey, meta) -> Promise<boolean>`, `window._mwWait(ms) -> Promise`, `window._plateState`/`_plateTaps`/`_plateOn`/`_mwPlateBusy`

- [ ] **Step 1: 획득 모달용 미리보기 이미지를 만든다**

모달은 `it.src` 를 정지 그림으로 그린다. 아우라는 6프레임 스트립(840×45)이라 그대로 쓰면 가로로 늘어진 띠가 뜬다. 첫 프레임만 잘라 쓴다.

```bash
python -c "
from PIL import Image
im = Image.open('char/fx/aurring_blue_front.png')
im.crop((0,0,140,45)).save('char/fx/aur_blue_preview.png')
print('saved', Image.open('char/fx/aur_blue_preview.png').size)
"
```

Expected: `saved (140, 45)`

- [ ] **Step 2: 시퀀스 함수들을 만든다** (Task 6 의 `mwPlateSet` **바로 아래**)

```js
window._plateState = 'closed';
window._plateTaps = 0;
window._plateOn = '';          // 지금 밟고 있는 스팟(칸을 벗어나야 초기화)
window._mwPlateBusy = false;   // 컷신 중 조작 잠금

window._mwWait = function (ms) { return new Promise(function (r) { setTimeout(r, ms); }); };

// 두드릴 때마다 달그락. ★두드리는 맛은 소유 여부와 상관없이 준다 —
//   이미 가진 사람이 눌렀는데 아무 반응도 없으면 그냥 그림이 된다(공룡에서 얻은 규칙).
window.mwPlateShake = function () {
  const el = document.getElementById('mw-plate'); if (!el) return;
  el.style.transition = 'transform .09s steps(2)';
  el.style.transform = 'translate(1px,-2px)';
  setTimeout(function () { el.style.transform = 'translate(-1px,1px)'; }, 90);
  setTimeout(function () { el.style.transform = 'none'; }, 180);
  if (navigator.vibrate) { try { navigator.vibrate(8); } catch (e) {} }
};

// 합판을 밟았다 — 달그락 + 말 걸기. 실제로 여는 건 두드리기(mwPlateTap)다.
window.mwPlateStep = async function () {
  if (window._mwPlateBusy) return;
  window.mwPlateShake();
  const season = window._seasonEnsureMonth ? window._seasonEnsureMonth() : '';
  const meta = (window.FIELD_AURAS || {})[season];
  const had = ((window._seasonState || {}).auras || []).indexOf(season) >= 0;
  if (!meta) { await window.mwFieldTalk(['그냥 낡은 합판이다.']); return; }
  if (had)   { await window.mwFieldTalk(['아까 열어본 그 합판이다.']); return; }
  await window.mwFieldTalk(['헬스장 바닥 한쪽이 조금 이상하다..', '한번 눌러볼까?']);
};

window.mwPlateTap = async function () {
  if (window._mwPlateBusy) return;
  window.mwPlateShake();
  const season = window._seasonEnsureMonth ? window._seasonEnsureMonth() : '';
  const meta = (window.FIELD_AURAS || {})[season];
  if (!meta) return;
  const st = window._seasonState || {};
  if ((st.auras || []).indexOf(season) >= 0) return;                 // 이미 가짐 — 달그락만
  // ★임시(익명) 계정에는 주지 않는다. 그 계정을 버리면 아이템도 같이 사라져 억울해진다(공룡과 같은 규칙).
  if (!window.currentUser || (window.isTempAccount && window.isTempAccount())) return;
  window._plateTaps++;
  if (window._plateState === 'closed' && window._plateTaps >= window._PLATE_TAPS_1) {
    window._plateState = 'ajar'; window.mwPlateSet('ajar'); window._plateTaps = 0;
    await window.mwFieldTalk(['조금만 더 하면 열릴 거 같다..']);
    return;
  }
  if (window._plateState === 'ajar' && window._plateTaps >= window._PLATE_TAPS_2) {
    await window.mwPlateOpen(season, meta);
  }
};

// 다 열린다 — 캐릭터가 한 칸 뒤로 물러서고, 구멍이 드러나고, 섬광 뒤 다시 닫힌다.
window.mwPlateOpen = async function (season, meta) {
  window._mwPlateBusy = true;                    // 컷신 동안 조작 잠금
  try {
    // ★캐릭터가 구멍에 빠진 것처럼 보이지 않게 한 칸 물러선다(대표 8-18).
    //   점프가 아니라 아래로 한 칸 걷기다. 물러선 칸(tr 8)은 트리거가 아니라 재발동하지 않는다.
    const p = window._charPos;
    if (window._charWalkable && window._charWalkable(p.tc, p.tr + 1)) {
      p.tr += 1; p.face = 'up'; window._charApplyPos && window._charApplyPos();
      const av = document.getElementById('charworld-avatar');
      if (av) { av.style.scale = '0.95 1.04'; setTimeout(function () { av.style.scale = '1 1'; }, 140); }
    }
    window._plateState = 'open'; window.mwPlateSet('open');
    await window._mwWait(260);
    await window.mwFieldTalk(['합판 아래에서 무언가 빛나고 있다.']);
    const ok = await window.mwPlateGrant(season, meta);
    await window.mwPlateFlash();
    window._plateState = 'closed'; window._plateTaps = 0; window.mwPlateSet('closed');
    if (ok) {
      window.mwSeasonCelebrate({
        id: 'aura_' + season, name: meta.name, title: meta.title, desc: meta.desc,
        src: 'char/fx/aur_' + meta.color + '_preview.png?v=1', w: 140, h: 45
      });
    }
  } finally { window._mwPlateBusy = false; }
};

// 흰 섬광 한 번. 그림이 아니라 CSS 다.
window.mwPlateFlash = function () {
  return new Promise(function (res) {
    const room = document.getElementById('charworld-room'); if (!room) return res();
    const f = document.createElement('div');
    f.style.cssText = 'position:absolute;inset:0;z-index:80;background:#fff;opacity:0;'
      + 'pointer-events:none;transition:opacity .12s linear';
    room.appendChild(f);
    requestAnimationFrame(function () {
      f.style.opacity = '1';
      setTimeout(function () {
        f.style.transition = 'opacity .34s ease-out'; f.style.opacity = '0';
        setTimeout(function () { f.remove(); res(); }, 360);
      }, 120);
    });
  });
};
```

- [ ] **Step 3: 지급 함수를 만든다 (★블록 5)**

`arrayUnion` 을 쓰므로 **블록 3 에 두면 `ReferenceError` 로 터진다.** 블록 5 의
`window._seasonWrite = async function ...` 정의 **바로 아래**에 넣는다.

```js
// 합판 보상 지급 — 소유(fieldAuras)에 넣고 **바로 켜준다**(aura). 얻자마자 꺼져 있으면
// 모달을 닫는 순간 아무 일도 안 일어난 것처럼 보인다. 끄는 건 꾸미기에서 한다.
// ★쓰기가 성공했을 때만 로컬에 반영한다 — 실패한 쓰기를 먼저 반영하면 새로고침에 사라지는 유령 지급이 된다.
// ★여기는 모듈 블록이라 arrayUnion 을 쓸 수 있다. 부르는 쪽(mwPlateOpen)은 블록 3 이라
//   window.mwPlateGrant 로 건너온다.
window.mwPlateGrant = async function (season, meta) {
  const user = window.currentUser; if (!user || !season || !meta) return false;
  try {
    const upd = { fieldAuras: arrayUnion(season), aura: season };
    if (meta.title) upd.titles = arrayUnion(meta.title);
    await window._seasonWrite(user.uid, upd);
  } catch (e) { console.warn('aura grant', e); return false; }
  const st = window._seasonState;
  if ((st.auras || []).indexOf(season) < 0) st.auras = (st.auras || []).concat(season);
  st.auraOn = season;
  if (meta.title && (st.titles || []).indexOf(meta.title) < 0) st.titles = (st.titles || []).concat(meta.title);
  window._charApplyPos && window._charApplyPos();          // 내 필드 캐릭터에 즉시 반영
  window._sqRtSend && window._sqRtSend();                  // 스쿼드 필드면 남에게도 즉시
  return true;
};
```

- [ ] **Step 4: 컷신 중에는 못 움직이게 막는다**

`window.charMove = function (dx, dy) {` **바로 다음 줄**에 넣는다.

```js
  if (window._mwPlateBusy) return;   // 합판 컷신 중엔 조작을 막는다(드래그로 구멍을 뚫고 지나간다)
```

- [ ] **Step 5: `charMove` 에 밟기 훅을 넣는다**

`if (canMove) { window._charPos.tc = ntc; window._charPos.tr = ntr; }` **바로 아래**에 넣는다.

```js
  // ★히든 오브젝트 밟기. 이동에 성공했을 때만 보고, 칸을 벗어났다 다시 들어와야 재발동한다
  //   (같은 칸에서 걸음마다 반복되면 대화창이 계속 뜬다).
  if (canMove) {
    const hit = window._mwPlateHit ? window._mwPlateHit(window._curField, window._charPos.tc, window._charPos.tr) : '';
    if (!hit) window._plateOn = '';
    else if (window._plateOn !== hit) { window._plateOn = hit; window.mwPlateStep && window.mwPlateStep(); }
  }
```

- [ ] **Step 6: 필드를 떠나면 초기화한다**

`charSetField` 안 `window._curField = key;` **바로 아래**에 넣는다.

```js
  // 합판은 전부 지나가는 상태다 — 필드를 떠나면 그림·탭 수를 되돌린다
  window._plateState = 'closed'; window._plateTaps = 0; window._plateOn = '';
  const _ft = document.getElementById('mw-fieldtalk'); if (_ft) _ft.remove();
```

- [ ] **Step 7: 테스트 + 문법 검사 + 커밋**

```bash
node tools/tests/field-aura.test.mjs
node tools/dogam-syntax-check.mjs
git status --short
git add index.html char/fx/aur_blue_preview.png
git commit -m "feat(field): 합판 밟기 -> 두드리기 -> 열림 -> 아우라 지급"
```

---

### Task 10: 꾸미기에 '이펙트' 칸

**Files:**
- Modify: `index.html:3110` 부근 — `mwRoomEdit` 의 '한정 오브젝트' 즉시실행 블록 **아래**
- Modify: `index.html` — **블록 5**: Task 9 의 `mwPlateGrant` **바로 아래**에 `mwAuraToggle`
  (`mwRoomEdit` 은 블록 3 이지만 `window.mwAuraToggle` 로 런타임에 건너온다)

**Interfaces:**
- Consumes: Task 2 `_seasonState.auras`/`auraOn`, Task 1 `FIELD_AURAS`
- Produces: `window.mwAuraToggle(seasonKey)`

- [ ] **Step 1: 카탈로그 칸을 그린다**

`mwRoomEdit` 안, '한정 오브젝트' 를 그리는 즉시실행 블록 **바로 아래**에 같은 문법으로 붙인다.

```js
      ${(() => {
        // 필드 아우라 — 가진 게 하나도 없으면 이 칸은 아예 안 그린다(한정 오브젝트와 같은 규칙).
        const owned = ((window._seasonState || {}).auras || [])
          .filter(k => (window.FIELD_AURAS || {})[k]);
        if (!owned.length) return '';
        const on = (window._seasonState || {}).auraOn || '';
        return `<div class="mw-redit-cathead">캐릭터 이펙트<span>${owned.length}</span></div>
          <div class="mw-redit-cat">${owned.map(k => {
            const m = window.FIELD_AURAS[k];
            // ★틴트 칩 금지 — 색면 배지를 쓰지 않는다. 켜짐은 글자색으로만 구분한다
            //   (정답 모양 = 스쿼드 '입금 ✓' 토글).
            const lit = (k === on);
            return `<button onclick="window.mwAuraToggle('${k}')"${lit ? '' : ' style="opacity:.72"'}><span class="thumb"><img src="char/fx/aur_${m.color}_preview.png?v=1" draggable="false"></span><span>${m.name}</span><span style="font-size:9.5px;background:none;color:${lit ? '#7AA4FF' : 'rgba(255,255,255,.3)'}">${lit ? '켜짐' : '꺼짐'}</span></button>`;
          }).join('')}
          </div>`;
      })()}
```

- [ ] **Step 2: 켜기/끄기를 만든다** (★블록 5, Task 9 의 `mwPlateGrant` **바로 아래**)

```js
// 아우라 켜기/끄기. 한 번에 하나만 켠다(aura 가 단일 값이다).
window.mwAuraToggle = async function (key) {
  const user = window.currentUser; if (!user) return;
  const st = window._seasonState || {};
  if ((st.auras || []).indexOf(key) < 0) return;         // 안 가진 건 못 켠다
  const next = (st.auraOn === key) ? '' : key;
  try { await window._seasonWrite(user.uid, { aura: next }); }
  catch (e) { console.warn('aura toggle', e); return; }
  st.auraOn = next;
  window._charApplyPos && window._charApplyPos();         // 내 필드에 즉시 반영
  window._sqRtSend && window._sqRtSend();                 // 스쿼드 필드면 남에게도 즉시
  window.mwRoomEdit && window.mwRoomEdit();               // 카탈로그를 다시 그려 켜짐 표시 갱신
};
```

- [ ] **Step 3: 문법 검사 + 커밋**

```bash
node tools/dogam-syntax-check.mjs
git status --short
git add index.html
git commit -m "feat(room): 꾸미기에 캐릭터 이펙트 칸 (켜기/끄기)"
```

---

### Task 11: 배포 + 실앱 검증

**Files:**
- Modify: `index.html` — `window._SW_V`
- Modify: `sw.js` — 캐시 이름 3줄 (★Edit 도구로만. PowerShell 금지)

- [ ] **Step 1: 전체 테스트**

```bash
node tools/tests/field-aura.test.mjs
node tools/tests/box-spot.test.mjs
node tools/tests/dogam-bonus.test.mjs
node tools/tests/field-place.test.mjs
node tools/dogam-syntax-check.mjs
```
Expected: 전부 통과

- [ ] **Step 2: `<script>` 6블록 문법 검사**

```bash
python -c "
import re,subprocess,os,tempfile
s=open('index.html',encoding='utf-8').read()
b=re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', s, re.S)
print('blocks:',len(b))
for i,x in enumerate(b):
    p=os.path.join(tempfile.gettempdir(),'chk%d.js'%i); open(p,'w',encoding='utf-8').write(x)
    r=subprocess.run(['node','--check',p],capture_output=True,text=True)
    print(i,'OK' if r.returncode==0 else 'FAIL'); print(r.stderr[:600] if r.returncode else '')
"
```
Expected: `blocks: 6` 이고 전부 `OK`

- [ ] **Step 3: sw 버전 올리기**

새 에셋(`char/fields/gym_plate_*`, `char/fx/aur_blue_preview.png`)이 들어갔으므로 이번엔 꼭 올린다. `sw.js` 의 세 곳과 `index.html` 의 `_SW_V` 를 **같은 숫자**로.

```bash
grep -n "_SW_V" index.html | tail -1
grep -n "murpy-v\|murpy-static-v\|murpy-cdn-v" sw.js
```

- [ ] **Step 4: 커밋 + 푸시**

```bash
git status --short
git add index.html sw.js
git commit -m "chore: sw 버전 올림 (합판 이스터에그 에셋)"
git push origin main
```

- [ ] **Step 5: 대표 실앱 확인 요청**

앱을 완전히 껐다 켠 뒤 확인받는다.

1. 머피월드 → 이동 → **헬스장** → 합판 칸(러닝머신 왼쪽 바닥)을 **밟으면** 달그락 + 대화창
2. 합판을 **10번 두드리면** 살짝 열리고 `조금만 더 하면 열릴 거 같다..`
3. 거기서 **30번 더 두드리면** 캐릭터가 한 칸 물러서고 활짝 열림 → 획득 문구 → 섬광 → 닫힘 → 획득 모달
4. 꾸미기에 **캐릭터 이펙트** 칸이 생기고, 켜면 내 필드 캐릭터 발밑에 고리가 돈다. 끄면 사라진다
5. 스쿼드 실시간 필드에서 **남에게도** 보인다
6. 같은 합판을 다시 밟으면 `아까 열어본 그 합판이다.` 로 끝난다 (중복 지급 없음)
7. **안 가진 사람에게는 안 보인다** — `?aur=1` 없이 확인

- [ ] **Step 6: 메모리 갱신**

`project_murpy_field_artifact.md` 와 `project_murpy_session_resume.md` 를 배포 커밋·sw 버전으로 갱신하고, 실앱에서 튜닝한 값(탭 수·연출 길이·아우라 크기)이 있으면 같이 적는다.
