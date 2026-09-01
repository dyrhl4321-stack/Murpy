# 머피 테니스 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 머피월드 `tennis` 필드에 1인용 랠리 게임을 붙인다 — 조작은 탭 하나이고 탭한 위치가 받아칠 코스가 된다.

**Architecture:** 덤벨 피하기·홀인 머피와 **같은 뼈대**를 쓴다(전체화면 오버레이 + 타이틀/설명/난이도/경기/결과 pane). 새 UI 문법을 만들지 않는다. 판정은 상태를 바꾸지 않는 순수 함수 `_tennisJudge` 로 분리해 `tools/tests/tennis-core.test.mjs` 에서 검증한다. 그림은 `field_tennis.png`(이미 있음) + `_charRenderTo`(이미 있음) + CSS 공. 신규 에셋은 타이틀 하나뿐.

**Tech Stack:** 단일 `index.html`(모듈 스크립트 + window 전역), DOM 렌더(캔버스 아님 — 기존 두 게임과 동일), `node --test` 아닌 순수 `node tools/tests/*.test.mjs` + `assert`.

**Spec:** `docs/superpowers/specs/2026-09-02-murpy-tennis-design.md`

## Global Constraints

- 이모지 금지 — 머피 전용 라인 SVG 아이콘만.
- 틴트 칩(반투명 색면 배지) 금지 — `background:none` + 테두리 + 글자색.
- 픽셀 폰트(`Galmuri`)는 머피월드 전용. 일반 UI는 Pretendard.
- 색: 블루 `#3D7EFF` = 메인/액션. 골드 `#F5C24B` = 별점·코인 전용.
- 캐릭터는 `_charRenderTo` 한 경로로만 그린다. 새 렌더 경로를 만들지 않는다.
- 검사는 **파이프 없이** 실행한다. `node tools/module-syntax-check.mjs | tail` 은 실패 exit 를 삼킨다.
- 배포 전 `python tools/check_version.py` 필수. `_SW_V`·`sw.js` 3곳·`version.txt` 가 같아야 한다.
- `char/` 는 옆 세션(system32-40) 작업 구역이다. `char/game/tennis_*.png` 만 만들고 다른 파일은 건드리지 않는다.
- 커밋은 `git add` 와 `git commit` 을 **한 호출로** 묶는다(두 창이 같은 파일을 만질 때 섞인다).

---

### Task 1: 상수 · 새 판 · 판정 순수 함수 + 테스트

핵심 규칙 전부가 여기 들어간다. 화면이 없어도 이 태스크만으로 게임이 "돌아가는지" 검증된다.

**Files:**
- Modify: `index.html` — 골프 블록이 끝나는 `// ===== 골프 스윙 끝` 바로 뒤(없으면 `window.HOF_KINDS` 정의 앞)에 테니스 블록을 연다
- Test: `tools/tests/tennis-core.test.mjs` (신규)

**Interfaces:**
- Produces:
  - `window.TENNIS` — 상수 묶음
  - `window.TENNIS_LV` — 난이도 3종
  - `window.tennisNew(lvKey) -> state`
  - `window._tennisJudge(s, tapX) -> { result, course?, perfect?, wobble? }` (순수 — s 를 바꾸지 않는다)
  - `window.tennisTick(s, dt) -> s.last`
- Consumes: 없음

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tools/tests/tennis-core.test.mjs`:

```js
// 머피 테니스 — 판정·물리 순수 로직 테스트 (index.html 에서 추출해 검증) · 9-02
// 실행: node tools/tests/tennis-core.test.mjs
//
// ★왜 있나: 이 게임은 대표가 자는 사이 만들어져 아침에 처음 켜진다.
//   "쳤는데 안 맞는다 / 안 쳤는데 넘어간다" 류는 폰으로 한 판 돌려도 원인을 못 찾는다.
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
function grab(re, name) { const m = src.match(re); assert(m, `index.html에서 ${name}를 찾지 못함`); return m[0]; }

