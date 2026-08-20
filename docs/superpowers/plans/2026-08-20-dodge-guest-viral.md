# 덤벨 피하기 미가입자 바이럴 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 카톡·인스타 링크를 누르면 가입도 로그인도 없이 바로 덤벨 피하기가 시작되고, 한 판 끝난 뒤에 닉네임(임시계정)을 받아 점수를 지킨다.

**Architecture:** 앱 전체가 단일 `index.html` 이다. 새 화면을 만들지 않는다 — 게임·공유 카드·게스트 닉네임 시트·가입 권유 팝업이 전부 이미 있고, 끊긴 자리만 잇는다. 이번 작업이 만지는 코드는 **전부 블록 5(모듈)** 안에 있어 블록을 넘나들지 않는다. 링크 파싱·점수 승격 같은 판정은 순수 함수로 빼서 node 로 검증한다.

**Tech Stack:** 바닐라 JS + Firebase(Auth 익명 로그인 / Firestore) + localStorage. 빌드 없음. 테스트는 node 내장 `assert`.

**Spec:** `docs/superpowers/specs/2026-08-20-dodge-guest-viral-design.md`

## Global Constraints

- **저장소:** `C:\Users\allys\Murpy` / 브랜치 `main`. 앱 전체가 `index.html` 한 파일.
- **★다른 창이 같은 `index.html` 에서 '머피월드 방 초대'를 만든다.** 구역이 갈려 있다:

  | 자리 | 누가 |
  |---|---|
  | 비로그인 if/else 사슬 (`_mwRoomInvite` 가지, `onAuthStateChanged` 안) | **다른 창** — 한 글자도 안 건드린다 |
  | `?room=` / `_mwRoomInvite` / `mwVisitRoom` / `mwRoomEnterChoice` | **다른 창** |
  | `?game=` / `dodge*` / `#dodge-*` / `window.DODGE` | **나** |
  | `_notMember` / `memberGate` / `requireRealAccount` | **아무도 안 건드린다** |
  | `mwShareKakao` / `mwShareSheet` / `mwSaveStamp` / `_dodgeCardImg` | **부르기만** 한다 |
  | `_guestGoSquad` | **나** (콜백 훅 2줄) |

- **커밋 전 반드시 `git diff` 를 눈으로 본다.** 내가 안 쓴 코드가 보이면 다른 창 것이다.
  `git add index.html` 로 통째로 담지 말고 **내 헝크만** 담는다. 커밋 뒤 `git log -1 --stat` 으로 줄 수를 확인한다.
- **sw 버전은 새 에셋 파일을 추가할 때만 올린다.** 이 작업은 에셋을 안 만드므로 **안 올린다** —
  `index.html` 은 sw 가 `cache:'no-store'` 로 매번 새로 받아 HTML 변경은 그냥 폰에 간다.
- **배포 전 필수:** `node tools/dogam-syntax-check.mjs` 통과.
- **`sw.js` 는 PowerShell 로 편집 금지** (인코딩 깨짐). Edit 도구로만.
- **이모지 금지.** 머피 전용 라인 SVG 아이콘만. 블록·기하문자(`▓`,`▼`)도 금지 — 픽셀폰트에서 깨진다.
- **틴트 칩 금지.** 반투명 색면 배지 대신 `background:none` + 테두리 + 글자색.
- **인라인 style 을 `''` 로 지우지 말 것** — 원래 값을 다시 박는다.
- **색:** 파랑 `var(--accent)` = 액션. 골드 `#F5C24B` = 별점·코인·칭호 전용.
- **URL 값은 남이 고칠 수 있다.** 화면에 넣을 땐 `textContent` 로만. `innerHTML` 금지.
- **카드 그림(`_dodgeCardImg`)·카톡 문구(`title`/`desc`/`btn`)·공유 버튼 3칸은 손대지 않는다.**

---

### Task 1: 링크 파싱·만들기 (순수 함수)

도전장 링크를 읽고 쓰는 판정을 순수 함수로 뺀다. URL 값은 남이 고칠 수 있으므로 여기가 **방어선**이다.

**Files:**
- Modify: `index.html` — `window.DODGE = {` (약 11792행) 정의 **바로 위**
- Test: `tools/tests/dodge-guest.test.mjs` (신규)

**Interfaces:**
- Produces:
  - `window.dodgeParseLink(search) -> {on:boolean, nick:string, score:number}`
    (`search` = `location.search` 같은 문자열)
  - `window.dodgeMakeLink(nick, score) -> string` (절대 URL)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tools/tests/dodge-guest.test.mjs` 를 만든다.

```js
// 덤벨 피하기 미가입자 바이럴 — 순수함수 테스트 (index.html 에서 추출해 검증)
// 실행: node tools/tests/dodge-guest.test.mjs
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
new Function('window', grab(/window\.DODGE = \{[\s\S]*?\n\};/, 'DODGE'))(w);
new Function('window', grab(/window\.dodgeParseLink = function[\s\S]*?\n\};/, 'dodgeParseLink'))(w);
new Function('window', grab(/window\.dodgeMakeLink = function[\s\S]*?\n\};/, 'dodgeMakeLink'))(w);

// 1) 정상 링크
let r = w.dodgeParseLink('?game=dodge&n=%ED%8C%A8%EC%88%98%ED%98%84&s=320');
assert.strictEqual(r.on, true, '게임 링크를 못 알아본다');
assert.strictEqual(r.nick, '패수현');
assert.strictEqual(r.score, 320);

// 2) game 파라미터가 없거나 다른 값이면 꺼진다 (방 초대 ?room= 을 삼키면 안 된다)
assert.strictEqual(w.dodgeParseLink('').on, false);
assert.strictEqual(w.dodgeParseLink('?room=abc123').on, false, '방 초대 링크를 게임이 가로챈다');
assert.strictEqual(w.dodgeParseLink('?sq=xyz').on, false, '스쿼드 초대 링크를 게임이 가로챈다');
assert.strictEqual(w.dodgeParseLink('?game=tennis').on, false, '모르는 게임을 연다');

