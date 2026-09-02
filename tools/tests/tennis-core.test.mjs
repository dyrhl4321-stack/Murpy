// 머피 테니스 — 판정·물리 순수 로직 테스트 (index.html 에서 추출해 검증) · 9-02
// 실행: node tools/tests/tennis-core.test.mjs
//
// ★왜 있나: 이 게임은 대표가 자는 사이 만들어져 아침에 처음 켜진다.
//   "쳤는데 안 맞는다 / 안 쳤는데 넘어간다" 류는 폰으로 한 판 돌려도 원인을 못 찾는다.
//   무궁화꽃(_sqMgJudge)이 같은 이유로 테스트를 붙였다 — 그 방식을 따른다.
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
  [/window\.tennisScore = function[\s\S]*?\n\};/, 'tennisScore'],
  [/window\._tennisHit = function[\s\S]*?\n\};/, '_tennisHit'],
  [/window\._tennisReturn = function[\s\S]*?\n\};/, '_tennisReturn'],
  [/window\._tennisServe = function[\s\S]*?\n\};/, '_tennisServe'],
  [/window\.tennisTick = function[\s\S]*?\n\};/, 'tennisTick'],
]) new Function('window', grab(re, name))(w);

const T = w.TENNIS;
const MID = (T.ZONE_Y0 + T.ZONE_Y1) / 2;
const HALF = (T.ZONE_Y1 - T.ZONE_Y0) / 2;
// 내 쪽으로 오는 공을, 캐릭터가 닿는 자리에, 존 한가운데에 놓는다
function ready(lv) {
  const s = w.tennisNew(lv || 'mid');
  s.toMe = true; s.by = MID; s.bx = 50; s.mx = 50;
  return s;
}
let n = 0;
const ok = (msg) => { n++; };

// 1) 새 판의 초기값
let s = w.tennisNew('mid');
assert.strictEqual(s.pts, 0, '시작 점수는 0이어야');
assert.strictEqual(s.lives, T.LIVES, '목숨이 상수와 달라');
assert.strictEqual(s.rally, 0, '랠리 0에서 시작해야');
assert.strictEqual(s.over, false, '시작하자마자 끝나면 안 된다');
assert.strictEqual(w.tennisNew('없는난이도').lv, 'mid', '모르는 난이도는 중으로 떨어져야');
ok();

// 2) 존 한가운데 + 캐릭터가 공 앞 = 맞는다. perfect 는 1
let r = w._tennisJudge(ready(), 50);
assert.strictEqual(r.result, 'hit', '한가운데인데 안 맞았다');
assert(r.perfect > 0.99, 'perfect 가 1 이어야: ' + r.perfect);
ok();

// 3) 순수 함수다 — 판정이 상태를 바꾸지 않는다
const s3 = ready(); const snap = JSON.stringify(s3);
w._tennisJudge(s3, 20);
assert.strictEqual(JSON.stringify(s3), snap, '_tennisJudge 가 상태를 바꿨다');
ok();

// 4) 너무 이르다 / 너무 늦다
const early = ready(); early.by = MID - HALF - 3;
assert.strictEqual(w._tennisJudge(early, 50).result, 'early', '존 앞인데 early 가 아니다');
const late = ready(); late.by = MID + HALF + 3;
assert.strictEqual(w._tennisJudge(late, 50).result, 'late', '존 뒤인데 late 가 아니다');
ok();

// 5) 캐릭터가 공에서 멀면 못 닿는다
const far = ready(); far.mx = 50 + T.REACH + 2;
assert.strictEqual(w._tennisJudge(far, 50).result, 'reach', '멀리 있는데 쳤다');
const near = ready(); near.mx = 50 + T.REACH - 1;
assert.strictEqual(w._tennisJudge(near, 50).result, 'hit', '닿는 거리인데 못 쳤다');
ok();

// 6) 탭한 x 가 그대로 코스가 된다(완벽하게 받았을 때)
assert(Math.abs(w._tennisJudge(ready(), 20).course - 20) < 0.01, '왼쪽을 탭했는데 코스가 다르다');
assert(Math.abs(w._tennisJudge(ready(), 80).course - 80) < 0.01, '오른쪽을 탭했는데 코스가 다르다');
ok();