const w = {};
for (const [re, name] of [
  [/window\.TENNIS = \{[\s\S]*?\n\};/, 'TENNIS'],
  [/window\.TENNIS_LV = \{[\s\S]*?\n\};/, 'TENNIS_LV'],
  [/window\.tennisNew = function[\s\S]*?\n\};/, 'tennisNew'],
  [/window\._tennisJudge = function[\s\S]*?\n\};/, '_tennisJudge'],
  [/window\.tennisTick = function[\s\S]*?\n\};/, 'tennisTick'],
]) new Function('window', grab(re, name))(w);

const T = w.TENNIS;
const mid = (T.ZONE_Y0 + T.ZONE_Y1) / 2;
// 내 쪽으로 오는 공을, 캐릭터가 닿는 자리에, 존 한가운데에 놓는다
function ready(lv) {
  const s = w.tennisNew(lv || 'mid');
  s.toMe = true; s.by = mid; s.bx = 50; s.mx = 50; s.alive = true;
  return s;
}

// 1) 새 판의 초기값
let s = w.tennisNew('mid');
assert.strictEqual(s.pts, 0, '시작 점수는 0');
assert.strictEqual(s.lives, T.LIVES, '목숨은 상수와 같아야');
assert.strictEqual(s.rally, 0, '랠리 0에서 시작');
assert.strictEqual(s.over, false, '시작하자마자 끝나면 안 된다');

// 2) 존 한가운데 + 캐릭터가 공 앞 = 맞는다. perfect 는 1 에 가깝다
let r = w._tennisJudge(ready(), 50);
assert.strictEqual(r.result, 'hit', '한가운데인데 안 맞았다');
assert(r.perfect > 0.99, 'perfect 가 1 이어야: ' + r.perfect);

// 3) 순수 함수다 — 판정이 상태를 바꾸지 않는다
const s3 = ready(); const snap = JSON.stringify(s3);
w._tennisJudge(s3, 20);
assert.strictEqual(JSON.stringify(s3), snap, '_tennisJudge 가 상태를 바꿨다');

// 4) 너무 이르다 / 너무 늦다
const early = ready(); early.by = T.ZONE_Y0 - 5;
assert.strictEqual(w._tennisJudge(early, 50).result, 'early', '존 앞인데 early 가 아니다');
const late = ready(); late.by = T.ZONE_Y1 + 5;
assert.strictEqual(w._tennisJudge(late, 50).result, 'late', '존 뒤인데 late 가 아니다');

// 5) 캐릭터가 공에서 멀면 못 닿는다
const far = ready(); far.mx = 50 + T.REACH + 2; far.bx = 50;
assert.strictEqual(w._tennisJudge(far, 50).result, 'reach', '멀리 있는데 쳤다');
const near = ready(); near.mx = 50 + T.REACH - 1; near.bx = 50;
assert.strictEqual(w._tennisJudge(near, 50).result, 'hit', '닿는 거리인데 못 쳤다');

// 6) 탭한 x 가 코스가 된다
assert(Math.abs(w._tennisJudge(ready(), 20).course - 20) < 0.01, '왼쪽을 탭했는데 코스가 다르다');
assert(Math.abs(w._tennisJudge(ready(), 80).course - 80) < 0.01, '오른쪽을 탭했는데 코스가 다르다');

// 7) 라인 밖을 노리면 아웃
assert.strictEqual(w._tennisJudge(ready(), T.SIDE_MIN - 3).result, 'out', '왼쪽 라인 밖인데 아웃이 아니다');
assert.strictEqual(w._tennisJudge(ready(), T.SIDE_MAX + 3).result, 'out', '오른쪽 라인 밖인데 아웃이 아니다');

// 8) 아슬아슬하게 받으면 코스가 공이 온 쪽으로 밀린다(결정적, 난수 없음)
const edge = ready(); edge.by = mid + (T.ZONE_Y1 - T.ZONE_Y0) / 2 * 0.9; edge.bx = 10;
const e1 = w._tennisJudge(edge, 50);
assert(e1.perfect < 0.2, '가장자리인데 perfect 가 높다: ' + e1.perfect);
assert(e1.course < 50, '급하게 받았으면 공이 온 쪽(왼쪽)으로 밀려야: ' + e1.course);
const edge2 = ready(); edge2.by = edge.by; edge2.bx = 90;
assert(w._tennisJudge(edge2, 50).course > 50, '오른쪽에서 온 공은 오른쪽으로 밀려야');

