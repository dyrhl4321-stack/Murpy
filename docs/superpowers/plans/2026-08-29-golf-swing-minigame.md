# 골프 스윙 미니게임 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 골프 필드에서 "당겼다 놓기"로 3홀을 도는 미니게임을, 덤벨 피하기와 같은 화면 뼈대(꽉 찬 화면·시작화면·기록·공유·게스트 링크·명예의 전당)로 만든다.

**Architecture:** 단일 파일 `index.html`. 순수 게임 로직(`GOLF`·`golfNew/golfShot/golfTick`)은 DOM 없이 `window.*` 로 정의해 기존 테스트 방식(정규식으로 index.html 에서 뽑아 `new Function` 으로 실행)으로 검증한다. 화면·입력·저장·공유는 dodge 함수들을 접두사만 `golf` 로 바꿔 복제한다.

**Tech Stack:** Vanilla JS(classic script 블록), CSS, Firestore(`users.games.golf`), localStorage, Leaflet 무관. 테스트 = `node tools/tests/golf-core.test.mjs`.

**Spec:** `docs/superpowers/specs/2026-08-29-golf-swing-minigame-design.md`

## Global Constraints
- 이모지 금지(머피 라인 SVG·글자만). 틴트 칩 금지(켜진 버튼만 `var(--accent)` 채움, 나머지 `background:none`+테두리).
- 픽셀 폰트(Galmuri) 는 머피월드 안이므로 허용. 색: 액션 블루 `#3D7EFF`, 골드 `#F5C24B`.
- 캐릭터는 `mwMiniCharHtml(cfg, h, face)` 로만 그린다. 새 렌더 경로 금지.
- index.html 을 고친 뒤 **반드시** `node tools/module-syntax-check.mjs` + `node tools/dogam-syntax-check.mjs`. 배포는 `node tools/bump-version.mjs <N>` → `python tools/check_version.py` → add·commit·push 한 호출.
- 게임 특성은 게임 안에서만(매칭·피드 노출 무관). 점수 상한 `MAX_SCORE 999`.
- 에셋이 없어도 게임이 돌아야 한다(CSS 폴백).

---

### Task 1: 순수 게임 코어 (상수·홀·선수·물리·점수) + 테스트

**Files:**
- Modify: `index.html` — dodge JS 블록 끝, `window.HOF_KINDS = {` 바로 **앞**에 골프 JS 블록 시작(`// ===== 골프 스윙 =====`)
- Test: `tools/tests/golf-core.test.mjs`

**Interfaces:**
- Produces: `window.GOLF`(상수), `window.GOLF_LV`, `window.GOLF_HOLES`, `window.GOLF_CHARS`, `window.golfNew(seed, lvKey, chKey)`, `window.golfShot(s, dx, dy)`, `window.golfTick(s, dt)`, `window.golfHoleScore(par, strokes)`, `window.golfTotal(s)`. 상태 `s` 모양은 아래 코드의 `golfNew` 반환값.

- [ ] **Step 1: 테스트 파일 작성**

```js
// 골프 스윙 — 순수 로직 테스트 (index.html 에서 추출해 검증)
// 실행: node tools/tests/golf-core.test.mjs
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';
const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
function grab(re, name) { const m = src.match(re); assert(m, `index.html에서 ${name}를 찾지 못함`); return m[0]; }
const w = {};
new Function('window', grab(/window\.GOLF = \{[\s\S]*?\n\};/, 'GOLF'))(w);
new Function('window', grab(/window\.GOLF_LV = \{[\s\S]*?\n\};/, 'GOLF_LV'))(w);
new Function('window', grab(/window\.GOLF_HOLES = \[[\s\S]*?\n\];/, 'GOLF_HOLES'))(w);
new Function('window', grab(/window\.GOLF_CHARS = \{[\s\S]*?\n\};/, 'GOLF_CHARS'))(w);
new Function('window', grab(/window\._golfRnd = function[\s\S]*?\n\};/, '_golfRnd'))(w);
new Function('window', grab(/window\.golfHoleScore = function[\s\S]*?\n\};/, 'golfHoleScore'))(w);
new Function('window', grab(/window\.golfNew = function[\s\S]*?\n\};/, 'golfNew'))(w);
new Function('window', grab(/window\.golfShot = function[\s\S]*?\n\};/, 'golfShot'))(w);
new Function('window', grab(/window\.golfTick = function[\s\S]*?\n\};/, 'golfTick'))(w);
new Function('window', grab(/window\.golfTotal = function[\s\S]*?\n\};/, 'golfTotal'))(w);

const run = (s, ms) => { for (let t = 0; t < ms; t += 16) w.golfTick(s, 16); return s; };

// 1) 점수표
assert.strictEqual(w.golfHoleScore(3, 1), 50); assert.strictEqual(w.golfHoleScore(3, 3), 30);
assert.strictEqual(w.golfHoleScore(3, 6), 0);  assert.strictEqual(w.golfHoleScore(3, 9), 0);

// 2) 샷: 아래로 당기면 위로 간다, 세기는 DRAG_MAX 에서 상한
let s = w.golfNew(7, 'mid', 'human');
assert.strictEqual(s.hole, 0); assert.strictEqual(s.x, 50); assert.strictEqual(s.y, w.GOLF.TEE_Y);
w.golfShot(s, 0, 20);                       // 손가락을 아래(+y)로 20 당김
assert(s.vy < 0 && Math.abs(s.vx) < 1e-9, '위로 굴러야 한다');
assert.strictEqual(s.strokes[0], 1);
const v1 = Math.hypot(s.vx, s.vy);
let s2 = w.golfNew(7, 'mid', 'human'); w.golfShot(s2, 0, 999);
assert(Math.abs(Math.hypot(s2.vx, s2.vy) - w.GOLF.V_MAX) < 1e-9, '세기 상한');
assert(v1 < w.GOLF.V_MAX);

// 3) 마찰로 멈춘다 · 굴러가는 동안 샷 무시
s = w.golfNew(7, 'easy', 'human'); w.golfShot(s, 0, 12);
assert.strictEqual(w.golfShot(s, 0, 12), false, '굴러가는 중엔 샷 불가');
run(s, 6000); assert(s.moving === false, '6초면 멈춰야 한다'); assert(s.y < w.GOLF.TEE_Y);

// 4) 파워 특성: 헬토리가 더 멀리 간다
const a = w.golfNew(3, 'easy', 'human'), b = w.golfNew(3, 'easy', 'heltori');
w.golfShot(a, 0, 20); w.golfShot(b, 0, 20); run(a, 8000); run(b, 8000);
assert(b.y < a.y, '헬토리(파워 1.25)가 더 멀리');

// 5) 바람: 뚱뚱이는 덜 밀린다 (상 난이도, 같은 시드 → 같은 바람)
const c = w.golfNew(11, 'hard', 'human'), d = w.golfNew(11, 'hard', 'ddungddung');
c.wind = { x: 0.01, y: 0 }; d.wind = { x: 0.01, y: 0 };
w.golfShot(c, 0, 20); w.golfShot(d, 0, 20); run(c, 8000); run(d, 8000);
assert(Math.abs(d.x - 50) < Math.abs(c.x - 50), '뚱뚱이가 바람에 덜 밀린다');

// 6) OB 벌타 + 복귀
s = w.golfNew(5, 'easy', 'human'); s.wind = { x: 0, y: 0 };
w.golfShot(s, 40, 0);                      // 손가락을 오른쪽으로 당김 → 왼쪽으로 세게
run(s, 8000);
assert.strictEqual(s.strokes[0], 2, 'OB 는 벌타 1');
assert.strictEqual(s.x, 50, '샷 전 자리로 복귀');
assert.strictEqual(s.last, 'ob');

// 7) 홀인: 홀 바로 앞에서 살짝 치면 들어간다 → 다음 홀
s = w.golfNew(5, 'easy', 'human'); s.wind = { x: 0, y: 0 };
const h = w.GOLF_HOLES[0]; s.x = h.x; s.y = h.y + 6;
w.golfShot(s, 0, 3.2); run(s, 6000);
assert.strictEqual(s.hole, 1, '홀인 후 다음 홀'); assert.strictEqual(s.last, 'in');
assert.strictEqual(s.strokes[0], 1); assert.strictEqual(s.x, 50); assert.strictEqual(s.y, w.GOLF.TEE_Y);

// 8) 좀비 멀리건: 첫 OB 는 벌타 없음
s = w.golfNew(5, 'easy', 'zombie'); s.wind = { x: 0, y: 0 };
w.golfShot(s, 40, 0); run(s, 8000);
assert.strictEqual(s.strokes[0], 1, '멀리건으로 벌타 없음'); assert.strictEqual(s.mulligan, 0);
w.golfShot(s, 40, 0); run(s, 8000);
assert.strictEqual(s.strokes[0], 3, '두 번째부터는 벌타');

// 9) 6타 상한: 홀을 못 넣어도 넘어간다 · 총점·배율
s = w.golfNew(5, 'hard', 'human'); s.wind = { x: 0, y: 0 };
for (let i = 0; i < 6; i++) { w.golfShot(s, 0, 0.5); run(s, 3000); }
assert.strictEqual(s.hole, 1, '6타면 다음 홀'); assert.strictEqual(s.strokes[0], 6);
s.strokes = [1, 3, 4]; s.hole = 3; s.done = true;
assert.strictEqual(w.golfTotal(s), Math.round((50 + 30 + 20) * w.GOLF_LV.hard.mul));
console.log('golf-core: OK');
```

