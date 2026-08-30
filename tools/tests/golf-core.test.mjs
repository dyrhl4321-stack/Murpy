// 골프 스윙 — 순수 로직 테스트 (index.html 에서 추출해 검증) · 8-30 팡야식(게이지·비행) 기준
// 실행: node tools/tests/golf-core.test.mjs
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';
const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
function grab(re, name) { const m = src.match(re); assert(m, `index.html에서 ${name}를 찾지 못함`); return m[0]; }
const w = {};
for (const [re, name] of [
  [/window\.GOLF = \{[\s\S]*?\n\};/, 'GOLF'], [/window\.GOLF_LV = \{[\s\S]*?\n\};/, 'GOLF_LV'], [/window\.GOLF_HOLES = \[[\s\S]*?\n\];/, 'GOLF_HOLES'],
  [/window\.GOLF_CHARS = \{[\s\S]*?\n\};/, 'GOLF_CHARS'], [/window\._golfRnd = function[\s\S]*?\n\};/, '_golfRnd'], [/window\.golfHoleScore = function[\s\S]*?\n\};/, 'golfHoleScore'],
  [/window\._golfWindFor = function[\s\S]*?\n\};/, '_golfWindFor'], [/window\._golfVillainsFor = function[\s\S]*?\n\};/, '_golfVillainsFor'], [/window\._golfMoleUp = function[\s\S]*?\n\};/, '_golfMoleUp'],
  [/window\.golfNew = function[\s\S]*?\n\};/, 'golfNew'], [/window\.GOLF_CLUBS = \{[\s\S]*?\n\};/, 'GOLF_CLUBS'],
  [/window\.GOLF\.G = [^\n]*\n(?:window\.GOLF\.[A-Z_]+ = [^\n]*\n)+/, 'GOLF 추가 상수'],
  [/window\._golfAimAngle = function[\s\S]*?\n\};/, '_golfAimAngle'], [/window\._golfSuggestClub = function[\s\S]*?\n\};/, '_golfSuggestClub'],
  [/window\.golfShot = function[\s\S]*?\n\};/, 'golfShot'], [/window\._golfInEllipse = function[\s\S]*?\n\};/, '_golfInEllipse'],
  [/window\.golfTick = function[\s\S]*?\n\};/, 'golfTick'], [/window\._golfCrowRepos = function[\s\S]*?\n\};/, '_golfCrowRepos'], [/window\._golfPenalty = function[\s\S]*?\n\};/, '_golfPenalty'],
  [/window\._golfNextHole = function[\s\S]*?\n\};/, '_golfNextHole'], [/window\.golfTotal = function[\s\S]*?\n\};/, 'golfTotal']
]) new Function('window', grab(re, name))(w);

const run = (s, ms) => { for (let t = 0; t < ms; t += 16) w.golfTick(s, 16); return s; };
const calm = (s) => { s.wind = { x: 0, y: 0 }; s.crow = null; s.mole = null; return s; };
const dist = (s, H) => Math.hypot(s.x - H.x, s.y - H.y);

// 1) 점수표
assert.strictEqual(w.golfHoleScore(3, 1), 50); assert.strictEqual(w.golfHoleScore(3, 3), 30); assert.strictEqual(w.golfHoleScore(3, 6), 0);

// 2) 새 판: 티에 있고 홀 1 은 멀어서 드라이버 권장
let s = calm(w.golfNew(7, 'mid', 'human'));
assert.strictEqual(s.hole, 0); assert.strictEqual(s.club, 'driver'); assert.strictEqual(s.z, 0);

// 3) 풀파워 드라이버 정확 샷: 공이 뜨고(z>0) 홀 쪽(-y)으로 가서 착지 후 멈춘다. 비거리는 dist 근처
assert(w.golfShot(s, 1, 0, 'driver')); assert(s.z > 0 && s.vy < 0, '떠서 위로 가야 한다');
assert.strictEqual(w.golfShot(s, 1, 0), false, '날아가는 중엔 샷 불가');
run(s, 9000); assert(!s.moving && s.z === 0, '9초면 멈추고 땅에');
const flew = w.GOLF.TEE_Y - s.y;
assert(flew > 38 && flew < 64, '드라이버 풀파워 비거리(굴림 포함)가 이상하다: ' + flew.toFixed(1));

// 4) 세기 절반이면 덜 간다
let s2 = calm(w.golfNew(7, 'mid', 'human')); w.golfShot(s2, 0.5, 0, 'driver'); run(s2, 9000);
assert(w.GOLF.TEE_Y - s2.y < flew * 0.8, '세기 0.5 가 풀파워만큼 간다');

// 5) 정확 실패(acc 1)면 옆으로 휜다, 정확 성공이면 직진
let s3 = calm(w.golfNew(7, 'mid', 'human')); w.golfShot(s3, 0.7, 1, 'driver'); run(s3, 9000);
assert(Math.abs(s3.x - 50) > 3, '슬라이스가 안 휜다 (x=' + s3.x.toFixed(1) + ')');
let s4 = calm(w.golfNew(7, 'mid', 'human')); w.golfShot(s4, 0.7, 0, 'driver'); run(s4, 9000);
assert(Math.abs(s4.x - 50) < 0.5, '정확 샷이 휜다 (x=' + s4.x.toFixed(2) + ')');