// 7) 라인 밖을 노리면 아웃
assert.strictEqual(w._tennisJudge(ready(), T.SIDE_MIN - 3).result, 'out', '왼쪽 라인 밖인데 아웃이 아니다');
assert.strictEqual(w._tennisJudge(ready(), T.SIDE_MAX + 3).result, 'out', '오른쪽 라인 밖인데 아웃이 아니다');
ok();

// 8) 아슬아슬하게 받으면 코스가 **공이 온 쪽**으로 밀린다 (결정적 — 난수 없음)
const edge = ready(); edge.by = MID + HALF * 0.9; edge.bx = 10; edge.mx = 10;
const e1 = w._tennisJudge(edge, 50);
assert(e1.perfect < 0.2, '가장자리인데 perfect 가 높다: ' + e1.perfect);
assert(e1.course < 50, '급하게 받았으면 공이 온 쪽(왼쪽)으로 밀려야: ' + e1.course);
const edge2 = ready(); edge2.by = edge.by; edge2.bx = 90; edge2.mx = 90;
assert(w._tennisJudge(edge2, 50).course > 50, '오른쪽에서 온 공은 오른쪽으로 밀려야');
// 같은 입력이면 늘 같은 결과 — 난수가 섞이지 않았음을 못박는다
assert.strictEqual(w._tennisJudge(edge, 50).course, e1.course, '같은 상황인데 결과가 달라졌다(난수가 섞였다)');
ok();

// 9) 난이도가 높을수록 존이 좁다
assert(w.TENNIS_LV.easy.zone > w.TENNIS_LV.mid.zone && w.TENNIS_LV.mid.zone > w.TENNIS_LV.hard.zone,
  '난이도별 존 배율이 하>중>상 이 아니다');
const hardEdge = ready('hard'); hardEdge.by = MID + HALF * 0.9;
assert.notStrictEqual(w._tennisJudge(hardEdge, 50).result, 'hit', '상 난이도에서 같은 위치가 맞으면 안 된다');
const easyEdge = ready('easy'); easyEdge.by = MID + HALF * 1.2;
assert.strictEqual(w._tennisJudge(easyEdge, 50).result, 'hit', '하 난이도는 더 넓게 받아줘야 한다');
ok();

// 10) 내 쪽으로 오는 공이 아니면 판정하지 않는다
const notMine = ready(); notMine.toMe = false;
assert.strictEqual(w._tennisJudge(notMine, 50).result, 'idle', '상대 코트 공인데 판정했다');
const done = ready(); done.over = true;
assert.strictEqual(w._tennisJudge(done, 50).result, 'idle', '끝난 판인데 판정했다');
ok();

// 11) 틱: 공이 움직인다
const t1 = ready(); const y0 = t1.by; w.tennisTick(t1, 16);
assert.notStrictEqual(t1.by, y0, '틱을 돌렸는데 공이 그대로다');
ok();

// 12) 틱: 안 치고 지나가면 실점하고 랠리가 끊긴다
const miss = ready(); miss.rally = 5;
for (let i = 0; i < 400 && miss.lives === T.LIVES; i++) w.tennisTick(miss, 16);
assert.strictEqual(miss.lives, T.LIVES - 1, '놓쳤는데 실점하지 않았다');
assert.strictEqual(miss.rally, 0, '실점했는데 랠리가 안 끊겼다');
ok();

// 13) 목숨이 다하면 끝난다
const dead = ready(); dead.lives = 1;
for (let i = 0; i < 600 && !dead.over; i++) w.tennisTick(dead, 16);
assert.strictEqual(dead.over, true, '목숨이 0인데 안 끝났다');
const before = JSON.stringify(dead); w.tennisTick(dead, 16);
assert.strictEqual(JSON.stringify(dead), before, '끝난 판인데 틱이 상태를 더 바꿨다');
ok();

// 14) 받아치면 공이 상대 쪽으로 간다 + 랠리가 오른다
const hit = ready();
w._tennisHit(hit, w._tennisJudge(hit, 30));
assert.strictEqual(hit.toMe, false, '받아쳤는데 아직 내 공이다');
assert.strictEqual(hit.rally, 1, '받아쳤는데 랠리가 안 올랐다');
const hy = hit.by; w.tennisTick(hit, 16);
assert(hit.by < hy, '상대 쪽으로 가야 하는데 y 가 안 줄었다');
ok();