- [ ] **Step 2: 실패 확인** — `node tools/tests/golf-core.test.mjs` → `index.html에서 GOLF를 찾지 못함` 으로 FAIL.

- [ ] **Step 3: index.html 에 코어 블록 추가** (`window.HOF_KINDS = {` 바로 앞)

```js
// ===== 골프 스윙 (2026-08-29) — 덤벨 피하기 뼈대 복제, 규칙만 골프 =====
// 설계: docs/superpowers/specs/2026-08-29-golf-swing-minigame-design.md
// 좌표 = dodge 와 같은 % 좌표(가로 0~100, 세로 0~100, 티는 아래·홀은 위). 순수 로직은 DOM·Firestore 없음.
window.GOLF = {
  W: 100, TEE_X: 50, TEE_Y: 86,
  DRAG_MAX: 38, V_MAX: 3.4,          // 당김 상한(논리 단위) · 최대 속도(단위/16ms틱)
  FRICTION: 0.982, ROUGH: 0.95, BUNKER: 0.86, BUNKER_POWER: 0.7,
  ROUGH_X: 8,                        // x<8 또는 x>92 는 러프
  STOP_V: 0.05, CUP_R: 2.2, CUP_MAX_V: 1.2, CUP_BOUNCE: 0.6,
  TREE_R: 4.5, TREE_BOUNCE: 0.5, WATER_V: 0.6,
  MAX_STROKES: 6, HOLES: 3, PAR: 3, MAX_SCORE: 999, RECS_MAX: 20
};
// 난이도 — 바람 세기(단위/틱²), 컵 배율, 페어웨이 마찰 보정, 점수 배율
window.GOLF_LV = {
  easy: { name: '하', wind: 0,     cup: 1.4,  fric: 0.975, mul: 0.7 },
  mid:  { name: '중', wind: 0.004, cup: 1.0,  fric: null,  mul: 1.0 },
  hard: { name: '상', wind: 0.010, cup: 0.85, fric: null,  mul: 2.5 }
};
// 홀 — 장애물은 타원(cx, cy, rx, ry). tree 는 원(TREE_R).
window.GOLF_HOLES = [
  { x: 50, y: 22, par: 3, bunkers: [], ponds: [], trees: [] },
  { x: 34, y: 20, par: 3, bunkers: [{ cx: 42, cy: 40, rx: 11, ry: 5 }], ponds: [], trees: [{ cx: 62, cy: 55 }] },
  { x: 66, y: 16, par: 3, bunkers: [{ cx: 74, cy: 34, rx: 9, ry: 4 }], ponds: [{ cx: 50, cy: 50, rx: 15, ry: 6 }], trees: [] }
];
// 선수 특성 — 게임 안에서만. body 키 = _CHAR_BODIES. mulligan = 홀당 벌타 면제 횟수
window.GOLF_CHARS = {
  human:      { name: '머피',     power: 1.0,  jitter: 0, windMul: 1.0, cup: 1.0, mulligan: 0, tip: '균형 잡힌 기본기' },
  human_f:    { name: '머피',     power: 1.0,  jitter: 0, windMul: 1.0, cup: 1.0, mulligan: 0, tip: '균형 잡힌 기본기' },
  heltori:    { name: '헬토리',   power: 1.25, jitter: 4, windMul: 1.0, cup: 1.0, mulligan: 0, tip: '힘은 센데 손이 떨린다' },
  ddungddung: { name: '뚱뚱이',   power: 0.85, jitter: 0, windMul: 0.4, cup: 1.0, mulligan: 0, tip: '무거워서 바람을 덜 탄다' },
  jaejin:     { name: '재진',     power: 1.1,  jitter: 0, windMul: 1.0, cup: 1.0, mulligan: 0, tip: '한 방이 있다' },
  cult:       { name: '교주',     power: 1.0,  jitter: 0, windMul: 0,   cup: 1.0, mulligan: 0, tip: '바람이 비켜 간다' },
  somm:       { name: '소믈리에', power: 1.0,  jitter: 0, windMul: 1.0, cup: 1.3, mulligan: 0, tip: '컵이 넓어 보인다' },
  zombie:     { name: '좀비',     power: 1.0,  jitter: 2, windMul: 1.0, cup: 1.0, mulligan: 1, tip: '홀마다 한 번은 없던 일로' }
};
// LCG 난수 (dodge 와 같은 식) — 시드가 같으면 바람·지터가 재현된다
window._golfRnd = function (s) { s.rnd = (s.rnd * 1103515245 + 12345) % 2147483648; return s.rnd / 2147483648; };
window.golfHoleScore = function (par, strokes) { return Math.max(0, (par + 3 - strokes)) * 10; };
window._golfWindFor = function (s) {
  const lv = window.GOLF_LV[s.lv] || window.GOLF_LV.mid;
  if (!lv.wind) return { x: 0, y: 0 };
  const ang = window._golfRnd(s) * Math.PI * 2, k = lv.wind * (s.lv === 'hard' ? (0.6 + window._golfRnd(s) * 0.8) : 1);
  return { x: Math.cos(ang) * k, y: Math.sin(ang) * k };
};
window.golfNew = function (seed, lvKey, chKey) {
  const s = { rnd: (seed | 0) || 1, lv: lvKey || 'mid', ch: chKey || 'human',
              hole: 0, strokes: [0, 0, 0], x: window.GOLF.TEE_X, y: window.GOLF.TEE_Y, vx: 0, vy: 0,
              moving: false, inBunker: false, done: false, last: '', t: 0,
              px: window.GOLF.TEE_X, py: window.GOLF.TEE_Y, mulligan: 0, wind: { x: 0, y: 0 } };
  s.mulligan = (window.GOLF_CHARS[s.ch] || window.GOLF_CHARS.human).mulligan;
  s.wind = window._golfWindFor(s);
  return s;
};
// 손가락을 (dx,dy) 만큼 당겼다 놓음(논리 단위). 공은 반대 방향으로. 성공하면 true.
window.golfShot = function (s, dx, dy) {
  const G = window.GOLF;
  if (s.done || s.moving) return false;
  const len = Math.hypot(dx, dy); if (len < 1) return false;
  const ch = window.GOLF_CHARS[s.ch] || window.GOLF_CHARS.human;
  let pow = Math.min(len, G.DRAG_MAX) / G.DRAG_MAX * G.V_MAX * ch.power * (s.inBunker ? G.BUNKER_POWER : 1);
  pow = Math.min(pow, G.V_MAX);
  let ang = Math.atan2(-dy, -dx);
  if (ch.jitter) ang += (window._golfRnd(s) * 2 - 1) * ch.jitter * Math.PI / 180;
  s.vx = Math.cos(ang) * pow; s.vy = Math.sin(ang) * pow;
  s.px = s.x; s.py = s.y; s.moving = true; s.last = ''; s.inBunker = false;
  s.strokes[s.hole]++;
  return true;
};
window._golfInEllipse = function (x, y, e) { const a = (x - e.cx) / e.rx, b = (y - e.cy) / e.ry; return a * a + b * b <= 1; };
// 한 틱. dt(ms). 반환 = s.last ('in' | 'ob' | 'water' | 'tree' | 'bunker' | 'stop' | '')
window.golfTick = function (s, dt) {
  const G = window.GOLF, lv = window.GOLF_LV[s.lv] || window.GOLF_LV.mid, ch = window.GOLF_CHARS[s.ch] || window.GOLF_CHARS.human;
  const H = window.GOLF_HOLES[s.hole];
  if (s.done || !H) return s.last;
  s.t += dt;
  if (!s.moving) return s.last;
  const k = dt / 16;
  s.vx += s.wind.x * ch.windMul * k; s.vy += s.wind.y * ch.windMul * k;
  s.x += s.vx * k; s.y += s.vy * k;
  // 나무 반사
  for (const tr of H.trees) {
    const d = Math.hypot(s.x - tr.cx, s.y - tr.cy);
    if (d < G.TREE_R && d > 1e-6) {
      const nx = (s.x - tr.cx) / d, ny = (s.y - tr.cy) / d, dot = s.vx * nx + s.vy * ny;
      s.vx = (s.vx - 2 * dot * nx) * G.TREE_BOUNCE; s.vy = (s.vy - 2 * dot * ny) * G.TREE_BOUNCE;
      s.x = tr.cx + nx * G.TREE_R; s.y = tr.cy + ny * G.TREE_R; s.last = 'tree';
    }
  }
  const penalty = function (why) {
    if (s.mulligan > 0) s.mulligan--; else s.strokes[s.hole]++;
    s.x = s.px; s.y = s.py; s.vx = 0; s.vy = 0; s.moving = false; s.last = why;
    if (s.strokes[s.hole] >= G.MAX_STROKES) window._golfNextHole(s);
  };
  // OB
  if (s.x < 2 || s.x > 98 || s.y < 1 || s.y > 99) { penalty('ob'); return s.last; }
  const sp = Math.hypot(s.vx, s.vy);
  // 연못 — 들어가면 끝(느리든 빠르든). 벌타 + 복귀
  for (const p of H.ponds) if (window._golfInEllipse(s.x, s.y, p)) { penalty('water'); return s.last; }
  // 홀
  const dh = Math.hypot(s.x - H.x, s.y - H.y);
  if (dh < G.CUP_R * lv.cup * ch.cup) {
    if (sp < G.CUP_MAX_V) { s.vx = 0; s.vy = 0; s.moving = false; s.last = 'in'; window._golfNextHole(s); return s.last; }
    s.vx *= G.CUP_BOUNCE; s.vy *= G.CUP_BOUNCE;
  }
  // 마찰
  let f = lv.fric || G.FRICTION;
  const inB = H.bunkers.some(function (b) { return window._golfInEllipse(s.x, s.y, b); });
  if (inB) f = G.BUNKER; else if (s.x < G.ROUGH_X || s.x > G.W - G.ROUGH_X) f = G.ROUGH;
  const fk = Math.pow(f, k); s.vx *= fk; s.vy *= fk;
  if (Math.hypot(s.vx, s.vy) < G.STOP_V) {
    s.vx = 0; s.vy = 0; s.moving = false; s.inBunker = inB; s.last = inB ? 'bunker' : 'stop';
    if (s.strokes[s.hole] >= G.MAX_STROKES) window._golfNextHole(s);
  }
  return s.last;
};
window._golfNextHole = function (s) {
  s.hole++;
  s.x = window.GOLF.TEE_X; s.y = window.GOLF.TEE_Y; s.px = s.x; s.py = s.y; s.vx = 0; s.vy = 0;
  s.moving = false; s.inBunker = false;
  s.mulligan = (window.GOLF_CHARS[s.ch] || window.GOLF_CHARS.human).mulligan;
  if (s.hole >= window.GOLF.HOLES) { s.done = true; s.hole = window.GOLF.HOLES; return; }
  s.wind = window._golfWindFor(s);
};
window.golfTotal = function (s) {
  const lv = window.GOLF_LV[s.lv] || window.GOLF_LV.mid;
  let sum = 0;
  for (let i = 0; i < window.GOLF.HOLES; i++) sum += window.golfHoleScore(window.GOLF_HOLES[i].par, s.strokes[i] || window.GOLF.MAX_STROKES);
  return Math.min(window.GOLF.MAX_SCORE, Math.round(sum * lv.mul));
};
```