// 3) ★점수 조작 방어 — MAX_SCORE 로 자른다
assert.strictEqual(w.dodgeParseLink('?game=dodge&s=999999').score, w.DODGE.MAX_SCORE);
assert.strictEqual(w.dodgeParseLink('?game=dodge&s=-5').score, 0);
assert.strictEqual(w.dodgeParseLink('?game=dodge&s=abc').score, 0);
assert.strictEqual(w.dodgeParseLink('?game=dodge&s=3.7').score, 3);
assert.strictEqual(w.dodgeParseLink('?game=dodge').score, 0, '점수가 없으면 0');

// 4) 닉네임 — 12자로 자르고, 없으면 빈 문자열
assert.strictEqual(w.dodgeParseLink('?game=dodge&n=' + encodeURIComponent('가'.repeat(30))).nick.length, 12);
assert.strictEqual(w.dodgeParseLink('?game=dodge').nick, '');
// 태그 문자는 그대로 돌려준다 — 지우는 게 아니라 **넣을 때 textContent 로** 막는다.
// 여기서 지우면 '<' 를 쓴 진짜 닉네임이 망가진다.
assert.strictEqual(w.dodgeParseLink('?game=dodge&n=' + encodeURIComponent('<b>')).nick, '<b>');

// 5) 깨진 URL 인코딩에도 안 터진다
assert.doesNotThrow(() => w.dodgeParseLink('?game=dodge&n=%E0%A4%A'));

// 6) 링크 만들기 — 항상 murpy.app, 닉네임은 인코딩
const link = w.dodgeMakeLink('패 수&현', 320);
assert(link.startsWith('https://murpy.app/?game=dodge'), '정식 주소가 아니다: ' + link);
assert(link.includes('s=320'));
assert(!link.includes('패 수&현'), '닉네임이 인코딩되지 않았다 — & 가 파라미터를 쪼갠다');
assert.strictEqual(w.dodgeParseLink(link.slice(link.indexOf('?'))).nick, '패 수&현', '만든 링크를 다시 못 읽는다');

// 7) 닉네임이 없어도 링크는 만들어진다
const bare = w.dodgeMakeLink('', 0);
assert(bare.startsWith('https://murpy.app/?game=dodge'));

console.log('dodge-guest.test.mjs: 링크 파싱·만들기 통과 OK');
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `node tools/tests/dodge-guest.test.mjs`
Expected: FAIL — `index.html에서 dodgeParseLink를 찾지 못함`

- [ ] **Step 3: 최소 구현을 넣는다**

`window.DODGE = {` 줄을 찾아 **그 바로 위**에 넣는다.

```js
// ===== 미가입자 바이럴 링크 (덤벨 피하기) =====
// 스펙: docs/superpowers/specs/2026-08-20-dodge-guest-viral-design.md
// murpy.app/?game=dodge&n=<닉네임>&s=<점수>  → 로그인 없이 바로 게임 + 도전장 표시
// ★값은 **남이 고칠 수 있다.** 링크를 손으로 바꿔 s=999999 를 넣을 수 있으므로 여기서 자른다.
//   닉네임의 태그 문자는 **지우지 않는다** — 지우면 '<' 를 쓴 진짜 닉네임이 망가진다.
//   막는 건 넣을 때다: 화면에는 반드시 textContent 로만 넣는다.
window.dodgeParseLink = function (search) {
  const off = { on: false, nick: '', score: 0 };
  let q;
  try { q = new URLSearchParams(search || ''); } catch (e) { return off; }
  if (q.get('game') !== 'dodge') return off;      // ?room= ?sq= 등 남의 링크를 가로채지 않는다
  let nick = '';
  try { nick = q.get('n') || ''; } catch (e) { nick = ''; }
  const raw = parseInt(q.get('s'), 10);
  const max = (window.DODGE && window.DODGE.MAX_SCORE) || 9999;
  return {
    on: true,
    nick: String(nick).slice(0, 12),
    score: (isFinite(raw) && raw > 0) ? Math.min(max, Math.floor(raw)) : 0
  };
};
// ★공유 링크는 **항상 정식 주소**로 만든다(mwShareKakao 와 같은 규칙). 지금 앱을 어디서
//   열었든 남에게 나가는 링크는 murpy.app 이어야 한다 — 옛 주소가 퍼지면 나중에 그 카드들이 죽는다.
window.dodgeMakeLink = function (nick, score) {
  const max = (window.DODGE && window.DODGE.MAX_SCORE) || 9999;
  const s = Math.max(0, Math.min(max, Math.floor(score || 0)));
  let u = 'https://murpy.app/?game=dodge&s=' + s;
  if (nick) u += '&n=' + encodeURIComponent(String(nick).slice(0, 12));
  return u;
};
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run: `node tools/tests/dodge-guest.test.mjs`
Expected: PASS — `링크 파싱·만들기 통과 OK`

- [ ] **Step 5: 문법 검사 + 커밋**

```bash
node tools/dogam-syntax-check.mjs
git diff --stat
git add index.html tools/tests/dodge-guest.test.mjs
git commit -m "feat(dodge): 도전장 링크 파싱·만들기 (순수함수)"
```

---

### Task 2: 게스트 점수 보관·승격 (순수 함수)

계정이 없는 동안 점수를 폰에 들고 있다가, 계정이 생기면 옮긴다.

**Files:**
- Modify: `index.html` — Task 1 의 `dodgeMakeLink` **바로 아래**
- Test: `tools/tests/dodge-guest.test.mjs`

**Interfaces:**
- Consumes: Task 1 없음 (독립)
- Produces:
  - `window.DODGE_GUEST_KEY` = `'murpy_dodge_guest'`
  - `window.dodgeGuestMerge(cur, rec, max) -> {best:number, recent:Array, plays:number}`
    순수 함수. `cur` = 지금 보관분(없으면 `null`), `rec` = `{s,t,lv,at}`, `max` = 보관 개수
  - `window.dodgeGuestLoad() -> object|null` / `window.dodgeGuestSave(obj)` / `window.dodgeGuestClear()`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tools/tests/dodge-guest.test.mjs` 의 `console.log` **바로 위**에 붙인다.