// 6) 퍼터는 안 뜬다 · 홀 6 앞에서 살살 치면 홀인 → 다음 홀 + 카메라용 티 복귀
s = calm(w.golfNew(5, 'easy', 'human')); const H0 = w.GOLF_HOLES[0]; s.x = H0.x; s.y = H0.y + 6; s.club = 'putter';
assert.strictEqual(w._golfSuggestClub(s), 'putter');
w.golfShot(s, 0.28, 0, 'putter'); assert.strictEqual(s.z, 0, '퍼터가 떴다');
run(s, 6000);
assert.strictEqual(s.hole, 1, '홀인 후 다음 홀 (last=' + s.last + ' d=' + dist(s, H0).toFixed(2) + ')');
assert.strictEqual(s.strokes[0], 1); assert.strictEqual(s.y, w.GOLF.TEE_Y);

// 7) 홀을 지나쳐도 다음 샷은 홀 방향(조준각이 홀을 향한다) — "하늘에서 아래로 쏘는" 일이 없다
s = calm(w.golfNew(5, 'easy', 'human')); s.x = 50; s.y = 10;   // 홀(50,22) 보다 위
const ang = w._golfAimAngle(s); assert(Math.sin(ang) > 0.9, '홀이 아래에 있으면 조준각도 아래(+y)여야 한다');

// 8) 파워 특성: 헬토리가 더 멀리 (같은 세기·정확)
const a = calm(w.golfNew(3, 'easy', 'human')), b = calm(w.golfNew(3, 'easy', 'heltori'));
w.golfShot(a, 0.5, 0, 'iron'); w.golfShot(b, 0.5, 0, 'iron'); run(a, 9000); run(b, 9000);
assert(b.y < a.y, '헬토리(파워 1.25)가 더 멀리 (a=' + a.y.toFixed(1) + ' b=' + b.y.toFixed(1) + ')');

// 9) 바람: 뚱뚱이는 덜 밀린다 (공중에서 바람 ×2.2)
const c = w.golfNew(11, 'hard', 'human'), d = w.golfNew(11, 'hard', 'ddungddung');
c.crow = null; c.mole = null; d.crow = null; d.mole = null; c.wind = { x: 0.004, y: 0 }; d.wind = { x: 0.004, y: 0 };
w.golfShot(c, 0.4, 0, 'iron'); w.golfShot(d, 0.4, 0, 'iron'); run(c, 9000); run(d, 9000);
assert(Math.abs(d.x - 50) < Math.abs(c.x - 50), '뚱뚱이가 바람에 덜 밀린다 (human x=' + c.x.toFixed(1) + ' ddung x=' + d.x.toFixed(1) + ')');

// 10) OB 벌타 + 복귀 — 홀 8 앞에서 풀파워 드라이버를 치면 홀을 한참 넘어 코스 밖(y<1)
s = calm(w.golfNew(5, 'easy', 'human')); s.x = 50; s.y = 24;   // 8-30 코스가 홀 뒤 -20 까지 연장됨(홀 앞에서 풀파워 → -37)
w.golfShot(s, 1, 0, 'driver'); run(s, 9000);
assert.strictEqual(s.last, 'ob', 'OB 가 안 났다 (y=' + s.y.toFixed(1) + ')'); assert.strictEqual(s.strokes[0], 2); assert.strictEqual(s.y, 24, '샷 전 자리로 복귀');

// 11) 좀비 멀리건: 첫 OB 는 벌타 없음
s = calm(w.golfNew(5, 'easy', 'zombie')); s.x = 50; s.y = 24;
w.golfShot(s, 1, 0, 'driver'); run(s, 9000); assert.strictEqual(s.strokes[0], 1, '멀리건'); assert.strictEqual(s.mulligan, 0);
w.golfShot(s, 1, 0, 'driver'); run(s, 9000); assert.strictEqual(s.strokes[0], 3, '두 번째부터 벌타');

// 12) 타수 상한(상 = 5)이면 다음 홀 · 총점 배율
s = calm(w.golfNew(5, 'hard', 'human'));
const mx = w.GOLF_LV.hard.maxStrokes || w.GOLF.MAX_STROKES;
for (let i = 0; i < mx; i++) { w.golfShot(s, 0.06, 0, 'putter'); run(s, 3000); calm(s); }
assert.strictEqual(s.hole, 1, '타수 상한이면 다음 홀 (strokes=' + s.strokes[0] + ')');
s.strokes = [1, 3, 4]; s.hole = 3; s.done = true;
assert.strictEqual(w.golfTotal(s), Math.round((50 + 30 + 20) * w.GOLF_LV.hard.mul));

// 13) 빠른 공은 컵을 스치고 지나간다(한 방 홀인 버그 방지)
s = calm(w.golfNew(5, 'easy', 'human')); s.x = H0.x; s.y = H0.y + 6;
w.golfShot(s, 1, 0, 'putter'); run(s, 200); assert.strictEqual(s.hole, 0, '세게 친 퍼팅이 홀인되면 안 된다 (last=' + s.last + ')');

// 14) 빌런: 하 없음 · 중 까마귀 · 상 둘 다. 까마귀는 공이 멈춰 있어도 움직인다
assert.strictEqual(w.golfNew(1, 'easy', 'human').crow, null);
const md = w.golfNew(1, 'mid', 'human'); assert.strictEqual(md.crow, null, '중은 1홀엔 까마귀 없음(8-30)'); md.hole = 1; w._golfVillainsFor(md); assert(md.crow, '중 2홀부터 까마귀');
const hd = w.golfNew(1, 'hard', 'human'); assert(hd.crow && hd.mole);
const cx0 = hd.crow.x; run(hd, 500); assert(hd.crow.x !== cx0, '까마귀가 안 움직인다');
console.log('golf-core: OK');