- [ ] **Step 4: 통과 확인** — `node tools/tests/golf-core.test.mjs` → `golf-core: OK`. 테스트 7)에서 홀인이 안 되면 `CUP_MAX_V`·당김 3.2 를 조정하되 규칙(느려야 들어감)은 유지.
- [ ] **Step 5: 문법 검사** — `node tools/module-syntax-check.mjs && node tools/dogam-syntax-check.mjs`
- [ ] **Step 6: 커밋** — `git add index.html tools/tests/golf-core.test.mjs && git commit -m "골프 스윙: 순수 코어(홀·선수·물리·점수) + 테스트"`

---

### Task 2: 화면 HTML + CSS (dodge 복제, 선수 장 추가)

**Files:**
- Modify: `index.html` — `#dodge-screen` 블록(`<div id="dodge-screen"` ~ 닫는 `</div>` 뒤) **바로 뒤**에 `#golf-screen`; dodge CSS(`#dodge-pane-howto.in > *:nth-child(1)` 근처) 뒤에 골프 셀렉터.

**Interfaces:**
- Produces: DOM id — `golf-screen, golf-bg, golf-field, golf-me, golf-hud, golf-hole-n, golf-strokes, golf-score, golf-wind, golf-start-screen, golf-art-bg, golf-pane-title, golf-title-txt, golf-best, golf-challenge, golf-pane-howto, golf-lv-row, golf-lv-desc, golf-pane-char, golf-char-row, golf-pane-recs, golf-rec-list, golf-rec-share, golf-over, golf-result, golf-share, golf-keep`. onclick 은 Task 3 함수명(`golfHowto/golfChars/golfGo/golfOpen/golfRecs/golfClose/golfPickLv/golfPickChar/golfShareRec`).

- [ ] **Step 1: HTML 추가** (`#dodge-screen` 닫힘 직후)

```html
<!-- ===== 골프 스윙 (2026-08-29) — 덤벨 피하기와 같은 구조 ===== -->
<div id="golf-screen" style="display:none;position:fixed;inset:0;height:100dvh;z-index:2300;max-width:390px;margin:0 auto;overflow:hidden;touch-action:none;overscroll-behavior:contain;background:#05070c;font-family:'Galmuri11',sans-serif">
  <div id="golf-bg" style="position:absolute;inset:0;background:#0e2412 center/cover no-repeat;image-rendering:pixelated;opacity:.45;pointer-events:none"></div>
  <div id="golf-field" style="position:absolute;inset:0;pointer-events:none"></div>
  <div id="golf-me" style="position:absolute;left:0;top:0;pointer-events:none;transform:translate(-50%,-100%)"></div>
  <div id="golf-hud" style="display:none;position:absolute;left:12px;top:12px;z-index:5;color:#fff;font-size:15px;text-shadow:0 2px 0 #05070c;pointer-events:none">
    <div>홀 <span id="golf-hole-n">1</span>/3 · <span id="golf-strokes">0</span>타</div>
    <div style="font-size:12.5px;color:rgba(255,255,255,.62);margin-top:3px;font-variant-numeric:tabular-nums">점수 <span id="golf-score">0</span></div>
    <div id="golf-wind" style="font-size:12px;color:#F5C24B;margin-top:5px"></div>
  </div>
  <button onclick="window.golfClose()" style="position:absolute;right:12px;top:12px;z-index:5;background:rgba(13,19,34,.78);border:2px solid #05070c;color:#cfd6e6;font-family:inherit;font-size:11.5px;padding:6px 10px;cursor:pointer">나가기</button>
  <div id="golf-start-screen" style="display:none;position:absolute;inset:0;z-index:7;flex-direction:column;align-items:center;justify-content:flex-end;gap:16px;padding:26px;background-color:#05070c;overflow:hidden">
    <div id="golf-art-bg" style="position:absolute;inset:0;background:center/cover no-repeat;image-rendering:pixelated;pointer-events:none"></div>
    <div style="position:absolute;inset:0;background:linear-gradient(180deg,transparent 34%,rgba(5,7,12,.62) 62%,rgba(5,7,12,.9) 100%);pointer-events:none"></div>
    <div style="position:absolute;left:18px;top:16px;display:flex;align-items:center;gap:6px;font-size:10px;color:rgba(255,255,255,.55)">from <img src="char/ui/ui_logo.png" alt="Murpy" style="height:13px"></div>
    <div id="golf-pane-title" class="dodge-pane" style="display:flex;flex-direction:column;align-items:center;gap:16px;width:100%;margin-top:auto;position:relative">
      <div id="golf-title-txt" style="font-family:'Galmuri14',sans-serif;font-size:30px;color:#fff;text-shadow:0 3px 0 #05070c">골프 스윙</div>
      <div id="golf-best" style="font-size:12.5px;color:#F5C24B"></div>
      <div id="golf-challenge" style="font-size:12.5px;color:#cfd6e6;display:none"></div>
      <button class="dodge-cta" onclick="window.golfHowto()">눌러서 시작</button>
      <button class="dodge-cta ghost" onclick="window.golfRecs()">내 기록 보기</button>
    </div>
    <div id="golf-pane-howto" class="dodge-pane" style="display:none;flex-direction:column;align-items:center;gap:18px;width:100%;position:relative">
      <div style="font-family:'Galmuri14',sans-serif;font-size:18px;color:#fff">이렇게 하면 돼요</div>
      <div style="font-size:13px;color:#e8edf7;line-height:1.75;text-align:center">공 뒤로 <b style="color:#3D7EFF">당겼다 놓으면</b> 세기와 방향이 정해져요.<br>3홀 · 적은 타수로 넣을수록 점수가 커요.</div>
      <div style="display:flex;gap:14px;font-size:11.5px;color:#cfd6e6;text-align:center">
        <div><div class="golf-ico golf-ico-hole"></div>홀 · 느리게 굴려야 들어가요</div>
        <div><div class="golf-ico golf-ico-bunker"></div>벙커 · 빨리 서고 다음 샷이 약해요</div>
        <div><div class="golf-ico golf-ico-pond"></div>연못 · 벌타 1</div>
      </div>
      <div style="width:100%"><div style="font-size:11.5px;color:rgba(255,255,255,.5);margin-bottom:6px">난이도</div>
        <div id="golf-lv-row" style="display:flex;gap:8px"></div>
        <div id="golf-lv-desc" style="font-size:11.5px;color:rgba(255,255,255,.55);margin-top:8px"></div></div>
      <button class="dodge-cta" onclick="window.golfChars()">선수 고르기</button>
      <button class="dodge-cta ghost" onclick="window.golfOpen()">뒤로</button>
    </div>
    <div id="golf-pane-char" class="dodge-pane" style="display:none;flex-direction:column;align-items:center;gap:14px;width:100%;position:relative">
      <div style="font-family:'Galmuri14',sans-serif;font-size:18px;color:#fff">누구로 칠까요?</div>
      <div id="golf-char-row" style="display:flex;gap:10px;overflow-x:auto;width:100%;padding:4px 2px 8px;scroll-snap-type:x mandatory"></div>
      <button class="dodge-cta" onclick="window.golfGo()">시작!</button>
      <button class="dodge-cta ghost" onclick="window.golfHowto()">뒤로</button>
    </div>
    <div id="golf-pane-recs" class="dodge-pane" style="display:none;flex-direction:column;align-items:center;gap:14px;width:100%;position:relative">
      <div style="font-family:'Galmuri14',sans-serif;font-size:18px;color:#fff">내 기록</div>
      <div id="golf-rec-list" style="width:100%;max-height:38vh;overflow-y:auto"></div>
      <div id="golf-rec-share"></div>
      <button class="dodge-cta ghost" onclick="window.golfOpen()">뒤로</button>
    </div>
    <button onclick="window.golfClose()" style="position:relative;background:none;border:none;color:rgba(255,255,255,.4);font-family:inherit;font-size:12px;cursor:pointer;padding:6px">나가기</button>
  </div>
  <div id="golf-over" style="display:none;position:absolute;inset:0;z-index:6;background:rgba(5,7,12,.86);flex-direction:column;align-items:center;justify-content:center;gap:14px;padding:26px;text-align:center">
    <div id="golf-result"></div>
    <div id="golf-share" class="mw-share"></div>
    <div id="golf-keep"></div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;justify-content:center">
      <button class="dodge-cta" onclick="window.golfGo()">다시 하기</button>
      <button class="dodge-cta ghost" onclick="window.golfOpen()">난이도·선수</button>
      <button class="dodge-cta ghost" onclick="window.golfClose()">그만</button>
    </div>
  </div>
</div>
```