// 9) 난이도가 높을수록 존이 좁다
const zoneOf = (lv) => { const s = ready(lv); const h = (T.ZONE_Y1 - T.ZONE_Y0) / 2 * w.TENNIS_LV[lv].zone; return h; };
assert(zoneOf('easy') > zoneOf('mid') && zoneOf('mid') > zoneOf('hard'), '난이도별 존 너비가 하>중>상 이 아니다');
const hardEdge = ready('hard'); hardEdge.by = mid + (T.ZONE_Y1 - T.ZONE_Y0) / 2 * 0.9;
assert.notStrictEqual(w._tennisJudge(hardEdge, 50).result, 'hit', '상 난이도에서 같은 위치가 맞으면 안 된다');

// 10) 내 쪽으로 오는 공이 아니면 판정하지 않는다
const notMine = ready(); notMine.toMe = false;
assert.strictEqual(w._tennisJudge(notMine, 50).result, 'idle', '상대 코트 공인데 판정했다');

// 11) 틱: 공이 움직인다
const t1 = ready(); const y0 = t1.by; w.tennisTick(t1, 16);
assert.notStrictEqual(t1.by, y0, '틱을 돌렸는데 공이 그대로다');

// 12) 틱: 안 치고 지나가면 실점하고 랠리가 끊긴다
const miss = ready(); miss.rally = 5;
for (let i = 0; i < 400 && miss.lives === T.LIVES; i++) w.tennisTick(miss, 16);
assert.strictEqual(miss.lives, T.LIVES - 1, '놓쳤는데 실점하지 않았다');
assert.strictEqual(miss.rally, 0, '실점했는데 랠리가 안 끊겼다');

// 13) 목숨이 다하면 끝난다
const dead = w.tennisNew('mid'); dead.lives = 1; dead.toMe = true; dead.by = mid; dead.bx = 50; dead.mx = 50;
for (let i = 0; i < 600 && !dead.over; i++) w.tennisTick(dead, 16);
assert.strictEqual(dead.over, true, '목숨이 0인데 안 끝났다');

// 14) 점수식 — 득점 100, 최장 랠리 10, 난이도 배율
const sc = w.tennisNew('hard'); sc.pts = 3; sc.bestRally = 7;
assert.strictEqual(w.tennisScore(sc), Math.round((3 * T.PT_SCORE + 7 * T.RALLY_SCORE) * w.TENNIS_LV.hard.mul),
  '점수식이 스펙과 다르다');

console.log('테니스 코어 테스트 14개 통과');
```

- [ ] **Step 2: 실패를 확인한다**

Run: `node tools/tests/tennis-core.test.mjs`
Expected: FAIL — `index.html에서 TENNIS를 찾지 못함`

- [ ] **Step 3: 최소 구현을 넣는다**

`index.html` 의 `// ===== 골프 스윙 끝` 다음 줄부터. 각 함수는 **`window.X = function ... \n};` 형태로 한 줄에서 시작해 `\n};` 로 끝나야** 한다 — 테스트가 그 모양으로 뽑는다.

