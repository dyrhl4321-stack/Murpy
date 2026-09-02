// 머피런 — 코어 물리·판정 테스트 (index.html 에서 추출해 검증) · 9-02
// 실행: node tools/tests/run-core.test.mjs
//
// ★왜 있나: 러너는 "점프했는데 맞았다 / 안 뛰었는데 죽었다"가 전부인 게임이다.
//   충돌 상자와 점프 높이의 관계가 틀어지면 폰에서는 원인을 못 찾는다. 여기서 못 박는다.
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
function grab(re, name) { const m = src.match(re); assert(m, `index.html에서 ${name}를 찾지 못함`); return m[0]; }

const w = {};
for (const [re, name] of [
  [/window\.RUN = \{[\s\S]*?\n\};/, 'RUN'],
  [/window\.RUN_OBS = \{[\s\S]*?\n\};/, 'RUN_OBS'],
  [/window\.RUN_LV = \{[\s\S]*?\n\};/, 'RUN_LV'],
  [/window\._runRng = function[\s\S]*?\n\};/, '_runRng'],
  [/window\.runNew = function[\s\S]*?\n\};/, 'runNew'],
  [/window\._runSpawn = function[\s\S]*?\n\};/, '_runSpawn'],
  [/window\._runHit = function[\s\S]*?\n\};/, '_runHit'],
  [/window\.runJump = function[\s\S]*?\n\};/, 'runJump'],
  [/window\.runRelease = function[\s\S]*?\n\};/, 'runRelease'],
  [/window\.runScore = function[\s\S]*?\n\};/, 'runScore'],
  [/window\.runMeters = function[\s\S]*?\n\};/, 'runMeters'],
  [/window\.runTick = function[\s\S]*?\n\};/, 'runTick'],
]) new Function('window', grab(re, name))(w);

const R = w.RUN;
let pass = 0;
function ok(name, fn) { fn(); pass++; console.log('  ✓ ' + name); }

// ── 1) 같은 시드는 같은 판 — 스폰 순서·위치·거리까지 그대로 ────────────────
ok('결정성: 같은 시드 = 같은 판', () => {
  const a = w.runNew('mid', 42), b = w.runNew('mid', 42);
  for (let i = 0; i < 400 && !a.over; i++) { w.runTick(a, 16); w.runTick(b, 16); }
  assert.strictEqual(a.over, b.over);
  assert.strictEqual(a.d.toFixed(6), b.d.toFixed(6));
  assert.deepStrictEqual(a.obs.map(o => o.t + '@' + o.x.toFixed(3)), b.obs.map(o => o.t + '@' + o.x.toFixed(3)));
});

// ── 2) 처음 두 장애물은 지상(허들/웅덩이) — 공중 장애물로 배우게 하지 않는다 ──
ok('첫 두 장애물은 지상', () => {
  for (const seed of [1, 7, 99, 12345]) {
    const s = w.runNew('mid', seed);
    w._runSpawn(s); w._runSpawn(s);
    assert(s.obs.every(o => o.t === 'h' || o.t === 'p'), `seed ${seed}: ${s.obs.map(o => o.t)}`);
  }
});

// ── 3) 점프 물리: 짧은 탭도 허들(y1=8)은 넘고, 길게 누르면 확실히 더 높다 ──
function apex(hold) {
  const s = w.runNew('mid', 1); s.nextAt = 1e9;      // 장애물 없이 물리만
  w.runJump(s); if (!hold) w.runRelease(s);
  let top = 0;
  for (let i = 0; i < 200 && s.air; i++) { w.runTick(s, 16); top = Math.max(top, s.z); }
  return top;
}
ok('점프 높이: 탭 > 허들, 홀드 > 탭', () => {
  const tap = apex(false), hold = apex(true);
  assert(tap > w.RUN_OBS.h.y1 + 1, `탭 정점 ${tap.toFixed(1)} 이 허들(${w.RUN_OBS.h.y1})을 못 넘는다`);
  assert(hold > tap + 4, `홀드 정점 ${hold.toFixed(1)} 이 탭(${tap.toFixed(1)})보다 충분히 높지 않다`);
  assert(hold < w.RUN_OBS.g.y0 + w.RUN.CH + 6, '홀드가 비정상적으로 높다');
});