- [ ] **Step 2: CSS 추가** (dodge 게임 CSS 끝, `#dodge-pane-recs.in > *:nth-child(4)` 규칙 뒤)

```css
/* ===== 골프 스윙 — dodge 셀렉터 병기 ===== */
#golf-start-screen.in{animation:dodgeScreenIn .34s ease both}
#golf-art-bg.in{animation:dodgeArtIn 1.5s cubic-bezier(.2,.8,.2,1) both}
#golf-pane-title.in > *{animation:dodgePaneIn .5s ease both}
#golf-pane-title.in > *:nth-child(1){animation-delay:.55s}#golf-pane-title.in > *:nth-child(2){animation-delay:.7s}
#golf-pane-title.in > *:nth-child(3){animation-delay:.8s}#golf-pane-title.in > *:nth-child(4){animation-delay:.92s}#golf-pane-title.in > *:nth-child(5){animation-delay:1.05s}
#golf-pane-howto.in > *,#golf-pane-char.in > *,#golf-pane-recs.in > *{animation:dodgePaneIn .5s ease both}
#golf-pane-howto.in > *:nth-child(1),#golf-pane-char.in > *:nth-child(1),#golf-pane-recs.in > *:nth-child(1){animation-delay:.04s}
#golf-pane-howto.in > *:nth-child(2),#golf-pane-char.in > *:nth-child(2),#golf-pane-recs.in > *:nth-child(2){animation-delay:.12s}
#golf-pane-howto.in > *:nth-child(3),#golf-pane-char.in > *:nth-child(3),#golf-pane-recs.in > *:nth-child(3){animation-delay:.2s}
#golf-pane-howto.in > *:nth-child(4),#golf-pane-char.in > *:nth-child(4){animation-delay:.28s}
#golf-pane-howto.in > *:nth-child(5){animation-delay:.36s}
#golf-pane-title.in > .dodge-cta,#golf-pane-howto.in > .dodge-cta,#golf-pane-char.in > .dodge-cta{animation:dodgePaneIn .5s ease both, dodgeCta 1.6s ease-in-out 1.2s infinite}
.golf-ico{width:44px;height:44px;margin:0 auto 6px;image-rendering:pixelated;background:center/contain no-repeat}
.golf-ico-hole{background-image:url('char/game/golf_hole.png?v=1')}
.golf-ico-bunker{background-image:url('char/game/golf_bunker.png?v=1')}
.golf-ico-pond{background-image:url('char/game/golf_pond.png?v=1')}
.golf-ball{position:absolute;width:18px;height:18px;border-radius:50%;background:#fff;box-shadow:inset -3px -3px 0 #cfd6e6,0 3px 0 rgba(0,0,0,.35);transform:translate(-50%,-50%);image-rendering:pixelated}
.golf-ball.img{background:center/contain no-repeat;box-shadow:none;border-radius:0}
.golf-hole{position:absolute;transform:translate(-50%,-100%);width:26px;height:40px;background:center bottom/contain no-repeat;image-rendering:pixelated}
.golf-hole.css::before{content:'';position:absolute;left:50%;bottom:0;width:16px;height:8px;margin-left:-8px;border-radius:50%;background:#1a1f16;border:2px solid #e8edf7}
.golf-hole.css::after{content:'';position:absolute;left:50%;bottom:6px;width:2px;height:30px;background:#fff;box-shadow:3px -22px 0 3px #e5484d}
.golf-obs{position:absolute;transform:translate(-50%,-50%);border-radius:50%;image-rendering:pixelated;background:center/contain no-repeat}
.golf-obs.bunker.css{background:#f3e4b3;border:2px solid #d9c58c}
.golf-obs.pond.css{background:#8fd3f4;border:2px solid #5fb0dc}
.golf-obs.tree.css{border-radius:50%;background:#5fbf64;box-shadow:inset -6px -6px 0 #4fa35a}
.golf-aim{position:absolute;left:0;top:0;height:0;border-top:3px dashed rgba(255,255,255,.85);transform-origin:0 50%;pointer-events:none}
.golf-aim::after{content:'';position:absolute;right:-6px;top:-6px;width:9px;height:9px;border-radius:50%;background:#3D7EFF;border:2px solid #fff}
.golf-gauge{position:absolute;width:8px;height:44px;background:rgba(5,7,12,.7);border:2px solid #05070c;transform:translate(14px,-50%)}
.golf-gauge > i{position:absolute;left:0;right:0;bottom:0;background:#3D7EFF}
.golf-gauge.hot > i{background:#F5C24B}
.golf-card{flex:0 0 118px;scroll-snap-align:start;border:2px solid rgba(255,255,255,.14);padding:10px 8px;text-align:center;background:none;cursor:pointer;color:#e8edf7;font-family:inherit}
.golf-card.on{border-color:#3D7EFF;box-shadow:0 0 0 2px rgba(61,126,255,.35)}
.golf-card.lock{opacity:.38}
.golf-card .bar{height:5px;background:rgba(255,255,255,.12);margin-top:4px}.golf-card .bar > i{display:block;height:100%;background:#3D7EFF}
@keyframes golfSwing{0%{transform:translate(-50%,-100%) scale(1)}40%{transform:translate(-50%,-100%) scale(1.1,.92)}100%{transform:translate(-50%,-100%) scale(1)}}
#golf-me.swing{animation:golfSwing .25s ease}
```

- [ ] **Step 3: 문법 검사** 두 개 → OK. 브라우저에서 `window.golfOpen` 은 아직 없으니 화면은 안 뜬다(정상).
- [ ] **Step 4: 커밋** — `git add index.html && git commit -m "골프 스윙: 화면 HTML/CSS (dodge 뼈대 복제 + 선수 장)"`

---

### Task 3: 시작화면 흐름·난이도·선수 선택·필드 칩·뒤로가기

**Files:**
- Modify: `index.html` — 골프 JS 블록(Task 1) 뒤에 이어서. `charSetField` 끝의 `window.dodgeFieldBtn(key)` 줄 옆. 뒤로가기 처리(`dodge-screen` 을 검사하는 곳, 약 10623). `showSplashOnboarding` 래핑(dodge `_dodgeLinkBoot` 안의 조건).

**Interfaces:**
- Consumes: Task 1 전역, Task 2 DOM.
- Produces: `window.golfOpen()`, `golfHowto()`, `golfChars()`, `golfRecs()`, `golfGo()`, `golfClose()`, `golfPickLv(k)`, `golfPickChar(k)`, `_golfShowPane(id)`, `_golfPaintStart()`, `_golfLv`, `_golfCh`, `_golfOwnedBodies()`, `golfFieldBtn(key)`.

- [ ] **Step 1: 흐름 코드 추가**