```js
// 8) 게스트 점수 보관 — Firestore 의 games.dodge 와 **같은 모양**이어야 옮길 때 변환이 없다
new Function('window', grab(/window\.dodgeGuestMerge = function[\s\S]*?\n\};/, 'dodgeGuestMerge'))(w);

let g = w.dodgeGuestMerge(null, { s: 120, t: 30, lv: 'mid', at: 1000 }, 20);
assert.strictEqual(g.best, 120, '첫 기록이 최고점이 안 된다');
assert.strictEqual(g.plays, 1);
assert.strictEqual(g.recent.length, 1);

// 더 낮은 점수를 내도 최고점은 안 내려간다
g = w.dodgeGuestMerge(g, { s: 50, t: 12, lv: 'mid', at: 2000 }, 20);
assert.strictEqual(g.best, 120, '낮은 점수가 최고점을 덮었다');
assert.strictEqual(g.plays, 2);

// 최신 판이 **앞**에 온다
assert.strictEqual(g.recent[0].s, 50, '최신 판이 맨 앞이 아니다');

// 더 높은 점수는 갱신된다
g = w.dodgeGuestMerge(g, { s: 300, t: 60, lv: 'hard', at: 3000 }, 20);
assert.strictEqual(g.best, 300);

// max 를 넘으면 오래된 것부터 버린다
let many = null;
for (let i = 0; i < 30; i++) many = w.dodgeGuestMerge(many, { s: i, t: i, lv: 'mid', at: i }, 20);
assert.strictEqual(many.recent.length, 20, '보관 개수를 안 자른다');
assert.strictEqual(many.recent[0].s, 29, '최신이 맨 앞이 아니다');

// 망가진 보관분이 들어와도 안 터진다 (localStorage 는 사람이 고칠 수 있다)
assert.doesNotThrow(() => w.dodgeGuestMerge({ best: 'x', recent: 'nope' }, { s: 10, t: 1, lv: 'mid', at: 1 }, 20));
const fixed = w.dodgeGuestMerge({ best: 'x', recent: 'nope' }, { s: 10, t: 1, lv: 'mid', at: 1 }, 20);
assert.strictEqual(fixed.best, 10, '망가진 best 를 복구 못 한다');
assert(Array.isArray(fixed.recent), '망가진 recent 를 배열로 못 되돌린다');
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `node tools/tests/dodge-guest.test.mjs`
Expected: FAIL — `index.html에서 dodgeGuestMerge를 찾지 못함`

- [ ] **Step 3: 구현을 넣는다**

Task 1 의 `dodgeMakeLink` 정의 **바로 아래**에 넣는다.

```js
// ---- 계정이 없는 동안의 점수 보관 ----
// ★Firestore 의 users/{uid}.games.dodge 와 **같은 모양**으로 들고 있는다.
//   모양이 다르면 계정이 생겼을 때 변환하다 어긋난다.
window.DODGE_GUEST_KEY = 'murpy_dodge_guest';
// 순수 함수 — localStorage 를 모른다(그래야 node 로 검증할 수 있다).
window.dodgeGuestMerge = function (cur, rec, max) {
  const c = (cur && typeof cur === 'object') ? cur : {};
  const oldBest = (typeof c.best === 'number' && isFinite(c.best)) ? c.best : 0;
  const oldRecent = Array.isArray(c.recent) ? c.recent : [];
  const oldPlays = (typeof c.plays === 'number' && isFinite(c.plays)) ? c.plays : 0;
  const s = Math.max(0, Math.floor((rec && rec.s) || 0));
  return {
    best: Math.max(oldBest, s),
    plays: oldPlays + 1,
    recent: [rec].concat(oldRecent).slice(0, max || 20),
    lastAt: (rec && rec.at) || Date.now()
  };
};
window.dodgeGuestLoad = function () {
  try { return JSON.parse(localStorage.getItem(window.DODGE_GUEST_KEY) || 'null'); }
  catch (e) { return null; }
};
window.dodgeGuestSave = function (o) {
  try { localStorage.setItem(window.DODGE_GUEST_KEY, JSON.stringify(o)); } catch (e) {}
};
// ★옮기고 나면 반드시 비운다. 두 벌로 남으면 어느 게 진짜인지 알 수 없어진다.
window.dodgeGuestClear = function () {
  try { localStorage.removeItem(window.DODGE_GUEST_KEY); } catch (e) {}
};
```

- [ ] **Step 4: 테스트 + 문법 검사 + 커밋**

```bash
node tools/tests/dodge-guest.test.mjs
node tools/dogam-syntax-check.mjs
git diff --stat
git add index.html tools/tests/dodge-guest.test.mjs
git commit -m "feat(dodge): 계정 없는 동안 점수를 폰에 보관 (순수함수)"
```

---

### Task 3: `dodgeSave` 가 계정 없어도 안 버리게

지금은 `if (!user) return;` 로 **조용히 버린다.** 비회원이 최고점을 내도 사라진다.

**Files:**
- Modify: `index.html:12485` 부근 — `window.dodgeSave = async function`
- Test: `tools/tests/dodge-guest.test.mjs`

**Interfaces:**
- Consumes: Task 2 `dodgeGuestMerge`/`dodgeGuestLoad`/`dodgeGuestSave`, `DODGE_RECS_MAX`
- Produces: `dodgeSave` 가 계정이 없으면 localStorage 에 쌓는다(시그니처 그대로)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`console.log` **바로 위**에 붙인다.

```js
// 9) 계정이 없어도 점수를 버리지 않는다
const save = grab(/window\.dodgeSave = async function[\s\S]*?\n\};/, 'dodgeSave');
assert(!/if \(!user\) return;/.test(save),
  'dodgeSave 가 계정 없으면 그냥 버린다 → 비회원 최고점이 사라진다');