// ── 4) 공중에서는 다시 못 뛴다(이단 점프 금지) ─────────────────────────────
ok('이단 점프 금지', () => {
  const s = w.runNew('mid', 1); s.nextAt = 1e9;
  assert.strictEqual(w.runJump(s), true);
  assert.strictEqual(w.runJump(s), false);
});

// ── 5) 충돌 상자: 허들은 땅에서 맞고 위로는 통과, 비둘기는 그 반대 ─────────
ok('허들: 땅에서 충돌 · 점프 정점에선 통과', () => {
  const s = w.runNew('mid', 1);
  const o = { t: 'h', x: s.d + 2 };
  assert(w._runHit(s, o), '땅에 서 있는데 허들에 안 맞는다');
  s.z = w.RUN_OBS.h.y1 + 0.5;
  assert(!w._runHit(s, o), '허들 위를 넘는데 맞는다');
});
ok('비둘기: 달리면 안전 · 뛰면 맞는다', () => {
  const s = w.runNew('mid', 1);
  const o = { t: 'g', x: s.d + 2 };
  assert(!w._runHit(s, o), '서서 달리는데 비둘기에 맞는다 (y0 가 캐릭터 키보다 낮다)');
  s.z = 12;
  assert(w._runHit(s, o), '점프 중인데 비둘기에 안 맞는다');
});

// ── 6) 충돌 = 종료, 하 난이도는 한 번 부활 + 무적 ──────────────────────────
ok('중 난이도: 충돌 즉시 종료', () => {
  const s = w.runNew('mid', 1); s.nextAt = 1e9;
  s.obs = [{ t: 'h', x: s.d + 1 }];
  const r = w.runTick(s, 16);
  assert.strictEqual(r, 'crash'); assert.strictEqual(s.over, true);
});
ok('하 난이도: 1회 부활 · 무적 · 두 번째는 끝', () => {
  const s = w.runNew('easy', 1); s.nextAt = 1e9;
  s.obs = [{ t: 'h', x: s.d + 1 }];
  assert.strictEqual(w.runTick(s, 16), 'revive');
  assert.strictEqual(s.over, false); assert.strictEqual(s.revives, 0); assert(s.inv > 0);
  assert.strictEqual(w.runTick(s, 16), '', '무적인데 또 걸렸다');
  s.inv = 0; s.obs = [{ t: 'h', x: s.d + 1 }];
  assert.strictEqual(w.runTick(s, 16), 'crash'); assert.strictEqual(s.over, true);
});

// ── 7) 점수 = 거리(m) × 난이도 배율, 상한 ─────────────────────────────────
ok('점수·거리 환산', () => {
  const s = w.runNew('hard', 1);
  s.d = 1000;                                        // 1000u = 200m
  assert.strictEqual(w.runMeters(s), 200);
  assert.strictEqual(w.runScore(s), Math.round(200 * w.RUN_LV.hard.mul));
  s.d = 1e9;
  assert.strictEqual(w.runScore(s), R.MAX_SCORE, '점수 상한이 안 걸린다');
});

// ── 8) 100m 마다 mile 이벤트가 정확히 한 번 ────────────────────────────────
ok('100m 이벤트', () => {
  const s = w.runNew('mid', 1); s.nextAt = 1e9;
  s.d = 499 / R.M_PER_U * R.M_PER_U;                 // 99.8m 근처
  s.d = 498;
  let miles = 0;
  for (let i = 0; i < 40; i++) { if (w.runTick(s, 16) === 'mile') miles++; }
  assert.strictEqual(miles, 1, `100m 이벤트가 ${miles}번 울렸다`);
});

// ── 9) 종료 뒤 틱은 아무것도 안 바꾼다 ─────────────────────────────────────
ok('종료 뒤 no-op', () => {
  const s = w.runNew('mid', 1); s.over = true; s.last = 'crash';
  const d = s.d;
  assert.strictEqual(w.runTick(s, 16), 'crash');
  assert.strictEqual(s.d, d);
});

// ── 10) 속도는 상한까지만 오른다 ───────────────────────────────────────────
ok('속도 상한', () => {
  const s = w.runNew('mid', 1); s.nextAt = 1e9;
  for (let i = 0; i < 8000 && !s.over; i++) w.runTick(s, 16);
  assert(s.v <= w.RUN_LV.mid.vmax + 1e-9, `속도 ${s.v} 가 상한을 넘었다`);
});

