// 무궁화꽃이 피었습니다 — 판정 로직 테스트 (index.html 에서 추출해 검증) · 9-02
// 실행: node tools/tests/mugung-core.test.mjs
//
// ★왜 있나: 이 게임은 대표가 자는 사이에 만들어 아침에 처음 켜진다.
//   판정이 틀린 채로 켜지면 "움직였는데 안 걸린다 / 가만히 있었는데 걸린다"가 되고,
//   그건 폰으로 한 판 돌려도 원인을 못 찾는 종류의 버그다. 여기서 막는다.
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
function grab(re, name) { const m = src.match(re); assert(m, `index.html에서 ${name}를 찾지 못함`); return m[0]; }

const w = {};
for (const [re, name] of [
  [/window\.SQ_MG = \{[\s\S]*?\n\};/, 'SQ_MG'],
  [/window\._sqMgJudge = function[\s\S]*?\n\};/, '_sqMgJudge'],
]) new Function('window', grab(re, name))(w);
const auth = { currentUser: { uid: 'a' } };
new Function('window', 'auth', grab(/window\._sqMgClaimGoal = function[\s\S]*?\n\};/, '_sqMgClaimGoal'))(w, auth);

const Z = w.SQ_MG;
const J = (v, players, caught) => w._sqMgJudge(v, players, caught);
const join3 = { a: { nick: 'A' }, b: { nick: 'B' }, c: { nick: 'C' } };

// ── 1) go 구간 → 돌아보며 지금 위치를 스냅샷으로 박는다 ──────────────────
{
  const r = J({ st: 'go', join: join3 }, { a: { x: 50, y: 70 }, b: { x: 40, y: 60 }, c: { x: 60, y: 80 } });
  assert.strictEqual(r.next, 'st');
  assert.deepStrictEqual(r.snap.a, { x: 50, y: 70 });
  assert.deepStrictEqual(r.snap.b, { x: 40, y: 60 });
  assert.strictEqual(Object.keys(r.snap).length, 3, '참가자 전원이 스냅샷에 들어가야 한다');
}

// ── 2) 이미 탈락한 사람은 스냅샷에 안 들어간다(계속 판정할 이유가 없다) ──
{
  const r = J({ st: 'go', join: join3, out: { b: 1 } }, { a: { x: 50, y: 70 }, b: { x: 40, y: 60 }, c: { x: 60, y: 80 } });
  assert(!('b' in r.snap), '탈락자가 스냅샷에 있다');
  assert.strictEqual(Object.keys(r.snap).length, 2);
}

// ── 3) 정지 구간: 안 움직이면 안 걸린다 ─────────────────────────────────
{
  const snap = { a: { x: 50, y: 70 }, b: { x: 40, y: 60 } };
  const r = J({ st: 'st', join: join3, snap }, { a: { x: 50, y: 70 }, b: { x: 40, y: 60 } });
  assert.strictEqual(r.next, 'go');
  assert.strictEqual(Object.keys(r.out).length, 0, '가만히 있었는데 걸렸다');
}

// ── 4) 허용치 안쪽 흔들림은 봐준다 / 넘으면 걸린다 ──────────────────────
{
  const snap = { a: { x: 50, y: 70 }, b: { x: 40, y: 60 } };
  const tiny = Z.MOVE_TOL * 0.5, big = Z.MOVE_TOL * 2;
  const r = J({ st: 'st', join: join3, snap },
              { a: { x: 50 + tiny, y: 70 }, b: { x: 40 + big, y: 60 } });
  assert(!r.out.a, `허용치(${Z.MOVE_TOL}) 안쪽 흔들림에 걸렸다`);
  assert(r.out.b, '허용치를 넘게 움직였는데 안 걸렸다');
  assert.strictEqual(r.next, 'go', '아직 남은 사람이 있으면 계속된다');
}

// ── 5) 대각선 이동도 거리로 잰다 (x·y 따로 보면 새어나간다) ─────────────
{
  const d = Z.MOVE_TOL * 0.8;          // 축 하나로는 허용치 안이지만 대각선 거리는 1.13배 → 넘는다
  const snap = { a: { x: 50, y: 70 } };
  const r = J({ st: 'st', join: { a: {} }, snap }, { a: { x: 50 + d, y: 70 + d } });
  assert(r.out.a, '대각선으로 빠져나갔다 (x·y 를 따로 보면 이렇게 샌다)');
}

// ── 6) 결승선에 닿으면 이긴다 ───────────────────────────────────────────
{
  const snap = { a: { x: 50, y: Z.GOAL_Y - 1 }, b: { x: 40, y: 60 } };
  const r = J({ st: 'st', join: { a: {}, b: {} }, snap },
              { a: { x: 50, y: Z.GOAL_Y - 1 }, b: { x: 40, y: 60 } });
  assert.strictEqual(r.next, 'end');
  assert.strictEqual(r.win, 'a');
}