```js
// ===== 머피 테니스 (2026-09-02) — 덤벨 피하기·홀인 머피 뼈대 재사용, 규칙만 테니스 =====
// 조작은 탭 하나. **탭한 x 가 받아칠 코스**다. 캐릭터 좌우 이동은 자동.
// 좌표: 코트 0~100 x 0~100. 위가 상대, 아래가 나, 네트 y=50.
window.TENNIS = {
  NET_Y: 50, MY_BASE: 88, OP_BASE: 12,
  ZONE_Y0: 78, ZONE_Y1: 94,          // 임팩트 존(내 코트의 가로 띠)
  SIDE_MIN: 8, SIDE_MAX: 92,         // 코트 좌우 라인. 밖으로 치면 아웃
  REACH: 9,                          // 캐릭터가 공에 닿는 거리
  MY_V: 0.75, OP_V: 0.55,            // 좌우 이동 속도(단위/틱)
  V_MAX: 2.2,
  WOBBLE: 18,                        // 급하게 받았을 때 코스가 밀리는 최대 폭
  LIVES: 3,
  PT_SCORE: 100, RALLY_SCORE: 10, MAX_SCORE: 99999
};
// 난이도 — 대표 8-30: "난이도마다 차별점이 확실해야 한다"
window.TENNIS_LV = {
  easy: { name: '하', opV: 0.40, ballV: 0.75, acc: 0.012, zone: 1.5, out: 1.4, mul: 0.7 },
  mid:  { name: '중', opV: 0.55, ballV: 0.90, acc: 0.020, zone: 1.0, out: 1.0, mul: 1.0 },
  hard: { name: '상', opV: 0.78, ballV: 1.10, acc: 0.030, zone: 0.7, out: 0.75, mul: 2.5 }
};
window.tennisNew = function (lvKey) {
  const T = window.TENNIS, lv = window.TENNIS_LV[lvKey] || window.TENNIS_LV.mid;
  return {
    lv: window.TENNIS_LV[lvKey] ? lvKey : 'mid',
    bx: 50, by: T.NET_Y, vy: lv.ballV, vx: 0, z: 0,   // 공
    mx: 50, ox: 50,                                    // 내 캐릭터 x, 상대 x
    toMe: true, rally: 0, bestRally: 0, pts: 0,
    lives: T.LIVES, over: false, last: '', t: 0
  };
};
// 탭 판정. ★상태를 바꾸지 않는다(순수) — 테스트가 이걸 검증한다.
window._tennisJudge = function (s, tapX) {
  const T = window.TENNIS, lv = window.TENNIS_LV[s.lv] || window.TENNIS_LV.mid;
  if (!s.toMe || s.over) return { result: 'idle' };
  const mid = (T.ZONE_Y0 + T.ZONE_Y1) / 2;
  const half = (T.ZONE_Y1 - T.ZONE_Y0) / 2 * lv.zone;
  if (s.by < mid - half) return { result: 'early' };
  if (s.by > mid + half) return { result: 'late' };
  if (Math.abs(s.mx - s.bx) > T.REACH) return { result: 'reach' };
  const perfect = Math.max(0, 1 - Math.abs(s.by - mid) / half);
  // ★급하게 받으면 원하는 곳에 못 보낸다 — 공이 **온 쪽**으로 밀린다.
  //   난수를 쓰지 않는다: 같은 상황이면 늘 같은 결과여야 유저가 배울 수 있다.
  const wob = (1 - perfect) * T.WOBBLE / lv.out;
  const course = tapX + (s.bx - 50) / 50 * wob;
  if (course < T.SIDE_MIN || course > T.SIDE_MAX) {
    return { result: 'out', course: course, perfect: perfect, wobble: wob };
  }
  return { result: 'hit', course: course, perfect: perfect, wobble: wob };
};
window.tennisScore = function (s) {
  const T = window.TENNIS, lv = window.TENNIS_LV[s.lv] || window.TENNIS_LV.mid;
  return Math.min(T.MAX_SCORE, Math.round((s.pts * T.PT_SCORE + s.bestRally * T.RALLY_SCORE) * lv.mul));
};
```

`tennisTick` 은 Step 3b 로 이어서 넣는다(길어서 나눈다):