assert(/dodgeGuestSave\(/.test(save) && /dodgeGuestMerge\(/.test(save),
  'dodgeSave 가 계정 없을 때 폰에 보관하지 않는다');
// 보관 뒤에는 반드시 return — 그 아래 Firestore 코드로 흘러가면 터진다
assert(/dodgeGuestSave\([\s\S]{0,200}?return;/.test(save),
  '게스트 보관 뒤 return 이 없다 → Firestore 코드로 흘러간다');
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `node tools/tests/dodge-guest.test.mjs`
Expected: FAIL — `dodgeSave 가 계정 없으면 그냥 버린다`

- [ ] **Step 3: 첫 줄을 바꾼다**

`window.dodgeSave = async function (score, sec, lvKey) {` 다음 줄
`const user = auth.currentUser || window.currentUser; if (!user) return;` 를 이걸로 바꾼다.

```js
  const user = auth.currentUser || window.currentUser;
  const n0 = Math.max(0, Math.min(window.DODGE.MAX_SCORE, Math.floor(score || 0)));
  // ★계정이 없어도 **버리지 않는다.** 링크로 들어온 사람은 계정이 없는 채로 한 판을 한다 —
  //   여기서 버리면 "기록 남기기"를 눌러도 남길 게 없다. 폰에 들고 있다가 계정이 생기면 옮긴다.
  if (!user) {
    const rec = { s: n0, t: Math.max(0, Math.floor(sec || 0)), lv: lvKey || 'mid', at: Date.now() };
    const merged = window.dodgeGuestMerge(window.dodgeGuestLoad(), rec, window.DODGE_RECS_MAX);
    window.dodgeGuestSave(merged);
    window._dodgeBest = Math.max(window._dodgeBest || 0, merged.best || 0);   // 시작화면 표시용
    return;
  }
```

- [ ] **Step 4: 테스트 + 문법 검사 + 커밋**

```bash
node tools/tests/dodge-guest.test.mjs
node tools/dogam-syntax-check.mjs
git diff --stat
git add index.html tools/tests/dodge-guest.test.mjs
git commit -m "feat(dodge): 계정 없어도 점수를 안 버린다 (폰에 보관)"
```

---

### Task 4: 게스트 점수를 계정으로 옮기기

**Files:**
- Modify: `index.html` — `window.dodgeSave` 정의 **바로 아래**
- Modify: `index.html:17522` 부근 — `window._guestGoSquad` (콜백 훅 2줄)
- Test: `tools/tests/dodge-guest.test.mjs`

**Interfaces:**
- Consumes: Task 2 `dodgeGuestLoad`/`dodgeGuestClear`
- Produces: `window.dodgeGuestPromote() -> Promise<boolean>` (옮겼으면 true),
  `window._guestAfter` (일회용 콜백. `_guestGoSquad` 가 있으면 부르고 비운다)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`console.log` **바로 위**에 붙인다.

```js
// 10) 게스트 닉네임 저장이 끝난 뒤 **어디로 갈지**를 부르는 쪽이 정할 수 있어야 한다
//     (스쿼드에서 왔으면 스쿼드로, 게임에서 왔으면 게임으로)
const gogo = grab(/window\._guestGoSquad = function[\s\S]*?\n\};/, '_guestGoSquad');
assert(/_guestAfter/.test(gogo), '_guestGoSquad 에 콜백 훅이 없다 → 게임에서 와도 스쿼드로 간다');
assert(/window\._guestAfter = null/.test(gogo), '콜백을 비우지 않는다 → 다음 번에 또 불린다');
// 콜백이 없으면 지금 동작 그대로여야 한다(스쿼드 흐름 무영향)
assert(/_sqInviteSid/.test(gogo), '스쿼드 흐름이 사라졌다');

// 11) 승격 함수 — 옮기고 나면 폰 보관분을 비운다
const pro = grab(/window\.dodgeGuestPromote = async function[\s\S]*?\n\};/, 'dodgeGuestPromote');
assert(/dodgeGuestClear\(\)/.test(pro), '옮긴 뒤 폰 보관분을 안 비운다 → 두 벌이 남는다');
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `node tools/tests/dodge-guest.test.mjs`
Expected: FAIL — `_guestGoSquad 에 콜백 훅이 없다`

- [ ] **Step 3: `_guestGoSquad` 에 콜백 훅을 넣는다**

```js
window._guestGoSquad = function () {
  if (typeof dismissLanding === 'function') dismissLanding();
  // ★부른 쪽이 '끝나고 어디로 갈지'를 정할 수 있게 한다 (덤벨 피하기에서 닉네임을 받는 경우).
  //   안 정했으면 아래 스쿼드 흐름 그대로다 — 기존 동작은 한 글자도 안 바뀐다.
  const after = window._guestAfter;
  if (after) { window._guestAfter = null; try { after(); } catch (e) { console.warn('guest after', e); } return; }
  const sid = window._sqInviteSid;
  if (sid && window.openSquadDetail) setTimeout(function () { window.openSquadDetail(sid); }, 300);
};
```

- [ ] **Step 4: 승격 함수를 만든다**

`window.dodgeSave` 정의 **바로 아래**에 넣는다.

```js
// 폰에 들고 있던 게스트 점수를 지금 계정으로 옮긴다. 옮겼으면 true.
// ★쓰기가 성공했을 때만 폰 보관분을 비운다 — 실패했는데 비우면 기록이 통째로 증발한다.
window.dodgeGuestPromote = async function () {
  const user = auth.currentUser || window.currentUser; if (!user) return false;
  const g = window.dodgeGuestLoad();
  if (!g || !(g.best > 0)) { window.dodgeGuestClear(); return false; }
  try {
    const ref = doc(db, 'users', user.uid);
    const snap = await getDoc(ref);
    const cur = ((snap.exists() && snap.data().games) || {}).dodge || {};
    const recs = (Array.isArray(g.recent) ? g.recent : [])
      .concat(Array.isArray(cur.recent) ? cur.recent : [])
      .sort(function (a, b) { return (b.at || 0) - (a.at || 0); })
      .slice(0, window.DODGE_RECS_MAX);
    await updateDoc(ref, {
      'games.dodge.best': Math.max(cur.best || 0, g.best || 0),
      'games.dodge.plays': increment(g.plays || 1),
      'games.dodge.recent': recs,
      'games.dodge.lastAt': Date.now()
    });
  } catch (e) { console.warn('dodge promote', e); return false; }
  window.dodgeGuestClear();
  window._dodgeBest = Math.max(window._dodgeBest || 0, g.best || 0);
  return true;
};
```

- [ ] **Step 5: 테스트 + 문법 검사 + 커밋**

```bash
node tools/tests/dodge-guest.test.mjs
node tools/dogam-syntax-check.mjs
git diff --stat
git add index.html tools/tests/dodge-guest.test.mjs
git commit -m "feat(dodge): 게스트 점수를 계정으로 옮기기 + _guestGoSquad 콜백 훅"
```

---

### Task 5: 게임오버에 「기록 남기기」

**Files:**
- Modify: `index.html:2201` 부근 — `#dodge-share` 아래에 자리 하나 추가
- Modify: `index.html` — `window._dodgeShowShare` (약 12458행) 안에서 그 자리를 채운다
- Modify: `index.html` — Task 4 의 `dodgeGuestPromote` 아래에 `dodgeSaveRecord`

**Interfaces:**
- Consumes: Task 4 `dodgeGuestPromote`, 기존 `guestAskNick`, `guestNudge`
- Produces: `window.dodgeSaveRecord()` (게임오버의 「기록 남기기」 버튼이 부른다)

- [ ] **Step 1: DOM 자리를 만든다**

`<div id="dodge-share" style="display:none;width:100%;max-width:300px"></div>` **바로 아래**에 넣는다.

```html
    <!-- 계정이 없거나 임시계정일 때만 뜬다. 내용은 _dodgeShowShare 가 채운다.
         ★새 화면을 만들지 않는다 — 닉네임 시트(guestAskNick)와 가입 권유(guestNudge)는 이미 있다. -->
    <div id="dodge-keep" style="display:none;width:100%;max-width:300px"></div>
```

- [ ] **Step 2: `dodgeSaveRecord` 를 만든다**

Task 4 의 `dodgeGuestPromote` 정의 **바로 아래**에 넣는다.

```js
// 게임오버의 「기록 남기기」 — 계정이 없으면 임시계정을 만들고 닉네임을 받는다.
// ★닉네임 시트는 스쿼드가 쓰던 guestAskNick 을 그대로 쓴다. 새 화면을 만들지 않는다.
//   끝나고 스쿼드로 가버리지 않게 _guestAfter 로 돌아올 곳을 정해 둔다(Task 4).
window.dodgeSaveRecord = async function () {
  if (auth.currentUser) { await window.dodgeGuestPromote(); window._dodgeRefreshKeep(); return; }
  try { await signInAnonymously(auth); }
  catch (e) { console.error('익명 로그인 실패', e); showToast('기록을 남기지 못했어요 · 잠시 후 다시'); return; }
  window._guestJustStarted = true;          // 스쿼드 흐름이 초대 시트를 다시 띄우지 않게
  window._guestAfter = function () {
    window.dodgeGuestPromote().then(function () {
      window._dodgeRefreshKeep();
      showToast('기록을 남겼어요');
    });
  };
  window.guestAskNick && window.guestAskNick();
};
// 게임오버 아래쪽 안내를 지금 상태에 맞게 다시 그린다.
window._dodgeRefreshKeep = function () {
  const host = document.getElementById('dodge-keep'); if (!host) return;
  const u = auth.currentUser;
  const btn = 'width:100%;border:none;border-radius:12px;padding:13px;font-size:13.5px;'
    + 'font-weight:800;cursor:pointer;font-family:inherit';
  if (!u) {
    // 계정이 아예 없다 — 필요한 건 가입이 아니라 **먼저 기록 남기기**다(스펙 5장).
    host.style.display = '';
    host.innerHTML = '<button onclick="window.dodgeSaveRecord()" style="' + btn
      + ';background:var(--accent);color:#fff">기록 남기기</button>'
      + '<div style="font-size:11px;color:rgba(255,255,255,.4);margin-top:7px;line-height:1.6">'
      + '닉네임만 정하면 이 점수가 남아요</div>';
    return;
  }
  if (u.isAnonymous) {
    // ★틴트 칩 금지 — 색면 배지를 쓰지 않는다. 글자색과 테두리로만.
    host.style.display = '';
    host.innerHTML = '<div style="background:none;border:1px solid rgba(255,255,255,.14);'
      + 'border-radius:12px;padding:11px 13px;font-size:11.5px;color:rgba(255,255,255,.55);line-height:1.65">'
      + '랭킹에 올리려면 <b style="color:#cfd6e6">가입</b>이 필요해요</div>';
    return;
  }
  host.style.display = 'none';
  host.innerHTML = '';
};
```

- [ ] **Step 3: `_dodgeShowShare` 끝에서 부른다**

`window._dodgeShowShare` 안에서 아래 줄을 찾아 **그 바로 아래**에 넣는다(실측 확인된 자리다):

```js
    window._mwKakaoPrep && window._mwKakaoPrep();   // 카톡용 공개 URL 미리 올려 둔다
```

```js
    // 기록 안내 + 임시계정이면 하루 한 번 가입 권유(제한은 guestNudge 가 알아서 지킨다)
    if (hostId !== 'dodge-rec-share') {          // '내 기록' 목록에서 부른 경우엔 안 띄운다
      window._dodgeRefreshKeep && window._dodgeRefreshKeep();
      if (auth.currentUser && auth.currentUser.isAnonymous && window.guestNudge) {
        setTimeout(function () { window.guestNudge(); }, 1200);
      }
    }
```

- [ ] **Step 4: 문법 검사 + 커밋**

```bash
node tools/dogam-syntax-check.mjs
node tools/tests/dodge-guest.test.mjs
git diff --stat
git add index.html
git commit -m "feat(dodge): 게임오버에 기록 남기기 + 가입 안내"
```

---

### Task 6: 공유 링크 + 인스타 버튼이 링크도 복사

**Files:**
- Modify: `index.html` — `window._dodgeShowShare` 안의 `_mwShareMeta` 와 인스타 버튼
- Modify: `index.html` — Task 5 의 `_dodgeRefreshKeep` 아래에 `dodgeShareIG`
- Test: `tools/tests/dodge-guest.test.mjs`

**Interfaces:**
- Consumes: Task 1 `dodgeMakeLink`
- Produces: `window.dodgeShareIG(score)` (인스타 버튼이 부른다. 닉네임은 `window._mwMyNick` 에서 읽는다)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`console.log` **바로 위**에 붙인다.

```js
// 12) ★카톡 카드가 게임으로 가야 한다 — 지금은 link 가 비어 홈으로 떨어진다
const show = grab(/window\._dodgeShowShare = function[\s\S]*?\n\};/, '_dodgeShowShare');
assert(/link:\s*window\.dodgeMakeLink\(/.test(show),
  '_mwShareMeta 에 도전장 링크가 없다 → 카톡 카드가 홈으로 간다');
// 카드 그림·문구는 손대지 않았는지 (대표 지시)
assert(/title: '덤벨 피하기 ' \+ score \+ '점!'/.test(show), '카톡 제목 문구가 바뀌었다');
assert(/btn: '나도 해보기'/.test(show), '카톡 버튼 문구가 바뀌었다');
assert(/_dodgeCardImg\(/.test(show), '카드 그림 호출이 사라졌다');

// 13) 인스타 버튼은 링크도 같이 복사한다 (버튼 3칸은 그대로)
assert(/onclick="window\.dodgeShareIG\(/.test(show), '인스타 버튼이 링크를 안 복사한다');
assert(/mwShareSheet\(\)/.test(src), 'mwShareSheet 호출이 사라졌다');
const ig = grab(/window\.dodgeShareIG = function[\s\S]*?\n\};/, 'dodgeShareIG');
assert(/clipboard/.test(ig), '클립보드 복사가 없다');
assert(/mwShareSheet\(\)/.test(ig), '공유시트를 안 연다');
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `node tools/tests/dodge-guest.test.mjs`
Expected: FAIL — `_mwShareMeta 에 도전장 링크가 없다`

- [ ] **Step 3: `_mwShareMeta` 에 링크 한 줄을 넣는다**

`_dodgeShowShare` 안의 `_mwShareMeta` 를 이렇게 바꾼다. **title/desc/btn 은 그대로 둔다.**

```js
    // 카톡 카드 문구 — 기록 자랑 + 설치 유도 (대표 8-19)
    window._mwShareMeta = {
      title: '덤벨 피하기 ' + score + '점!',
      desc: '머피월드에서 훈수충 아재를 피해 보세요',
      btn: '나도 해보기',
      // ★이게 없으면 mwShareKakao 가 기본값(홈)으로 떨어진다 — 받은 사람이 게임에 못 닿는다.
      //   머피월드 → 헬스장 필드까지 찾아가야 해서 사실상 아무도 안 온다(대표 8-20).
      link: window.dodgeMakeLink(window._mwMyNick || '', score),
    };
```

- [ ] **Step 4: 인스타 버튼을 바꾼다**

같은 함수 안 `host.innerHTML` 의 인스타 버튼 줄에서 `onclick` 만 바꾼다.
**아이콘·글자·버튼 개수는 그대로다.**

```js
      + '<button class="mw-sbtn" onclick="window.dodgeShareIG(' + score + ')" aria-label="인스타그램에 공유">' + (B.ig || '') + '<span>인스타그램</span></button>'
```

- [ ] **Step 5: `dodgeShareIG` 를 만든다**

Task 5 의 `_dodgeRefreshKeep` 정의 **바로 아래**에 넣는다.

```js
// 인스타는 사진만 올라가고 링크는 안 따라간다 — 유저가 스토리에 직접 붙여야 한다(대표 8-20).
// 그래서 공유시트를 열기 **전에** 링크를 클립보드에 넣어 둔다.
// ★복사는 반드시 **탭 제스처 안에서** 해야 브라우저가 허용한다. 공유시트를 연 뒤엔 막힌다.
// ★네이티브(앱스토어)로 가도 이 버튼은 남는다 — instagram-stories:// 로 스토리를 바로 열 수는
//   있지만 링크 자동 첨부는 메타 승인 파트너만 된다고 알려져 있다.
window.dodgeShareIG = function (score) {
  const url = window.dodgeMakeLink(window._mwMyNick || '', score || 0);
  const go = function () {
    showToast('링크도 복사했어요 · 스토리에 붙여넣으세요');
    window.mwShareSheet && window.mwShareSheet();
  };
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(go, go);
    } else {
      const ta = document.createElement('textarea');
      ta.value = url; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); } catch (e) {}
      document.body.removeChild(ta);
      go();
    }
  } catch (e) { go(); }
};
```

- [ ] **Step 6: 테스트 + 문법 검사 + 커밋**

```bash
node tools/tests/dodge-guest.test.mjs
node tools/dogam-syntax-check.mjs
git diff --stat
git add index.html tools/tests/dodge-guest.test.mjs
git commit -m "feat(dodge): 카톡 카드가 게임으로 가게 + 인스타 버튼이 링크도 복사"
```

---

### Task 7: 링크로 들어오면 바로 게임 (+ 온보딩 미루기)

★이 태스크가 이번 작업의 핵심이다. **비로그인 if/else 사슬을 건드리지 않는다** — 다른 창이 거기서 작업 중이다.

**Files:**
- Modify: `index.html` — `// ===== 덤벨 피하기 끝 =====` (약 12553행) **바로 위**
- Modify: `index.html:2151` 부근 — `#dodge-best` 아래에 도전장 자리
- Test: `tools/tests/dodge-guest.test.mjs`