// ── 7) ★결승선에 있어도 움직이다 걸리면 진다 (판정 순서가 중요) ─────────
{
  const snap = { a: { x: 50, y: 60 }, b: { x: 40, y: 60 } };
  const r = J({ st: 'st', join: { a: {}, b: {} }, snap },
              { a: { x: 50, y: Z.GOAL_Y - 1 }, b: { x: 40, y: 60 } });   // a 가 정지 중에 결승선까지 뛰었다
  assert(r.out.a, '정지 구간에 뛰어서 결승선에 갔는데 안 걸렸다');
  assert.notStrictEqual(r.win, 'a', '걸린 사람이 우승했다');
}

// ── 8) 전원 탈락이면 술래 승리로 끝난다 ─────────────────────────────────
{
  const snap = { a: { x: 50, y: 70 } };
  const r = J({ st: 'st', join: { a: {} }, snap }, { a: { x: 50 + Z.MOVE_TOL * 3, y: 70 } });
  assert.strictEqual(r.next, 'end');
  assert.strictEqual(r.win, null, '전원 탈락인데 우승자가 있다');
}

// ── 9) 위치가 안 온 사람(접속 끊김)은 걸지 않는다 ───────────────────────
{
  const snap = { a: { x: 50, y: 70 }, b: { x: 40, y: 60 } };
  const r = J({ st: 'st', join: join3, snap }, { a: { x: 50, y: 70 } });   // b 의 위치가 없다
  assert(!r.out.b, '위치가 안 온 사람을 탈락시켰다(끊긴 사람이 억울해진다)');
}

// ── 10) 로비 등 다른 상태에서는 아무 판정도 하지 않는다 ─────────────────
assert.strictEqual(J({ st: 'lb', join: join3 }, {}), null);
assert.strictEqual(J({ st: 'end', join: join3 }, {}), null);

// ── 11) 같은 입력이면 같은 답 — 두 진행자가 동시에 써도 결과가 같아야 한다 ──
{
  const v = { st: 'st', join: join3, snap: { a: { x: 50, y: 70 }, b: { x: 40, y: 60 }, c: { x: 60, y: 80 } } };
  const p = { a: { x: 50, y: 70 }, b: { x: 44, y: 60 }, c: { x: 60, y: 80 } };
  assert.deepStrictEqual(J(v, p), J(v, p), '같은 입력에 다른 답이 나온다 — 승계가 사고로 이어진다');
}


// ── 12) ★탭 이동 대응: 정지 중에 걷고 있으면 걸린다 ─────────────────────
//   스쿼드 필드는 탭하면 그 순간 위치가 목적지로 확정된다. 위치만 보면
//   "캐릭터는 눈앞에서 걸어가는데 안 걸리는" 상태가 된다 — 게임이 성립하지 않는다.
{
  const snap = { a: { x: 50, y: 70 } };
  const r = J({ st: 'st', join: { a: {} }, snap }, { a: { x: 50, y: 70, moving: true } });
  assert(r.out.a, '정지 구간에 걷고 있는데 안 걸렸다 (탭 이동의 핵심 케이스)');
}

// ── 13) 훑어서 모은 사람도 걸린다 (짧은 걸음은 구간 중간에 끝난다) ───────
{
  const snap = { a: { x: 50, y: 70 }, b: { x: 40, y: 60 } };
  const now = { a: { x: 50, y: 70, moving: false }, b: { x: 40, y: 60, moving: false } };
  const r0 = J({ st: 'st', join: { a: {}, b: {} }, snap }, now);
  assert(!r0.out.a && !r0.out.b, '마지막 순간만 보면 짧은 걸음을 놓친다(전제 확인)');
  const r1 = J({ st: 'st', join: { a: {}, b: {} }, snap }, now, { a: 1 });
  assert(r1.out.a, '구간 중간에 걷던 사람을 못 잡았다');
  assert(!r1.out.b, '가만히 있던 사람까지 잡았다');
}

// ── 14) 돌아보는 순간 걷고 있던 사람은 그때부터 걸린 것으로 담는다 ──────
{
  const r = J({ st: 'go', join: { a: {}, b: {} } },
              { a: { x: 50, y: 70, moving: true }, b: { x: 40, y: 60, moving: false } });
  assert.strictEqual(r.next, 'st');
  assert(r.movingNow.a, '돌아봤는데 걷고 있던 사람이 안 담겼다');
  assert(!r.movingNow.b, '가만히 있던 사람이 담겼다');
  assert(r.snap.a && r.snap.b, '스냅샷은 전원 그대로 찍혀야 한다');
}

// ── 15) 멈춰 있으면(moving:false, 위치 동일) 절대 안 걸린다 ──────────────
{
  const snap = { a: { x: 50, y: 70 } };
  const r = J({ st: 'st', join: { a: {} }, snap }, { a: { x: 50, y: 70, moving: false } }, {});
  assert(!r.out.a, '가만히 있었는데 걸렸다 — 이게 제일 나쁜 버그다');
}