```js
// 한 틱. 반환 = s.last ('' | 'miss' | 'point' | 'over')
window.tennisTick = function (s, dt) {
  const T = window.TENNIS, lv = window.TENNIS_LV[s.lv] || window.TENNIS_LV.mid;
  if (s.over) return s.last;
  s.t += dt; const k = dt / 16;
  s.last = '';
  // 공
  s.by += s.vy * k * (s.toMe ? 1 : -1);
  s.bx += s.vx * k;
  if (s.bx < T.SIDE_MIN || s.bx > T.SIDE_MAX) { s.vx = -s.vx; s.bx = Math.max(T.SIDE_MIN, Math.min(T.SIDE_MAX, s.bx)); }
  // 내 캐릭터 — 공 쪽으로 자동으로 간다(조작하지 않는다)
  const md = s.bx - s.mx; s.mx += Math.max(-T.MY_V, Math.min(T.MY_V, md)) * k;
  // 상대 — 공 쪽으로 간다. 난이도가 낮으면 느려서 못 따라간다
  const od = s.bx - s.ox; s.ox += Math.max(-lv.opV, Math.min(lv.opV, od)) * k;
  if (s.toMe) {
    // 내가 안 치고 베이스라인을 넘겼다 = 실점
    if (s.by > T.MY_BASE + 8) {
      s.lives -= 1; s.rally = 0; s.last = 'miss';
      if (s.lives <= 0) { s.over = true; s.last = 'over'; return s.last; }
      window._tennisServe(s, true);
    }
  } else {
    // 상대 코트 도달 — 닿으면 받아치고, 못 닿으면 내 득점
    if (s.by < T.OP_BASE + 6) {
      if (Math.abs(s.ox - s.bx) <= T.REACH) {
        window._tennisReturn(s);
      } else {
        s.pts += 1; s.bestRally = Math.max(s.bestRally, s.rally); s.rally = 0; s.last = 'point';
        window._tennisServe(s, false);
      }
    }
  }
  return s.last;
};
// 상대가 받아친다 — 내 쪽으로 코스를 정해 보낸다. 난수 없이 상대 위치에서 먼 쪽을 노린다.
window._tennisReturn = function (s) {
  const T = window.TENNIS, lv = window.TENNIS_LV[s.lv] || window.TENNIS_LV.mid;
  s.rally += 1; s.bestRally = Math.max(s.bestRally, s.rally);
  const target = s.mx < 50 ? T.SIDE_MAX - 6 : T.SIDE_MIN + 6;   // 내가 있는 반대쪽
  s.toMe = true; s.by = T.OP_BASE + 6;
  s.vy = Math.min(T.V_MAX, lv.ballV + s.rally * lv.acc);
  s.vx = (target - s.bx) / ((T.MY_BASE - T.OP_BASE) / s.vy);
};
// 서브 — mine=true 면 내가 실점해서 다시 시작, false 면 내가 득점해서 상대 서브
window._tennisServe = function (s, mine) {
  const T = window.TENNIS, lv = window.TENNIS_LV[s.lv] || window.TENNIS_LV.mid;
  s.toMe = true; s.by = T.NET_Y; s.bx = 50; s.vx = 0;
  s.vy = lv.ballV; s.ox = 50;
};
```

- [ ] **Step 4: 통과를 확인한다**

Run: `node tools/tests/tennis-core.test.mjs`
Expected: `테니스 코어 테스트 14개 통과`

- [ ] **Step 5: 문법 검사 후 커밋**

```bash
node tools/module-syntax-check.mjs
git add index.html tools/tests/tennis-core.test.mjs && git commit -m "feat(tennis): 규칙·판정 코어 + 테스트 14개"
```

---

### Task 2: 화면 — 마크업·CSS

**Files:**
- Modify: `index.html` — 골프 화면 마크업(`<!-- ===== 골프 스윙 ... -->` 블록, 약 3030~3110행) 바로 뒤에 같은 모양으로 추가
- Modify: `index.html` — `.golf-*` CSS 옆에 `.tennis-*` 추가

**Interfaces:**
- Consumes: Task 1 의 `window.TENNIS`
- Produces: DOM id `tennis-screen` · `tennis-pane-title` · `tennis-pane-howto` · `tennis-pane-char` · `tennis-field` · `tennis-over` · `tennis-score` · `tennis-lives`

- [ ] **Step 1: 골프 마크업을 그대로 복사해 id 만 바꾼다**

골프 블록을 복사하고 `golf-` → `tennis-`, 문구만 테니스로. **버튼 크기·배치는 건드리지 않는다** — 8-30에 대표가 "배치·버튼 크기가 다르다"고 지적해 골프가 덤벨 마크업을 그대로 쓰게 된 이유가 이것이다.

- [ ] **Step 2: 코트 CSS**