**Interfaces:**
- Consumes: Task 1 `dodgeParseLink`, 기존 `dodgeOpen`/`dodgeClose`
- Produces: `window._dodgeFromLink` (불리언), `window._dodgeChallenge` (`{nick,score}` 또는 null)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`console.log` **바로 위**에 붙인다.

```js
// 14) ★비로그인 if/else 사슬을 건드리지 않았는가 (다른 창 구역)
const chain = grab(/if \(window\._mwRoomInvite && window\.mwRoomEnterChoice\)[\s\S]*?showSplashOnboarding\(\), 1700\);/, '비로그인 사슬');
assert(!/game/.test(chain), '게임 링크 처리가 비로그인 사슬에 들어갔다 → 다른 창과 충돌한다');

// 15) 온보딩은 사슬을 고치지 말고 **감싸서** 미룬다 (온보딩 z 30000 > 게임 z 2300)
assert(/window\.showSplashOnboarding = function/.test(src),
  'showSplashOnboarding 을 감싸지 않는다 → 온보딩이 게임을 덮는다');

// 16) 도전장 표시는 textContent 로만 (URL 은 남이 고칠 수 있다)
const boot = grab(/window\._dodgeLinkBoot = function[\s\S]*?\n\};/, '_dodgeLinkBoot');
assert(!/innerHTML/.test(boot), '도전장을 innerHTML 로 넣는다 → 주입이 된다');
assert(/textContent/.test(boot), '도전장을 textContent 로 안 넣는다');
// 주소를 지워야 새로고침 때 또 안 튄다
assert(/replaceState/.test(boot), '주소를 안 지운다 → 새로고침마다 게임이 다시 뜬다');
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `node tools/tests/dodge-guest.test.mjs`
Expected: FAIL — `showSplashOnboarding 을 감싸지 않는다`

★**감싸기가 통하는 근거(실측 확인함).** `showSplashOnboarding` 은 블록 4(일반 `<script>`)의
최상위 `function` 선언이라 **전역 프로퍼티**다. 우리 코드는 블록 5(module)에 있지만,
`window.showSplashOnboarding = ...` 로 바꾸면 블록 5의 비로그인 사슬이 부르는 **맨이름
`showSplashOnboarding()` 도 전역 객체를 거쳐 바뀐 함수를 집는다.** `dismissLanding` 도
블록 2 최상위라 전역이다. 둘 다 `window.` 없이 써도 되지만, 바꿔치기는 `window.` 로 해야 한다.

- [ ] **Step 3: 도전장 자리를 만든다**

`<div id="dodge-best" ...></div>` **바로 아래**에 넣는다.

```html
      <!-- 링크로 들어온 사람에게만 보인다. 내용은 _dodgeLinkBoot 가 textContent 로 채운다.
           ★골드(#F5C24B)는 별점·코인 자리라 안 쓴다 — 흰 글자에 그림자로 띄운다. -->
      <div id="dodge-challenge" style="display:none;font-size:13.5px;font-weight:800;color:#fff;text-shadow:0 2px 6px rgba(0,0,0,.85)"></div>
```

- [ ] **Step 4: 링크 부팅을 만든다**

`// ===== 덤벨 피하기 끝 =====` **바로 위**에 넣는다.

```js
// ---- 링크로 들어오면 바로 게임 (미가입자 바이럴) ----
// 스펙: docs/superpowers/specs/2026-08-20-dodge-guest-viral-design.md
// ★**인증을 기다리지 않는다.** 계정이 필요 없으므로 onAuthStateChanged 와 무관하게 즉시 연다.
//   비로그인 if/else 사슬(_mwRoomInvite → _sqInviteSid → 온보딩)은 **한 글자도 안 건드린다** —
//   그 사슬의 첫 가지가 방 초대이고, 다른 창이 거기서 작업 중이다.
window._dodgeFromLink = false;
window._dodgeChallenge = null;
window._dodgeLinkBoot = function () {
  const p = window.dodgeParseLink(location.search);
  if (!p.on) return;
  window._dodgeFromLink = true;
  window._dodgeChallenge = { nick: p.nick, score: p.score };
  // 주소를 지운다 — 새로고침할 때마다 게임이 다시 튀면 안 된다
  try { history.replaceState(null, '', location.pathname); } catch (e) {}
  // ★온보딩(#splash-ob, z 30000)이 게임(z 2300)을 통째로 덮는다. 사슬을 고치는 대신
  //   함수를 감싸 **게임이 떠 있는 동안에는 미뤄 둔다.** 게임을 닫을 때 그때 부른다.
  //   순서가 오히려 낫다 — 재미를 먼저 보여주고 소개한다.
  if (typeof window.showSplashOnboarding === 'function' && !window._dodgeObWrapped) {
    window._dodgeObWrapped = true;
    const orig = window.showSplashOnboarding;
    window.showSplashOnboarding = function () {
      if (document.getElementById('dodge-screen') &&
          document.getElementById('dodge-screen').style.display !== 'none') {
        window._dodgeObPending = true; return;
      }
      return orig.apply(this, arguments);
    };
  }
  if (typeof dismissLanding === 'function') { try { dismissLanding(); } catch (e) {} }
  window.dodgeOpen && window.dodgeOpen();
  // 도전장 한 줄. ★textContent 로만 넣는다 — URL 은 남이 고칠 수 있는 값이다.
  const el = document.getElementById('dodge-challenge');
  if (el && p.score > 0) {
    el.textContent = (p.nick ? p.nick + '님의 ' : '') + p.score + '점에 도전!';
    el.style.display = '';
  }
};
// 로드가 끝난 뒤에 돈다 — showSplashOnboarding·dodgeOpen 이 다 정의된 다음이어야 한다.
if (document.readyState === 'complete') setTimeout(window._dodgeLinkBoot, 0);
else window.addEventListener('load', function () { setTimeout(window._dodgeLinkBoot, 0); });
```

- [ ] **Step 5: 게임을 닫을 때 미뤄둔 온보딩을 부른다**

`window.dodgeClose = function () {` 의 마지막 줄 `window._dodgeS = null;` **바로 아래**에 넣는다.

```js
  // 링크로 들어와 온보딩을 미뤄뒀으면 이제 보여준다 — 게임 → 나가기 → 소개 순서
  if (window._dodgeObPending) {
    window._dodgeObPending = false;
    setTimeout(function () { window.showSplashOnboarding && window.showSplashOnboarding(); }, 300);
  }
```

- [ ] **Step 6: 테스트 + 문법 검사 + 커밋**

```bash
node tools/tests/dodge-guest.test.mjs
node tools/dogam-syntax-check.mjs
git diff --stat
git add index.html tools/tests/dodge-guest.test.mjs
git commit -m "feat(dodge): 링크로 들어오면 로그인 없이 바로 게임 + 온보딩 미루기"
```

---

### Task 8: 배포 + 실앱 검증

**Files:**
- 없음 (검증만). **sw 버전은 안 올린다** — 새 에셋 파일이 없다.

- [ ] **Step 1: 전체 테스트**

```bash
node tools/tests/dodge-guest.test.mjs
node tools/tests/field-aura.test.mjs
node tools/tests/room-items.test.mjs
node tools/tests/box-spot.test.mjs
node tools/tests/dogam-bonus.test.mjs
node tools/tests/field-place.test.mjs
node tools/dogam-syntax-check.mjs
```
Expected: 전부 통과

- [ ] **Step 2: 모듈 블록까지 포함해 문법 재확인**

```bash
python -c "
import re,subprocess,os,tempfile
s=open('index.html',encoding='utf-8').read()
b=re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', s, re.S)
print('blocks:',len(b))
for i,x in enumerate(b):
    p=os.path.join(tempfile.gettempdir(),'chk%d.js'%i); open(p,'w',encoding='utf-8').write(x)
    r=subprocess.run(['node','--check',p],capture_output=True,text=True)
    print(' ',i,'OK' if r.returncode==0 else 'FAIL')
    if r.returncode: print(r.stderr[:500])
"
```
Expected: 전부 `OK`

- [ ] **Step 3: 푸시**

```bash
git status --short
git diff --stat
git log --oneline -8 | cat
git push origin main
```

- [ ] **Step 4: 배포 반영 확인**

```bash
until curl -s "https://murpy.app/index.html?cb=$(date +%s%N)" | grep -q "_dodgeLinkBoot"; do sleep 5; done; echo "배포 반영"
```

- [ ] **Step 5: 대표 실앱 확인 요청**

**로그아웃 상태** 또는 시크릿 창에서 확인한다.

1. `murpy.app/?game=dodge&n=패수현&s=320` → **로그인 없이 바로 게임**, 시작화면에 `패수현님의 320점에 도전!`
2. 그 상태로 5초 이상 둬도 **온보딩이 안 덮는다**. 게임에서 **나가기** 를 누르면 그때 온보딩이 뜬다
3. 한 판 하고 게임오버 → **「기록 남기기」** → 닉네임 → `기록을 남겼어요`
4. 다시 게임오버 화면에 `랭킹에 올리려면 가입이 필요해요` 가 뜬다
5. 그 뒤 정식 가입(구글/카카오) → **점수가 따라온다**
6. 회원 계정으로 카톡 공유 → 받은 사람이 **「나도 해보기」** → **게임으로 간다**(지금은 홈으로 감)
7. 인스타 버튼 → 공유시트가 뜨고 **링크가 이미 복사돼 있다**(메모장에 붙여넣어 확인)
8. 임시계정은 명예의 전당 **게임 탭에 안 뜬다**
9. 주소를 손으로 고쳐도 안 깨진다: `?game=dodge&s=999999` / `?game=dodge&n=<b>x</b>`
10. **방 초대 링크(`?room=`)와 스쿼드 초대(`?sq=`)가 그대로 동작한다** — 게임이 가로채지 않는다

- [ ] **Step 6: 메모리 갱신**

`project_murpy_growth_framework.md` 에 바이럴 고리(링크 → 게임 → 기록 → 공유)를 적고,
실앱에서 튜닝한 값이 있으면 같이 남긴다.