// ── 16) ★결승선에 실제로 닿을 수 있는가 ────────────────────────────────
//   9-02에 GOAL_Y 를 16 으로 뒀는데 캐릭터 이동 범위가 y 55~92 라 **닿을 방법이 없었다.**
//   아무도 못 이기고 전원 탈락으로만 끝나는 게임이 될 뻔했다. 숫자를 바꿀 때 여기서 걸린다.
assert(typeof Z.WALK_TOP === 'number', 'WALK_TOP 이 없다 — 이동 범위를 안 넓히면 결승선에 못 닿는다');
assert(Z.WALK_TOP <= Z.GOAL_Y,
  `결승선에 닿을 수 없다: 올라갈 수 있는 최고점 y=${Z.WALK_TOP} 인데 우승 조건은 y<=${Z.GOAL_Y}`);
assert(Z.GOAL_Y < 55, '결승선이 평소 이동범위(y>=55) 안에 있으면 시작하자마자 이긴다');

// ── 17) ★함수 이름을 타이머 번호로 덮어쓰지 않는가 ─────────────────────
//   9-02 로비 타이머를 `window._sqMgTick = setInterval(...)` 로 잡았는데 판정 함수 이름도 _sqMgTick 이었다.
//   함수가 숫자로 덮여 '돌아보기'가 영영 안 불렸다(대표: "무궁화꽃이 피었습니다~ 여기서 안 바뀜").
for (const fn of ['_sqMgTick', '_sqMgArm', '_sqMgScan', '_sqMgJudge', '_sqMgPaint', '_sqMgApplyVis']) {
  const defs = (src.match(new RegExp('window\.' + fn + ' = ', 'g')) || []).length;
  assert.strictEqual(defs, 1, `window.${fn} 대입이 ${defs}곳 — 함수 하나만 있어야 한다(타이머 번호로 덮이면 게임이 멈춘다)`);
}

// ── 18) ★돌아보기 전에 결승선을 넘었으면 걷고 있었어도 승리 ─────────────
//   9-02 대표: "돌아보기 전에 선 넘었는데 죽었다고 판정". 결승선 판정이 정지 구간 끝에서만 돌아서였다.
{
  const r = J({ st: 'go', join: { a: {}, b: {} } }, { a: { x: 50, y: Z.GOAL_Y - 1, moving: true }, b: { x: 40, y: 60, moving: true } });
  assert.strictEqual(r.next, 'end', '돌아보는 순간 결승선 넘은 사람이 있으면 끝나야 한다');
  assert.strictEqual(r.win, 'a', '걷고 있었어도 이미 넘었으면 승리');
}

// ── 19) ★내 기기에서 선을 넘는 프레임에 즉시 go→ov 를 청구한다 ─────────
{
  let written = null, calls = 0;
  const cur = { g: 'mg', st: 'go', join: { a: {}, b: {} }, out: null, host: 'b', t: 10, dl: 20 };
  w._sqMgV = cur; w._sqMgGoalSent = null;
  w._sqMgRef = sid => sid; w._sqMgNow = () => 1000;
  w._rt = { runTransaction: (ref, fn) => { calls++; written = fn({ ...cur }); return Promise.resolve(); } };
  assert.strictEqual(w._sqMgClaimGoal('room', { y: Z.GOAL_Y, moving: true }), true, '선을 넘은 프레임에 청구하지 않았다');
  assert.strictEqual(calls, 1, '결승 트랜잭션이 실행되지 않았다');
  assert.strictEqual(written.st, 'ov');
  assert.strictEqual(written.win, 'a');
  assert.strictEqual(written.dl, 1000 + Z.OVER_MS);
  assert.strictEqual(w._sqMgClaimGoal('room', { y: Z.GOAL_Y - 1 }), true);
  assert.strictEqual(calls, 1, '같은 구간에서 결승 트랜잭션을 중복 실행했다');
}

// ── 20) 돌아본 뒤(st)나 선 앞에서는 로컬 결승을 허용하지 않는다 ─────────
{
  let calls = 0;
  w._rt = { runTransaction: () => { calls++; return Promise.resolve(); } };
  w._sqMgGoalSent = null; w._sqMgV = { g: 'mg', st: 'st', join: { a: {} }, t: 11, dl: 21 };
  assert.strictEqual(w._sqMgClaimGoal('room', { y: Z.GOAL_Y - 1 }), false);
  w._sqMgV = { g: 'mg', st: 'go', join: { a: {} }, t: 12, dl: 22 };
  assert.strictEqual(w._sqMgClaimGoal('room', { y: Z.GOAL_Y + 0.1 }), false);
  assert.strictEqual(calls, 0, '부정한 결승 트랜잭션이 실행됐다');
}

// ── 21) 참가자가 아니거나 이미 탈락했으면 결승을 청구하지 않는다 ────────
{
  let calls = 0;
  w._rt = { runTransaction: () => { calls++; return Promise.resolve(); } };
  w._sqMgGoalSent = null; w._sqMgV = { g: 'mg', st: 'go', join: { b: {} }, t: 13, dl: 23 };
  assert.strictEqual(w._sqMgClaimGoal('room', { y: Z.GOAL_Y }), false);
  w._sqMgV = { g: 'mg', st: 'go', join: { a: {} }, out: { a: 1 }, t: 14, dl: 24 };
  assert.strictEqual(w._sqMgClaimGoal('room', { y: Z.GOAL_Y }), false);
  assert.strictEqual(calls, 0);
}

console.log('mugung-core: 21개 항목 전부 통과');