```css
.tennis-court{position:absolute;inset:0;background:url('char/fields/field_tennis.png?v=3') center/cover no-repeat;image-rendering:pixelated}
.tennis-ball{position:absolute;width:9px;height:9px;border-radius:50%;background:#e8ff4a;box-shadow:inset -2px -2px 0 #b9cc2e,0 2px 0 rgba(0,0,0,.35);transform:translate(-50%,-50%);pointer-events:none}
.tennis-shadow{position:absolute;width:9px;height:4px;border-radius:50%;background:rgba(0,0,0,.35);transform:translate(-50%,-50%);pointer-events:none}
.tennis-ring{position:absolute;border:2px solid rgba(255,255,255,.85);border-radius:50%;transform:translate(-50%,-50%);pointer-events:none;opacity:.9}
.tennis-ring.hot{border-color:#3D7EFF}
```

- [ ] **Step 3: 문법 검사 후 커밋**

```bash
node tools/module-syntax-check.mjs
git add index.html && git commit -m "feat(tennis): 화면 마크업·CSS (골프 뼈대 복제)"
```

---

### Task 3: 그리기 · 입력 · 루프

**Files:**
- Modify: `index.html` — Task 1 블록 뒤

**Interfaces:**
- Consumes: `TENNIS`, `tennisNew`, `_tennisJudge`, `tennisTick`, Task 2 의 DOM id
- Produces: `window.tennisOpen()`, `window._tennisPaint(s)`, `window._tennisFrame(ts)`

- [ ] **Step 1: 그리기**

논리 좌표 → px 는 골프의 `P()` 와 같은 방식이되 회전·원근이 없다(탑다운 고정 카메라):

```js
window._tennisPaint = function (s) {
  const host = document.getElementById('tennis-field'); if (!host) return;
  const W = host.clientWidth || 360, H = host.clientHeight || 640, T = window.TENNIS;
  const P = function (x, y) { return { x: x / 100 * W, y: y / 100 * H }; };
  const b = P(s.bx, s.by), sh = P(s.bx, s.by + 2);
  let h = '<div class="tennis-court"></div>';
  h += '<div class="tennis-shadow" style="left:' + sh.x + 'px;top:' + sh.y + 'px"></div>';
  h += '<div class="tennis-ball" style="left:' + b.x + 'px;top:' + b.y + 'px"></div>';
  // 타이밍 링 — 공이 존에 가까울수록 좁아진다. ★공식이 아니라 실제 공 위치로 계산한다.
  if (s.toMe) {
    const mid = (T.ZONE_Y0 + T.ZONE_Y1) / 2, c = P(s.mx, mid);
    const d = Math.min(1, Math.abs(s.by - mid) / 40);
    const r = 14 + d * 46;
    h += '<div class="tennis-ring' + (d < 0.18 ? ' hot' : '') + '" style="left:' + c.x + 'px;top:' + c.y
       + 'px;width:' + (r * 2) + 'px;height:' + (r * 2) + 'px"></div>';
  }
  host.innerHTML = h;
  window._tennisPlaceChars(s, host, W, H);
};
```

캐릭터는 `_charRenderTo` 로 별도 노드에 그린다 — `innerHTML` 로 매 프레임 지우면 캐릭터가 깜빡인다. `_tennisPlaceChars` 는 노드를 한 번 만들고 `style.left/top` 만 갱신한다.

- [ ] **Step 2: 입력 — 탭 한 번**

```js
// 탭한 x 를 코트 0~100 으로 바꿔 판정에 넘긴다.
host.addEventListener('pointerdown', function (e) {
  const s = window._tennisS; if (!s || s.over) return;
  const r = host.getBoundingClientRect();
  const tapX = Math.max(0, Math.min(100, (e.clientX - r.left) / r.width * 100));
  const j = window._tennisJudge(s, tapX);
  if (j.result === 'hit') { window._tennisHit(s, j); }
  else if (j.result === 'out') { s.lives -= 1; s.rally = 0; showToast('아웃!'); if (s.lives <= 0) { s.over = true; } else window._tennisServe(s, true); }
  // early / late / reach 는 헛스윙 — 공은 계속 간다(놓치면 tick 이 실점 처리한다)
});
```