```js
window._golfLv = (function () { try { return localStorage.getItem('golf_lv') || 'mid'; } catch (e) { return 'mid'; } })();
window._golfCh = (function () { try { return localStorage.getItem('golf_char') || ''; } catch (e) { return ''; } })();
window.golfPickLv = function (k) { if (!window.GOLF_LV[k]) return; window._golfLv = k; try { localStorage.setItem('golf_lv', k); } catch (e) {} window._golfPaintStart(); };
window.golfPickChar = function (k) { if (!window.GOLF_CHARS[k]) return; if (!window._golfOwnedBodies().has(k)) { showToast('아직 해금하지 않은 캐릭터예요'); return; } window._golfCh = k; try { localStorage.setItem('golf_char', k); } catch (e) {} window._golfPaintChars(); };
// 내가 가진 몸통 — 캐릭터 시스템의 판정(옷장·해금 플래그)을 그대로 쓴다. 기본 몸통은 항상 있다.
window._golfOwnedBodies = function () {
  const set = new Set(['human', 'human_f']);
  const B = window._CHAR_BODIES || {}, me = (window.currentUser || {}).uid || '';
  const cfg = window.getMyCharacter ? window.getMyCharacter() : null;
  Object.keys(B).forEach(function (k) {
    const b = B[k];
    if (b.owner) { if (b.owner === me) set.add(k); return; }
    if (b.hidden) { if (window._mwHiddenOwned && window._mwHiddenOwned(k)) set.add(k); return; }
    if (b.code) { if (window._charBodyUnlocked && window._charBodyUnlocked(k)) set.add(k); return; }
  });
  if (cfg && cfg.body) set.add(cfg.body);
  return set;
};
window._golfMyBody = function () { const cfg = window.getMyCharacter ? window.getMyCharacter() : null; return (cfg && cfg.body) || 'human'; };
window._golfCharCfg = function () {
  const base = window.getMyCharacter ? window.getMyCharacter() : window.CHAR_DEFAULT;
  const cfg = Object.assign({}, base || {});
  const ch = window._golfCh && window._golfOwnedBodies().has(window._golfCh) ? window._golfCh : window._golfMyBody();
  cfg.body = ch;
  if (window._charEnsureDefaults) window._charEnsureDefaults(cfg);
  return cfg;
};
window._golfShowPane = function (id) {
  document.querySelectorAll('#golf-start-screen .dodge-pane').forEach(function (el) { el.classList.remove('in'); el.style.display = 'none'; });
  const el = document.getElementById(id); if (!el) return;
  const ss = document.getElementById('golf-start-screen'), ab = document.getElementById('golf-art-bg');
  if (id !== 'golf-pane-title') {
    if (ss) { ss.style.backgroundColor = 'rgba(5,7,12,.58)'; ss.style.justifyContent = 'center'; }
    if (ab) { ab.classList.remove('in'); ab.style.opacity = '0'; }
  } else {
    if (ss) { ss.style.backgroundColor = '#05070c'; ss.style.justifyContent = 'flex-end'; }
    if (ab) ab.style.opacity = '';
  }
  el.style.display = 'flex'; void el.offsetWidth; el.classList.add('in');
};
window._golfPaintStart = function () {
  const row = document.getElementById('golf-lv-row'), desc = document.getElementById('golf-lv-desc');
  if (row) row.innerHTML = Object.keys(window.GOLF_LV).map(function (k) {
    const on = k === window._golfLv;
    return '<button class="dodge-lv-btn' + (on ? ' on' : '') + '" onclick="window.golfPickLv(\'' + k + '\')" style="flex:1;font-family:inherit;font-size:13px;padding:9px 0;cursor:pointer;border:2px solid ' + (on ? 'var(--accent)' : 'rgba(255,255,255,.18)') + ';background:' + (on ? 'var(--accent)' : 'none') + ';color:#fff">' + window.GOLF_LV[k].name + '</button>';
  }).join('');
  const lv = window.GOLF_LV[window._golfLv] || window.GOLF_LV.mid;
  if (desc) desc.textContent = lv.wind ? ('바람 ' + (window._golfLv === 'hard' ? '강함' : '약함') + ' · 컵 ' + lv.cup + '배 · 점수 ×' + lv.mul) : ('바람 없음 · 컵 ' + lv.cup + '배 · 점수 ×' + lv.mul);
  const best = document.getElementById('golf-best');
  if (best) best.textContent = window._golfBest > 0 ? ('내 최고 ' + window._golfBest + '점') : '';
  const tt = document.getElementById('golf-title-txt'); if (tt) tt.style.display = window._golfArt ? 'none' : '';
};
window._golfPaintChars = function () {
  const row = document.getElementById('golf-char-row'); if (!row) return;
  const owned = window._golfOwnedBodies();
  const cur = window._golfCh && owned.has(window._golfCh) ? window._golfCh : window._golfMyBody();
  const base = window.getMyCharacter ? window.getMyCharacter() : window.CHAR_DEFAULT;
  const keys = Object.keys(window.GOLF_CHARS).filter(function (k) { return k !== (window._golfMyBody() === 'human_f' ? 'human' : 'human_f'); });
  row.innerHTML = keys.map(function (k) {
    const c = window.GOLF_CHARS[k], has = owned.has(k), on = k === cur;
    const cfg = Object.assign({}, base || {}, { body: k }); if (window._charEnsureDefaults) window._charEnsureDefaults(cfg);
    const bar = function (v, max) { return '<div class="bar"><i style="width:' + Math.round(v / max * 100) + '%"></i></div>'; };
    return '<button class="golf-card' + (on ? ' on' : '') + (has ? '' : ' lock') + '" onclick="window.golfPickChar(\'' + k + '\')">'
      + '<div style="height:64px;display:flex;align-items:flex-end;justify-content:center">' + (window.mwMiniCharHtml ? window.mwMiniCharHtml(cfg, 60, 'down') : '') + '</div>'
      + '<div style="font-size:12.5px;margin-top:6px">' + c.name + '</div>'
      + '<div style="font-size:10px;color:rgba(255,255,255,.5);margin-top:2px;min-height:26px">' + (has ? c.tip : '해금하면 쓸 수 있어요') + '</div>'
      + '<div style="font-size:9.5px;color:rgba(255,255,255,.4);text-align:left;margin-top:4px">파워' + bar(c.power, 1.3) + '정확' + bar(5 - c.jitter, 5) + '바람' + bar(1 - c.windMul, 1) + '</div>'
      + '</button>';
  }).join('');
};
window.golfOpen = function () {
  const el = document.getElementById('golf-screen'); if (!el) return;
  window._golfCheckArt(); window._golfApplyBg();
  document.getElementById('golf-over').style.display = 'none';
  el.style.display = 'block';
  try { document.documentElement.style.overflow = 'hidden'; document.body.style.overflow = 'hidden'; } catch (e) {}
  cancelAnimationFrame(window._golfRaf); window._golfRaf = 0; window._golfS = null;
  const hud = document.getElementById('golf-hud'); if (hud) hud.style.display = 'none';
  const f = document.getElementById('golf-field'); if (f) f.innerHTML = '';
  const me = document.getElementById('golf-me'); if (me) me.innerHTML = '';
  const ss = document.getElementById('golf-start-screen');
  if (ss) { ss.style.display = 'flex'; ss.classList.remove('in'); void ss.offsetWidth; ss.classList.add('in'); }
  window._golfShowPane('golf-pane-title'); window._golfPaintStart();
  const ab = document.getElementById('golf-art-bg'); if (ab && window._golfArt) { ab.classList.remove('in'); void ab.offsetWidth; ab.classList.add('in'); }
  window._golfBind();
};
window.golfHowto = function () { window._golfShowPane('golf-pane-howto'); window._golfPaintStart(); };
window.golfChars = function () { window._golfShowPane('golf-pane-char'); window._golfPaintChars(); };
window.golfClose = function () {
  cancelAnimationFrame(window._golfRaf); window._golfRaf = 0; window._golfS = null;
  const el = document.getElementById('golf-screen'); if (el) el.style.display = 'none';
  try { document.documentElement.style.overflow = ''; document.body.style.overflow = ''; } catch (e) {}
  if (window._golfObPending) { const f = window._golfObPending; window._golfObPending = null; try { f(); } catch (e) {} }
};
// 필드 칩 — 골프 필드에서만. dodge 와 같은 자리(top 52px)
window.golfFieldBtn = function (key) {
  const room = document.getElementById('charworld-room'); if (!room) return;
  let b = document.getElementById('golf-start');
  if (key !== 'golf') { if (b) b.remove(); return; }
  if (b) return;
  b = document.createElement('button');
  b.id = 'golf-start'; b.className = 'mw-fieldchip'; b.style.top = '52px'; b.textContent = '골프 스윙';
  b.onclick = function (e) { e.stopPropagation(); window.golfOpen(); };
  room.appendChild(b);
};
```

- [ ] **Step 2: 훅 3곳**
  - `charSetField` 끝 `window.dodgeFieldBtn(key)` 바로 뒤에 `if (window.golfFieldBtn) window.golfFieldBtn(key);`
  - 뒤로가기(dodge-screen 을 보는 분기) 옆에 같은 모양으로: `const gs = document.getElementById('golf-screen'); if (gs && gs.style.display !== 'none') { window.golfClose(); return; }`
  - `_golfOwnedBodies` 가 부르는 `_mwHiddenOwned`·`_charBodyUnlocked` 가 실제 이름과 다르면 **이 단계에서** `rg "hidden.*owned\|unlock" index.html` 로 실제 판정 함수를 찾아 바꾼다(없으면 `cfg.body` 만으로 판정 = 현재 쓰는 몸통만 열림).
- [ ] **Step 3: 문법 검사 → 브라우저에서 골프 필드 → 칩 → 타이틀/설명/선수 장 전환 확인.**
- [ ] **Step 4: 커밋** — `"골프 스윙: 시작화면 흐름·난이도·선수 선택·필드 칩"`

---

### Task 4: 게임 루프·그리기·입력(당겼다 놓기)·결과 화면

**Files:**
- Modify: `index.html` — 골프 JS 블록 이어서.

**Interfaces:**
- Consumes: Task 1 `golfNew/golfShot/golfTick/golfTotal`, Task 3 `_golfCharCfg/_golfShowPane`.
- Produces: `window.golfGo()`, `_golfFrame`, `_golfPaint(s)`, `_golfBind()`, `_golfEnd(s)`, `_golfApplyBg()`, `_golfCheckArt()`. `_golfEnd` 는 Task 5 의 `golfSave(score, sec, s)` 와 `_golfShowShare(score, s)` 를 부른다(Task 5 전까지는 `window.golfSave && ...` 가드).

