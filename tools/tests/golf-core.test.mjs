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
new Function('window', grab(/window\._golfWindFor = function[\s\S]*?\n\};/, '_golfWindFor'))(w);
new Function('window', grab(/window\._golfVillainsFor = function[\s\S]*?\n\};/, '_golfVillainsFor'))(w);
new Function('window', grab(/window\._golfMoleUp = function[\s\S]*?\n\};/, '_golfMoleUp'))(w);
new Function('window', grab(/window\.golfNew = function[\s\S]*?\n\};/, 'golfNew'))(w);
new Function('window', grab(/window\.golfShot = function[\s\S]*?\n\};/, 'golfShot'))(w);
new Function('window', grab(/window\._golfInEllipse = function[\s\S]*?\n\};/, '_golfInEllipse'))(w);
new Function('window', grab(/window\.golfTick = function[\s\S]*?\n\};/, 'golfTick'))(w);
new Function('window', grab(/window\._golfNextHole = function[\s\S]*?\n\};/, '_golfNextHole'))(w);
new Function('window', grab(/window\.golfTotal = function[\s\S]*?\n\};/, 'golfTotal'))(w);

const run = (s, ms) => { for (let t = 0; t < ms; t += 16) w.golfTick(s, 16); return s; };

// 1) 점수표
assert.strictEqual(w.golfHoleScore(3, 1), 50); assert.strictEqual(w.golfHoleScore(3, 3), 30);
assert.strictEqual(w.golfHoleScore(3, 6), 0);  assert.strictEqual(w.golfHoleScore(3, 9), 0);

// 2) 샷: 아래로 당기면 위로 간다, 세기는 DRAG_MAX 에서 상한
let s = w.golfNew(7, 'mid', 'human');
assert.strictEqual(s.hole, 0); assert.strictEqual(s.x, 50); assert.strictEqual(s.y, w.GOLF.TEE_Y);
w.golfShot(s, 0, 20);
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
w.golfShot(a, 0, 10); w.golfShot(b, 0, 10); run(a, 8000); run(b, 8000);   // 20 이면 헬토리가 OB 로 나가 버린다
assert(b.y < a.y, '헬토리(파워 1.25)가 더 멀리 (a=' + a.y.toFixed(1) + ' b=' + b.y.toFixed(1) + ')');

// 5) 바람: 뚱뚱이는 덜 밀린다
const c = w.golfNew(11, 'hard', 'human'), d = w.golfNew(11, 'hard', 'ddungddung');
c.wind = { x: 0.002, y: 0 }; d.wind = { x: 0.002, y: 0 };   // 0.01 이면 둘 다 OB 로 나가 같은 자리로 돌아온다
w.golfShot(c, 0, 5); w.golfShot(d, 0, 5); run(c, 8000); run(d, 8000);
assert(Math.abs(d.x - 50) < Math.abs(c.x - 50), '뚱뚱이가 바람에 덜 밀린다 (human x=' + c.x.toFixed(1) + ' ddung x=' + d.x.toFixed(1) + ')');

// 6) OB 벌타 + 복귀
s = w.golfNew(5, 'easy', 'human'); s.wind = { x: 0, y: 0 };
w.golfShot(s, 40, 0);
run(s, 8000);
assert.strictEqual(s.strokes[0], 2, 'OB 는 벌타 1');
assert.strictEqual(s.x, 50, '샷 전 자리로 복귀');
assert.strictEqual(s.last, 'ob');

// 7) 홀인: 홀 바로 앞에서 살짝 치면 들어간다 → 다음 홀
s = w.golfNew(5, 'easy', 'human'); s.wind = { x: 0, y: 0 };
const h = w.GOLF_HOLES[0]; s.x = h.x; s.y = h.y + 6;
w.golfShot(s, 0, 3.2); run(s, 6000);
assert.strictEqual(s.hole, 1, '홀인 후 다음 홀 (last=' + s.last + ', y=' + s.y.toFixed(2) + ')'); assert.strictEqual(s.last, 'in');
assert.strictEqual(s.strokes[0], 1); assert.strictEqual(s.x, 50); assert.strictEqual(s.y, w.GOLF.TEE_Y);

// 8) 좀비 멀리건: 첫 OB 는 벌타 없음
s = w.golfNew(5, 'easy', 'zombie'); s.wind = { x: 0, y: 0 };
w.golfShot(s, 40, 0); run(s, 8000);
assert.strictEqual(s.strokes[0], 1, '멀리건으로 벌타 없음'); assert.strictEqual(s.mulligan, 0);
w.golfShot(s, 40, 0); run(s, 8000);
assert.strictEqual(s.strokes[0], 3, '두 번째부터는 벌타');

// 9) 6타 상한: 홀을 못 넣어도 넘어간다 · 총점·배율
s = w.golfNew(5, 'hard', 'human'); s.wind = { x: 0, y: 0 };
const mx = w.GOLF_LV.hard.maxStrokes || w.GOLF.MAX_STROKES;   // 상은 홀당 5타(8-30 난이도 차별)
for (let i = 0; i < mx; i++) { w.golfShot(s, 0, 1.5); run(s, 3000); }   // 1 미만은 샷으로 안 친다
assert.strictEqual(s.hole, 1, '타수 상한이면 다음 홀'); assert.strictEqual(s.strokes[0], mx);
s.strokes = [1, 3, 4]; s.hole = 3; s.done = true;
assert.strictEqual(w.golfTotal(s), Math.round((50 + 30 + 20) * w.GOLF_LV.hard.mul));
// 10) ★빠른 공은 컵을 스치고 지나가야 한다 — 한 방에 홀인되던 버그(8-30). 홀 6 앞에서 세게 치면 홀인 아님
s = w.golfNew(5, 'easy', 'human'); s.wind = { x: 0, y: 0 }; s.crow = null; s.mole = null;
s.x = w.GOLF_HOLES[0].x; s.y = w.GOLF_HOLES[0].y + 6;
w.golfShot(s, 0, 38); run(s, 200);
assert.strictEqual(s.hole, 0, '세게 친 공이 홀인되면 안 된다 (last=' + s.last + ')');

// 11) 빌런: 하는 없음, 중은 까마귀, 상은 까마귀+두더지. 까마귀는 공이 멈춰 있어도 움직인다
assert.strictEqual(w.golfNew(1, 'easy', 'human').crow, null); assert(w.golfNew(1, 'mid', 'human').crow);
const hd = w.golfNew(1, 'hard', 'human'); assert(hd.crow && hd.mole);
const cx0 = hd.crow.x; run(hd, 500); assert(hd.crow.x !== cx0, '까마귀가 안 움직인다');

// 12) 까마귀에 맞으면 옆으로 밀린다
s = w.golfNew(9, 'mid', 'human'); s.wind = { x: 0, y: 0 };
s.crow = { x: 50, y: 78, dir: 1, hit: 0 }; s.x = 50; s.y = 80;   // 공 바로 앞 — 까마귀는 계속 움직이므로 멀리 두면 못 만난다
w.golfShot(s, 0, 4); run(s, 400);
assert(s.last === 'crow' || s.x > 50.5, '까마귀 충돌이 안 먹는다 (x=' + s.x.toFixed(2) + ' last=' + s.last + ')');
console.log('golf-core: OK');