// 15) 랠리가 길어지면 공이 빨라지되 상한을 넘지 않는다
const fast = ready(); fast.rally = 200;
w._tennisHit(fast, w._tennisJudge(fast, 50));
assert(fast.vy <= T.V_MAX + 1e-9, '공 속도가 상한을 넘었다: ' + fast.vy);
const slow = ready(); slow.rally = 0;
const slowJ = w._tennisJudge(slow, 50); w._tennisHit(slow, slowJ);
assert(slow.vy < fast.vy, '랠리가 길수록 빨라져야 한다');
ok();

// 16) 상대는 **내가 있는 반대쪽**으로 보낸다
const retL = ready(); retL.mx = 20; retL.bx = 50; w._tennisReturn(retL);
assert(retL.vx > 0, '내가 왼쪽인데 공이 왼쪽으로 온다');
const retR = ready(); retR.mx = 80; retR.bx = 50; w._tennisReturn(retR);
assert(retR.vx < 0, '내가 오른쪽인데 공이 오른쪽으로 온다');
ok();

// 17) 상대가 못 닿으면 내 득점
const pt = ready();
pt.toMe = false; pt.by = T.OP_BASE + 7; pt.bx = 90; pt.ox = 20; pt.vy = 1;
for (let i = 0; i < 60 && pt.pts === 0; i++) w.tennisTick(pt, 16);
assert.strictEqual(pt.pts, 1, '상대가 멀리 있는데 득점하지 못했다');
ok();

// 18) 점수식 — 득점 100, 최장 랠리 10, 난이도 배율
const sc = w.tennisNew('hard'); sc.pts = 3; sc.bestRally = 7;
assert.strictEqual(w.tennisScore(sc), Math.round((3 * T.PT_SCORE + 7 * T.RALLY_SCORE) * w.TENNIS_LV.hard.mul),
  '점수식이 스펙과 다르다');
const sc0 = w.tennisNew('mid');
assert.strictEqual(w.tennisScore(sc0), 0, '아무것도 안 했는데 점수가 있다');
ok();

// 19) ★수동 이동 (9-02 대표: "자동이동이 아니라 수동이동으로") — 손을 떼면(mtx null) 안 움직인다
const still = ready(); still.by = T.NET_Y + 2; still.bx = 20; still.mx = 80; still.mtx = null;
w.tennisTick(still, 16);
assert.strictEqual(still.mx, 80, '손을 뗐는데 캐릭터가 움직였다(자동 이동이 남아 있다)');
ok();

// 20) 손가락을 대면(mtx) 그쪽으로 달린다 — 속도는 MY_V 를 넘지 않는다
const mv = ready(); mv.by = T.NET_Y + 2; mv.mx = 20; mv.mtx = 90;
w.tennisTick(mv, 16);
assert(mv.mx > 20, '이동 목표를 줬는데 안 움직인다');
assert(mv.mx - 20 <= T.MY_V + 1e-9, '한 틱에 MY_V 보다 많이 움직였다: ' + (mv.mx - 20));
for (let i = 0; i < 900 && Math.abs(mv.mx - 90) > 0.5; i++) w.tennisTick(mv, 16);
assert(Math.abs(mv.mx - 90) < 2, '목표까지 도착하지 못했다: ' + mv.mx);
ok();

// 21) 손가락을 대고 있으면 존에서 자동으로 받아친다(홀드 랠리) — 코스는 라인 안으로
const hold = ready(); hold.by = MID - HALF - 2; hold.mtx = 50; hold.mx = 50; hold.bx = 50; hold.vx = 0;
let swung = false;
for (let i = 0; i < 200; i++) { w.tennisTick(hold, 16); if (!hold.toMe) { swung = true; break; } }
assert(swung, '손가락을 대고 있는데 자동 스윙이 안 나갔다');
assert(hold.rally >= 1, '자동 스윙인데 랠리가 안 올랐다');
ok();

console.log('테니스 코어 테스트 ' + n + '묶음 통과');