- [ ] **Step 1: 배경·아트 로딩 (dodge 패턴: 그냥 쓰고 onerror 로 폴백)**

```js
window._golfApplyBg = function () {
  const bg = document.getElementById('golf-bg'); if (!bg) return;
  bg.style.backgroundImage = "url('char/game/golf_bg.jpg?v=1')"; bg.style.opacity = '.62';
  const probe = new Image();
  probe.onerror = function () { bg.style.backgroundImage = "url('char/fields/field_golf.png?v=3')"; bg.style.opacity = '.45'; };
  probe.src = 'char/game/golf_bg.jpg?v=1';
};
window._golfCheckArt = function () {
  if (window._golfArt != null) return;
  const im = new Image();
  im.onload = function () { window._golfArt = true; const a = document.getElementById('golf-art-bg'); if (a) a.style.backgroundImage = "url('char/game/golf_title.png?v=1')"; window._golfPaintStart && window._golfPaintStart(); };
  im.onerror = function () { window._golfArt = false; window._golfPaintStart && window._golfPaintStart(); };
  im.src = 'char/game/golf_title.png?v=1';
  window._golfObj = {};
  ['ball', 'hole', 'bunker', 'pond', 'tree'].forEach(function (k) { const o = new Image(); o.onload = function () { window._golfObj[k] = true; }; o.onerror = function () { window._golfObj[k] = false; }; o.src = 'char/game/golf_' + k + '.png?v=1'; });
};
```

- [ ] **Step 2: 좌표 변환·그리기**

```js
// 논리 → 화면. 위로 갈수록 좁아지는 페어웨이(가로 62%)와 작아지는 스프라이트(55%)
window._golfSx = function (x, y, W) { return (50 + (x - 50) * (0.62 + 0.38 * y / 100)) / 100 * W; };
window._golfSy = function (y, H) { return y / 100 * H; };
window._golfScale = function (y) { return 0.55 + 0.45 * y / 100; };
window._golfPaint = function (s) {
  const host = document.getElementById('golf-field'); if (!host) return;
  const W = host.clientWidth || 360, H = host.clientHeight || 640, G = window.GOLF, O = window._golfObj || {};
  const Hh = window.GOLF_HOLES[Math.min(s.hole, G.HOLES - 1)];
  const px = function (x, y) { return window._golfSx(x, y, W); }, py = function (y) { return window._golfSy(y, H); };
  let h = '';
  const obs = function (list, cls, k) { list.forEach(function (e) { const sc = window._golfScale(e.cy); const w = e.rx * 2 / 100 * W * (0.62 + 0.38 * e.cy / 100), hh = e.ry * 2 / 100 * H;
    h += '<div class="golf-obs ' + cls + (O[k] ? '' : ' css') + '" style="left:' + px(e.cx, e.cy) + 'px;top:' + py(e.cy) + 'px;width:' + w + 'px;height:' + hh + 'px;' + (O[k] ? "background-image:url('char/game/golf_" + k + ".png?v=1')" : '') + '"></div>'; }); };
  obs(Hh.ponds, 'pond', 'pond'); obs(Hh.bunkers, 'bunker', 'bunker');
  Hh.trees.forEach(function (t) { const sc = window._golfScale(t.cy), sz = G.TREE_R * 2 / 100 * W * sc;
    h += '<div class="golf-obs tree' + (O.tree ? '' : ' css') + '" style="left:' + px(t.cx, t.cy) + 'px;top:' + py(t.cy) + 'px;width:' + sz + 'px;height:' + (sz * 1.25) + 'px;' + (O.tree ? "background-image:url('char/game/golf_tree.png?v=1');border-radius:0" : '') + '"></div>'; });
  const hs = window._golfScale(Hh.y);
  h += '<div class="golf-hole' + (O.hole ? '' : ' css') + '" style="left:' + px(Hh.x, Hh.y) + 'px;top:' + (py(Hh.y) + 6 * hs) + 'px;transform:translate(-50%,-100%) scale(' + hs + ');' + (O.hole ? "background-image:url('char/game/golf_hole.png?v=1')" : '') + '"></div>';
  const bs = window._golfScale(s.y);
  h += '<div class="golf-ball' + (O.ball ? ' img' : '') + '" style="left:' + px(s.x, s.y) + 'px;top:' + py(s.y) + 'px;transform:translate(-50%,-50%) scale(' + bs + ');' + (O.ball ? "background-image:url('char/game/golf_ball.png?v=1')" : '') + '"></div>';
  // 조준선 + 게이지 (당기는 중)
  const d = window._golfDrag;
  if (d && !s.moving && !s.done) {
    const dx = d.cx - d.sx, dy = d.cy - d.sy, len = Math.min(Math.hypot(dx, dy), G.DRAG_MAX), ang = Math.atan2(-dy, -dx) * 180 / Math.PI;
    const ratio = len / G.DRAG_MAX;
    h += '<div class="golf-aim" style="left:' + px(s.x, s.y) + 'px;top:' + py(s.y) + 'px;width:' + (ratio * 0.42 * W) + 'px;transform:rotate(' + ang + 'deg)"></div>';
    h += '<div class="golf-gauge' + (ratio > 0.8 ? ' hot' : '') + '" style="left:' + px(s.x, s.y) + 'px;top:' + py(s.y) + 'px"><i style="height:' + Math.round(ratio * 100) + '%"></i></div>';
  }
  host.innerHTML = h;
  // 캐릭터 — 티 옆(공 왼쪽)에 서 있고 공이 움직이면 제자리
  const me = document.getElementById('golf-me');
  if (me) {
    const chH = Math.round(0.11 * H);
    if (me._h !== chH || me._face !== (window._golfFace || 'up')) { me._h = chH; me._face = window._golfFace || 'up'; me.innerHTML = window.mwMiniCharHtml ? window.mwMiniCharHtml(window._golfCharCfg(), chH, me._face) : ''; }
    me.style.left = px(G.TEE_X - 9, G.TEE_Y) + 'px'; me.style.top = (py(G.TEE_Y) + 4) + 'px';
  }
  const hn = document.getElementById('golf-hole-n'), st = document.getElementById('golf-strokes'), sc = document.getElementById('golf-score'), wd = document.getElementById('golf-wind');
  if (hn) hn.textContent = Math.min(s.hole + 1, G.HOLES);
  if (st) st.textContent = s.strokes[Math.min(s.hole, G.HOLES - 1)];
  if (sc) sc.textContent = window.golfTotal(Object.assign({}, s, { strokes: s.strokes.map(function (v, i) { return i < s.hole ? v : G.MAX_STROKES; }) }));
  if (wd) { const k = Math.hypot(s.wind.x, s.wind.y); wd.textContent = k ? ('바람 ' + (Math.abs(s.wind.x) > Math.abs(s.wind.y) ? (s.wind.x > 0 ? '→' : '←') : (s.wind.y > 0 ? '↓' : '↑')) + ' ' + (k >= 0.008 ? '강' : '약')) : '바람 없음'; }
};
```

- [ ] **Step 3: 루프·입력·시작·종료**

