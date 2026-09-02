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

console.log('mugung-core: 15개 항목 전부 통과');