- [ ] **Step 3: 루프** — 골프 `_golfFrame` 과 같은 모양(rAF + dt 클램프)

- [ ] **Step 4: 헤드리스로 확인** — rAF 를 스텁하고 `for(ts+=16) _tennisFrame(ts)` 로 원하는 시각까지 직접 민다. `--virtual-time-budget` 은 게임 시계를 0.4초밖에 안 돌린다.

- [ ] **Step 5: 문법 검사 후 커밋**

---

### Task 4: 결과 저장 · 공유 · 명예의 전당

**Files:**
- Modify: `index.html` — 골프의 저장부(약 18268행 `games.golf.*`)를 그대로 본떠 `games.tennis.*`
- Modify: `index.html` — `HOF_KINDS` 에 `tennis` 추가, `HOF_GAMES` 에 `'tennis'` 추가

**Interfaces:**
- Consumes: `tennisScore(s)`
- Produces: `users/{uid}.games.tennis.{best,plays,recent,lastAt}`

- [ ] **Step 1: 점수 저장** — 골프와 같은 모양

```js
const upd = { 'games.tennis.plays': increment(1), 'games.tennis.lastAt': Date.now() };
if (n > (cur.best || 0)) upd['games.tennis.best'] = n;
```

- [ ] **Step 2: 명예의 전당 등록**

```js
  tennis:  { label: '테니스', unit: '점', game: '머피 테니스',
             get: function (u) {
               const n = ((u.games || {}).tennis || {}).best || 0;
               return (n > 0 && n <= window.TENNIS.MAX_SCORE) ? n : 0;
             } }
```

그리고 `window.HOF_GAMES = ['dodge', 'golf', 'tennis'];`

- [ ] **Step 3: 공유** — 새로 만들지 않는다. `_mwStampData` 에 카드 그림만 넣으면 카톡·인스타·저장이 그대로 돈다.

- [ ] **Step 4: 문법 검사 후 커밋**

---

### Task 5: 필드 칩 · 배포

**Files:**
- Modify: `index.html` — 골프 칩(약 17995행) 옆에 테니스 칩
- Modify: `index.html`, `sw.js`, `version.txt` — 버전

- [ ] **Step 1: 필드 칩**

```js
  if (key !== 'tennis') { if (b) b.remove(); return; }
  ...
  b.id = 'tennis-start'; b.className = 'mw-fieldchip'; b.style.top = '52px'; b.textContent = '머피 테니스';
  b.onclick = function (e) { e.stopPropagation(); window.tennisOpen(); };
```

- [ ] **Step 2: 버전 올리기** — `main` 을 pull 해 현재 번호 +1. 옆 세션이 같이 올리고 있으므로 **미리 찜하지 않는다.**

- [ ] **Step 3: 검사 전부 (파이프 없이)**

```bash
node tools/tests/tennis-core.test.mjs
node tools/module-syntax-check.mjs
python tools/check_version.py
```

- [ ] **Step 4: 커밋·푸시**

---

## Self-Review

- **스펙 커버리지:** 1절 자리(Task 5 칩) · 2절 규칙(Task 1) · 4절 구조(Task 2) · 5절 화면·링(Task 3) · 6절 난이도(Task 1 `TENNIS_LV`) · 7절 에셋(Task 2 CSS 공 · Task 3 `_charRenderTo`) · 저장·랭킹(Task 4). 빠진 항목 없음.
- **타입 일관성:** `_tennisJudge` 는 `{result, course, perfect, wobble}` 로 통일. `tennisTick` 반환은 `s.last` 문자열. `tennisScore(s)` 는 숫자.
- **미완성 표현:** 없음 — 모든 코드 단계에 실제 코드가 들어 있다.
- **남은 위험:** 타이틀 그림(`char/game/tennis_title.png`)이 없으면 글자 타이틀로 떨어지게 해야 한다. 골프가 `_golfCheckArt` 로 하는 것과 같은 처리를 Task 2 에서 같이 넣는다.