```js
window.golfGo = function () {
  const ss = document.getElementById('golf-start-screen'); if (ss) ss.style.display = 'none';
  document.getElementById('golf-over').style.display = 'none';
  const hud = document.getElementById('golf-hud'); if (hud) hud.style.display = '';
  const me = document.getElementById('golf-me'); if (me) { me._h = 0; me.innerHTML = ''; }
  const ch = window._golfCh && window._golfOwnedBodies().has(window._golfCh) ? window._golfCh : window._golfMyBody();
  window._golfS = window.golfNew(Date.now(), window._golfLv, ch);
  window._golfStartAt = Date.now(); window._golfDrag = null; window._golfLast = 0; window._golfFace = 'up';
  cancelAnimationFrame(window._golfRaf); window._golfRaf = requestAnimationFrame(window._golfFrame);
};
window._golfFrame = function (ts) {
  const s = window._golfS; if (!s) return;
  const dt = Math.min(50, ts - (window._golfLast || ts)); window._golfLast = ts;
  const before = s.hole, r = window.golfTick(s, dt);
  if (r === 'in' && s.hole !== before) showToast(s.strokes[before] === 1 ? '홀인원!' : (s.strokes[before] + '타로 홀인'));
  else if (r === 'water') showToast('연못에 빠졌어요 · 벌타 1');
  else if (r === 'ob') showToast('코스 밖 · 벌타 1');
  else if (r === 'bunker' && !s.moving) showToast('벙커 · 다음 샷이 약해져요');
  if (r === 'in' || r === 'water' || r === 'ob' || r === 'bunker' || r === 'stop') s.last = '';
  window._golfPaint(s);
  if (s.done) { window._golfEnd(s); return; }
  window._golfRaf = requestAnimationFrame(window._golfFrame);
};
// 입력 — 화면 아무 데나 누르고 당긴다. 버튼 위·굴러가는 중·게임 없음이면 무시(dodge skip 과 같다)
window._golfBind = function () {
  const el = document.getElementById('golf-screen'); if (!el || el._bound) return; el._bound = 1;
  const host = document.getElementById('golf-field');
  const toLogic = function (cx, cy) { const r = host.getBoundingClientRect(); return { x: (cx - r.left) / r.width * 100, y: (cy - r.top) / r.height * 100 }; };
  const skip = function (t) { const s = window._golfS; return !s || s.moving || s.done || (t && t.closest && t.closest('button')); };
  const down = function (cx, cy, t) { if (skip(t)) return; const p = toLogic(cx, cy); window._golfDrag = { sx: p.x, sy: p.y, cx: p.x, cy: p.y }; };
  const move = function (cx, cy) { if (!window._golfDrag) return; const p = toLogic(cx, cy); window._golfDrag.cx = p.x; window._golfDrag.cy = p.y; };
  const up = function () {
    const d = window._golfDrag, s = window._golfS; window._golfDrag = null; if (!d || !s) return;
    const dx = d.cx - d.sx, dy = d.cy - d.sy;
    if (window.golfShot(s, dx, dy)) {
      window._golfFace = dx > 2 ? 'left' : (dx < -2 ? 'right' : 'up');
      const me = document.getElementById('golf-me'); if (me) { me.classList.remove('swing'); void me.offsetWidth; me.classList.add('swing'); }
      if (navigator.vibrate) navigator.vibrate(8);
    }
  };
  el.addEventListener('touchstart', function (e) { const t = e.touches[0]; down(t.clientX, t.clientY, e.target); if (window._golfDrag) e.preventDefault(); }, { passive: false });
  el.addEventListener('touchmove', function (e) { if (!window._golfDrag) return; const t = e.touches[0]; move(t.clientX, t.clientY); e.preventDefault(); }, { passive: false });
  el.addEventListener('touchend', up); el.addEventListener('touchcancel', function () { window._golfDrag = null; });
  el.addEventListener('mousedown', function (e) { down(e.clientX, e.clientY, e.target); });
  el.addEventListener('mousemove', function (e) { if (e.buttons) move(e.clientX, e.clientY); });
  el.addEventListener('mouseup', up);
};
window._golfEnd = function (s) {
  cancelAnimationFrame(window._golfRaf); window._golfRaf = 0;
  const score = window.golfTotal(s), sec = Math.round((Date.now() - (window._golfStartAt || Date.now())) / 1000);
  const lv = window.GOLF_LV[s.lv] || window.GOLF_LV.mid, ch = window.GOLF_CHARS[s.ch] || window.GOLF_CHARS.human;
  const isBest = score > (window._golfBest || 0); if (isBest) window._golfBest = score;
  const holes = s.strokes.map(function (v, i) { return '<span style="display:inline-block;margin:0 6px"><span style="color:rgba(255,255,255,.45)">' + (i + 1) + '홀</span> <b>' + v + '타</b></span>'; }).join('');
  const res = document.getElementById('golf-result');
  if (res) res.innerHTML = '<div style="font-family:\'Galmuri14\',sans-serif;font-size:14px;color:rgba(255,255,255,.55)">' + ch.name + ' · 난이도 ' + lv.name + '</div>'
    + '<div style="font-family:\'Galmuri14\',sans-serif;font-size:48px;color:#fff;margin:6px 0 2px">' + score + '<span style="font-size:18px;color:#F5C24B"> 점</span></div>'
    + '<div style="font-size:12.5px;color:#cfd6e6">' + holes + '</div>'
    + (isBest && score > 0 ? '<div style="font-size:12.5px;color:#F5C24B;margin-top:8px">내 최고 기록!</div>' : '')
    + '<div style="font-size:11.5px;color:rgba(255,255,255,.4);margin-top:6px">' + Math.floor(sec / 60) + ':' + String(sec % 60).padStart(2, '0') + '</div>';
  document.getElementById('golf-over').style.display = 'flex';
  window._golfLastScore = score; window._golfLastSec = sec; window._golfLastS = s; window._golfShared = false;
  if (window._golfShowShare) window._golfShowShare(score, s);
  if (window.golfSave) window.golfSave(score, sec, s);
};
```

- [ ] **Step 4: 문법 검사 → 데스크톱 크롬 모바일 모드에서 한 판 끝까지(마우스 드래그). 홀인·벌타·벙커 토스트·결과 화면 확인.**
- [ ] **Step 5: 커밋** — `"골프 스윙: 게임 루프·그리기·당겼다 놓기 입력·결과 화면"`

---

### Task 5: 기록(Firestore·게스트)·공유 카드·링크·명예의 전당·auth 승격

**Files:**
- Modify: `index.html` — 골프 JS 블록 이어서; `HOF_KINDS` 에 golf 추가; `onAuthStateChanged` 안 `dodgeGuestPromote` 호출 옆; 게스트 닉 시트 억제 조건(`_dodgeFromLink`)에 `|| window._golfFromLink`; 월요일 팝업 종목 회전 배열.
- Test: `tools/tests/golf-guest.test.mjs`(dodge-guest.test.mjs 복제: `golfParseLink/golfMakeLink`)

**Interfaces:**
- Consumes: dodge 의 `dodgeGuestMerge(cur, rec, max)`, `dodgeNickGet/dodgeNickSave`, `mwShareKakao/mwShareSheet/mwSaveStamp/_mwKakaoPrep`, `_mwStampData/_mwShareMeta`, `_hofRank`.
- Produces: `golfSave(score, sec, s)`, `golfGuestLoad/Save/Clear`, `golfGuestPromote()`, `golfRecs()`, `golfShareRec(i)`, `_golfCardImg(score, s, cb)`, `_golfShowShare(score, s, hostId)`, `golfMakeLink(nick, score)`, `golfParseLink(search)`, `_golfLinkBoot`.

- [ ] **Step 1: 테스트** `tools/tests/golf-guest.test.mjs` — dodge-guest.test.mjs 를 복사해 `DODGE`→`GOLF`, `dodgeParseLink`→`golfParseLink`, `dodgeMakeLink`→`golfMakeLink`, `game=dodge`→`game=golf`, 상한 `GOLF.MAX_SCORE`(999) 로 바꾼다. 실행하면 FAIL.
- [ ] **Step 2: 구현**