// ── 11) 마주 오는 장애물(비둘기·자전거)은 세계 x 가 줄어든다 ───────────────
ok('마주 오는 장애물 이동', () => {
  const s = w.runNew('mid', 1); s.nextAt = 1e9;
  s.obs = [{ t: 'b', x: s.d + 120 }, { t: 'h', x: s.d + 120 }];
  const bx = s.obs[0].x, hx = s.obs[1].x;
  w.runTick(s, 16);
  assert(s.obs[0].x < bx, '자전거가 안 온다');
  assert.strictEqual(s.obs[1].x, hx, '허들이 움직였다');
});

// ── 12) 프로틴: 먹으면 +1·점수 보너스·아이템 소멸 ──────────────────────────
ok('프로틴 먹기', () => {
  const s = w.runNew('mid', 1); s.nextAt = 1e9;
  s.items = [{ t: 'pr', x: s.d + 2, y: 6 }];
  assert.strictEqual(w.runTick(s, 16), 'prot');
  assert.strictEqual(s.prot, 1);
  assert.strictEqual(s.items.length, 0, '먹은 프로틴이 남아 있다');
  const base = Math.round(s.d * R.M_PER_U * w.RUN_LV.mid.mul);
  assert.strictEqual(w.runScore(s), base + R.PROT_PT, '프로틴 보너스가 점수에 없다');
});

// ── 13) 치킨: 감점 + 슬로우 + 연속 게이지 리셋, 점수는 0 아래로 안 내려간다 ──
ok('치킨의 유혹', () => {
  const s = w.runNew('mid', 1); s.nextAt = 1e9;
  s.protRun = 4;
  s.items = [{ t: 'ck', x: s.d + 2, y: 5 }];
  assert.strictEqual(w.runTick(s, 16), 'chick');
  assert(s.slow > 0, '치킨을 먹었는데 안 느려진다');
  assert.strictEqual(s.protRun, 0, '치킨이 연속 게이지를 안 끊는다');
  assert.strictEqual(w.runScore(s), 0, '초반 치킨인데 점수가 음수다');
  // 슬로우 동안 실제로 덜 나아간다
  const d0 = s.d; w.runTick(s, 16); const slowGain = s.d - d0;
  s.slow = 0; const d1 = s.d; w.runTick(s, 16); const normGain = s.d - d1;
  assert(slowGain < normGain * 0.7, `슬로우가 안 걸린다 (${slowGain.toFixed(3)} vs ${normGain.toFixed(3)})`);
});

// ── 14) 득근 타임: 6연속에 터지고, 도는 동안 장애물에 안 죽고 더 빠르다 ──
ok('득근 타임: 발동·무적·가속', () => {
  const s = w.runNew('mid', 1); s.nextAt = 1e9;
  s.protRun = R.PUMP_N - 1;
  s.items = [{ t: 'pr', x: s.d + 2, y: 6 }];
  assert.strictEqual(w.runTick(s, 16), 'pump');
  assert(s.pump > 0); assert.strictEqual(s.protRun, 0);
  s.obs = [{ t: 'h', x: s.d + 1 }];
  const r = w.runTick(s, 16);
  assert(r !== 'crash' && !s.over, '득근 타임인데 허들에 죽었다');
  const d0 = s.d; w.runTick(s, 16); const pumpGain = s.d - d0;
  s.pump = 0; s.obs = []; const d1 = s.d; w.runTick(s, 16); const normGain = s.d - d1;
  assert(pumpGain > normGain * 1.2, `득근 가속이 없다 (${pumpGain.toFixed(3)} vs ${normGain.toFixed(3)})`);
});

// ── 15) 아치 프로틴은 점프 궤적으로 전부 닿는 높이다 ───────────────────────
ok('아치 프로틴 도달 가능', () => {
  const s = w.runNew('mid', 5);
  for (let i = 0; i < 30; i++) w._runSpawn(s);
  const maxY = Math.max(0, ...s.items.map(it => it.y));
  const holdApex = apex(true);
  assert(maxY - R.ITEM_R < holdApex + R.CH, `아치 꼭대기(${maxY})가 홀드 점프(${holdApex.toFixed(1)}+키)로도 안 닿는다`);
});

console.log(`\n머피런 코어 ${pass}개 전부 통과`);