```js
window.GOLF_GUEST_KEY = 'murpy_golf_guest';
window.golfGuestLoad = function () { try { return JSON.parse(localStorage.getItem(window.GOLF_GUEST_KEY) || 'null'); } catch (e) { return null; } };
window.golfGuestSave = function (o) { try { localStorage.setItem(window.GOLF_GUEST_KEY, JSON.stringify(o)); } catch (e) {} };
window.golfGuestClear = function () { try { localStorage.removeItem(window.GOLF_GUEST_KEY); } catch (e) {} };
window.golfMakeLink = function (nick, score) { return 'https://murpy.app/?game=golf&s=' + (Math.max(0, Math.min(window.GOLF.MAX_SCORE, Math.floor(score || 0)))) + '&nick=' + encodeURIComponent(String(nick || '').slice(0, 12)); };
window.golfParseLink = function (search) {
  const q = new URLSearchParams(search || ''); if (q.get('game') !== 'golf') return { on: false, nick: '', score: 0 };
  const n = parseInt(q.get('s') || '0', 10); return { on: true, nick: String(q.get('nick') || '').slice(0, 12), score: Math.max(0, Math.min(window.GOLF.MAX_SCORE, isNaN(n) ? 0 : n)) };
};
window.golfSave = async function (score, sec, s) {
  const user = auth.currentUser || window.currentUser;
  const n = Math.max(0, Math.min(window.GOLF.MAX_SCORE, Math.floor(score || 0)));
  const rec = { s: n, t: Math.max(0, Math.floor(sec || 0)), lv: s.lv, ch: s.ch, holes: s.strokes.slice(0, 3), at: Date.now() };
  if (!user) { const merged = window.dodgeGuestMerge(window.golfGuestLoad(), rec, window.GOLF.RECS_MAX); window.golfGuestSave(merged); window._golfBest = Math.max(window._golfBest || 0, merged.best || 0); return; }
  try {
    const ref = doc(db, 'users', user.uid); const snap = await getDoc(ref);
    const cur = ((snap.exists() && snap.data().games) || {}).golf || {};
    const upd = { 'games.golf.plays': increment(1), 'games.golf.lastAt': Date.now() };
    window._golfBest = Math.max(window._golfBest || 0, cur.best || 0, n);
    if (n > (cur.best || 0)) upd['games.golf.best'] = n;
    const recs = [rec].concat(Array.isArray(cur.recent) ? cur.recent : []).slice(0, window.GOLF.RECS_MAX);
    upd['games.golf.recent'] = recs; window._golfRecs = recs;
    await updateDoc(ref, upd); window._hofCache = null;
    window.track && window.track('game_end', { game: 'golf', score: n, lv: s.lv, ch: s.ch });
  } catch (e) { console.warn('golfSave', e); }
};
window.golfGuestPromote = async function () {
  const user = auth.currentUser || window.currentUser; if (!user) return false;
  const g = window.golfGuestLoad(); if (!g || !(g.best > 0)) { window.golfGuestClear(); return false; }
  try {
    const ref = doc(db, 'users', user.uid); const snap = await getDoc(ref);
    const cur = ((snap.exists() && snap.data().games) || {}).golf || {};
    const recs = (Array.isArray(g.recent) ? g.recent : []).concat(Array.isArray(cur.recent) ? cur.recent : []).sort(function (a, b) { return b.at - a.at; }).slice(0, window.GOLF.RECS_MAX);
    const upd = { 'games.golf.recent': recs, 'games.golf.plays': increment(g.plays || 0), 'games.golf.lastAt': Date.now() };
    if ((g.best || 0) > (cur.best || 0)) upd['games.golf.best'] = g.best;
    await updateDoc(ref, upd); window.golfGuestClear(); window._hofCache = null; showToast('골프 기록을 옮겼어요'); return true;
  } catch (e) { console.warn('golfGuestPromote', e); return false; }
};
window.golfRecs = async function () {
  window._golfShowPane('golf-pane-recs');
  const box = document.getElementById('golf-rec-list'); if (!box) return;
  let recs = window._golfRecs;
  if (!recs) { const user = auth.currentUser || window.currentUser;
    if (user) { try { const sn = await getDoc(doc(db, 'users', user.uid)); recs = (((sn.exists() && sn.data().games) || {}).golf || {}).recent || []; } catch (e) { recs = []; } }
    else recs = (window.golfGuestLoad() || {}).recent || [];
    window._golfRecs = recs; }
  if (!recs.length) { box.innerHTML = '<div style="padding:20px;color:rgba(255,255,255,.4);font-size:12.5px;text-align:center">아직 기록이 없어요</div>'; return; }
  box.innerHTML = recs.map(function (r, i) {
    const d = new Date(r.at || 0), lv = (window.GOLF_LV[r.lv] || {}).name || '중', ch = (window.GOLF_CHARS[r.ch] || {}).name || '';
    return '<div style="display:flex;align-items:center;gap:10px;padding:9px 4px;border-bottom:1px solid rgba(255,255,255,.07)">'
      + '<div style="font-family:\'Galmuri14\',sans-serif;font-size:19px;color:#fff;min-width:54px">' + r.s + '</div>'
      + '<div style="flex:1;font-size:11px;color:rgba(255,255,255,.55)">' + lv + ' · ' + ch + ' · ' + (Array.isArray(r.holes) ? r.holes.join('/') + '타' : '') + ' · ' + (d.getMonth() + 1) + '/' + d.getDate() + '</div>'
      + '<button onclick="window.golfShareRec(' + i + ')" style="background:none;border:1px solid rgba(255,255,255,.2);color:#cfd6e6;font-family:inherit;font-size:11px;padding:5px 9px;cursor:pointer">공유</button></div>';
  }).join('');
};
window.golfShareRec = function (i) { const r = (window._golfRecs || [])[i]; if (!r) return; window._golfShowShare(r.s, { lv: r.lv, ch: r.ch, strokes: r.holes || [] }, 'golf-rec-share'); };
// 공유 카드 1080×1350 — dodge 카드와 같은 문법(타이틀 그림 + 닉 + 점수 + 하단 문구)
window._golfCardImg = function (score, s, cb) {
  const W = 1080, H = 1350, cv = document.createElement('canvas'); cv.width = W; cv.height = H; const x = cv.getContext('2d');
  const im = new Image();
  const draw = function (ok) {
    x.fillStyle = '#0e2412'; x.fillRect(0, 0, W, H);
    if (ok) { const r = Math.max(W / im.width, H / im.height); x.drawImage(im, (W - im.width * r) / 2, 0, im.width * r, im.height * r); }
    const g = x.createLinearGradient(0, H * 0.45, 0, H); g.addColorStop(0, 'rgba(5,7,12,0)'); g.addColorStop(1, 'rgba(5,7,12,.92)'); x.fillStyle = g; x.fillRect(0, 0, W, H);
    x.textAlign = 'center'; x.fillStyle = '#fff';
    const nick = window.dodgeNickGet ? window.dodgeNickGet() : (window._mwMyNick || '머피');
    x.font = '42px Galmuri11, sans-serif'; x.fillText(nick, W / 2, H - 470);
    x.font = '150px Galmuri14, sans-serif'; x.fillText(String(score), W / 2, H - 300);
    x.fillStyle = '#F5C24B'; x.font = '48px Galmuri14, sans-serif'; x.fillText('점', W / 2 + x.measureText(String(score)).width / 2 + 40, H - 300);
    x.fillStyle = '#cfd6e6'; x.font = '40px Galmuri11, sans-serif';
    const lv = (window.GOLF_LV[s.lv] || {}).name || '중', ch = (window.GOLF_CHARS[s.ch] || {}).name || '';
    x.fillText('3홀 · ' + (s.strokes || []).join('/') + '타 · 난이도 ' + lv + (ch ? ' · ' + ch : ''), W / 2, H - 220);
    x.fillStyle = 'rgba(255,255,255,.55)'; x.font = '36px Galmuri11, sans-serif'; x.fillText('골프 스윙 · murpy.app', W / 2, H - 110);
    cb(cv.toDataURL('image/jpeg', 0.9));
  };
  im.onload = function () { draw(true); }; im.onerror = function () { draw(false); }; im.src = 'char/game/golf_title.png?v=1';
};
window._golfShowShare = function (score, s, hostId) {
  const host = document.getElementById(hostId || 'golf-share'); if (!host) return;
  const user = auth.currentUser || window.currentUser; const formal = !!(user && !user.isAnonymous);
  if (hostId !== 'golf-rec-share' && !formal && !window._golfShared) { host.innerHTML = ''; window._golfRefreshKeep && window._golfRefreshKeep(); return; }
  window._golfCardImg(score, s, function (data) {
    window._mwStampData = data;
    const nick = window.dodgeNickGet ? window.dodgeNickGet() : (window._mwMyNick || '머피');
    window._mwShareMeta = { title: '골프 스윙 ' + score + '점', desc: nick + '님의 기록 · 머피에서 도전해 보세요', btn: '나도 치러 가기', link: window.golfMakeLink(nick, score) };
    host.innerHTML = window._dodgeShareBtnsHtml ? window._dodgeShareBtnsHtml('golf') : '';
    if (window._mwKakaoPrep) window._mwKakaoPrep();
  });
};
window._golfLinkBoot = function () {
  const r = window.golfParseLink(location.search); if (!r.on) return;
  window._golfFromLink = true;
  try { history.replaceState(null, '', location.pathname); } catch (e) {}
  const orig = window.showSplashOnboarding;
  if (typeof orig === 'function' && !orig._golfWrapped) { const w = function () { const gs = document.getElementById('golf-screen'); if (gs && gs.style.display !== 'none') { window._golfObPending = function () { orig.apply(window, arguments); }; return; } return orig.apply(window, arguments); }; w._golfWrapped = 1; window.showSplashOnboarding = w; }
  window.dismissLanding && window.dismissLanding();
  window.golfOpen();
  const c = document.getElementById('golf-challenge'); if (c && r.nick) { c.style.display = ''; c.textContent = r.nick + '님이 ' + r.score + '점으로 도전장을 보냈어요'; }
};
window.addEventListener('load', function () { setTimeout(window._golfLinkBoot, 0); });
```
  - `_dodgeShareBtnsHtml` 이 없으면(공유 버튼 HTML 이 `_dodgeShowShare` 안에 인라인이면) 그 HTML 을 `window._dodgeShareBtnsHtml = function (game) {…}` 로 뽑아 dodge·golf 가 같이 쓰게 한다(인스타 = 링크 복사 후 `mwShareSheet`, 카톡 = `mwShareKakao(this)` + `id="golf-kkbtn"`, 저장 = `mwSaveStamp`).
  - `_golfRefreshKeep` = dodge `_dodgeRefreshKeep` 복제(게스트 닉 입력 → `dodgeNickSave` → `_golfShared=true` → `_golfShowShare` 재호출; 그 뒤 "기록 남기고 내 랭킹 확인하기" → `openModal('login-method-modal')`).
- [ ] **Step 3: 훅 3곳** — `HOF_KINDS` 에 `golf: { label: '골프', unit: '점', game: '골프 스윙', get: function (u) { const n = ((u.games || {}).golf || {}).best || 0; return n > 0 && n <= 999 ? n : 0; } }`; `onAuthStateChanged` 의 `dodgeGuestPromote` 옆에 `window.golfGuestPromote && window.golfGuestPromote();`; 게스트 닉 시트 억제 `_dodgeFromLink` 조건에 `|| window._golfFromLink`; 월요일 팝업 회전 배열에 `'golf'` 추가(있다면).
- [ ] **Step 4: 테스트·문법** — `node tools/tests/golf-guest.test.mjs` OK, 문법 2종 OK. 브라우저: 한 판 → 결과 → 공유 카드 이미지 뜸 → 내 기록 → 명예의 전당 골프 탭.
- [ ] **Step 5: 커밋** — `"골프 스윙: 기록·게스트·공유 카드·링크·명예의 전당"`

---

### Task 6: 배포 + 실기기 확인 + 메모리

- [ ] **Step 1:** `node tools/module-syntax-check.mjs && node tools/dogam-syntax-check.mjs && node tools/tests/golf-core.test.mjs && node tools/tests/golf-guest.test.mjs`
- [ ] **Step 2:** `node tools/bump-version.mjs <다음번호>` → `python tools/check_version.py` → `git add index.html sw.js version.txt tools/tests/golf-*.test.mjs && git commit -m "골프 스윙 미니게임 (v<N>)" && git push`
- [ ] **Step 3:** 대표 폰 확인 목록(스펙 §8): 화면 꽉 참·당김 감도·홀인 손맛·선수 장 잠금·명예의 전당·공유·게스트 링크. 에셋(`golf_bg.jpg` 등) 이 들어오면 `char/game/` 에 넣고 캐시버스터 `?v=` 올려 재배포.
- [ ] **Step 4:** 메모리 `project_murpy_session_resume` 에 배포 버전·남은 확인 항목 기록.
