// OX 퀴즈 문제 은행 — 데이터 무결성 테스트 · 9-02
// 실행: node tools/tests/quiz-bank.test.mjs
//
// ★왜 있나: 9-02에 문제를 99개 새로 넣었다(102 → 201). 사람이 손으로 쓴 데이터라
//   정답이 'O'/'X' 가 아니거나, 해설이 비었거나, 같은 문제가 두 번 들어가기 쉽다.
//   그런 건 폰으로 한 판 돌려도 그 문제가 안 뽑히면 안 걸린다. 여기서 전수로 본다.
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
function grab(re, name) { const m = src.match(re); assert(m, `index.html에서 ${name}를 찾지 못함`); return m[0]; }

const w = {};
for (const [re, name] of [
  [/window\.SQ_QZ = \{[^\n]*\n/, 'SQ_QZ'],
  [/window\.SQ_QUIZ_COMMON = \[[\s\S]*?\n\];/, 'SQ_QUIZ_COMMON'],
  [/window\.SQ_QUIZ_BY_TYPE = \{[\s\S]*?\n\};/, 'SQ_QUIZ_BY_TYPE'],
]) new Function('window', grab(re, name))(w);

const banks = [['공통', w.SQ_QUIZ_COMMON], ...Object.entries(w.SQ_QUIZ_BY_TYPE)];
const allQ = new Map();
let total = 0;

for (const [name, bank] of banks) {
  assert(Array.isArray(bank) && bank.length, `${name} 은행이 비었다`);
  bank.forEach((it, i) => {
    const at = `${name}[${i}]`;
    assert(it && typeof it === 'object', `${at} 항목이 객체가 아니다`);
    assert(it.d === 1 || it.d === 2, `${at} 난이도(d)가 1/2 가 아니다: ${JSON.stringify(it.d)}`);
    assert(typeof it.q === 'string' && it.q.trim().length >= 6, `${at} 문제가 비었거나 너무 짧다`);
    assert(it.a === 'O' || it.a === 'X', `${at} 정답이 'O'/'X' 가 아니다: ${JSON.stringify(it.a)}`);
    assert(typeof it.w === 'string' && it.w.trim().length >= 4, `${at} 해설이 비었다`);
    // 문제 문장이 겹치면 한 판에 같은 말이 두 번 나올 수 있다
    const key = it.q.replace(/\s+/g, '');
    assert(!allQ.has(key), `문제가 중복이다:\n  ${at}\n  ${allQ.get(key)}\n  "${it.q}"`);
    allQ.set(key, at);
    total++;
  });
}

// 한 판 구성이 실제로 가능한지 — 앞 4(기본) 뒤 6(어려움)
const cnt = (bank, d) => bank.filter(x => x.d === d).length;
assert(cnt(w.SQ_QUIZ_COMMON, 1) >= 2, '공통 기본 문제가 2개 미만');
assert(cnt(w.SQ_QUIZ_COMMON, 2) >= 4, '공통 어려움 문제가 4개 미만');
for (const [tk, bank] of Object.entries(w.SQ_QUIZ_BY_TYPE)) {
  assert(cnt(bank, 1) >= 2, `${tk} 기본 문제가 2개 미만 — 한 판을 못 채운다`);
  assert(cnt(bank, 2) >= 2, `${tk} 어려움 문제가 2개 미만 — 한 판을 못 채운다`);
  // ★중복 방지가 의미가 있으려면 한 판에 쓰는 수의 두 배는 있어야 한다(두 판치를 뺀다)
  assert(cnt(bank, 1) >= 4 && cnt(bank, 2) >= 4,
    `${tk} 은행이 얕다(기본 ${cnt(bank, 1)} · 어려움 ${cnt(bank, 2)}) — 두 판이면 바닥나 '아는 문제'가 된다`);
}

// O 와 X 가 한쪽으로 심하게 쏠리면 찍어서 맞힌다
let o = 0, x = 0;
for (const [, bank] of banks) bank.forEach(it => { it.a === 'O' ? o++ : x++; });
const ratio = o / (o + x);
assert(ratio > 0.35 && ratio < 0.65, `정답이 한쪽으로 쏠렸다 (O ${o} · X ${x} = ${(ratio * 100).toFixed(0)}%)`);

// ★난이도별로도 본다 — 한 판의 뒤 6문제가 전부 d:2 라, 여기가 쏠리면
//   '무조건 O' 찍기로 어려운 구간이 통째로 뚫린다(9-02에 68%까지 쏠렸던 적이 있다).
for (const d of [1, 2]) {
  let dO = 0, dx = 0;
  for (const [, bank] of banks) bank.filter(it => it.d === d).forEach(it => { it.a === 'O' ? dO++ : dx++; });
  const r = dO / (dO + dx);
  assert(r > 0.4 && r < 0.6, `난이도 ${d} 정답이 쏠렸다 (O ${dO} · X ${dx} = ${(r * 100).toFixed(0)}%)`);
}

console.log(`quiz-bank: 문제 ${total}개 (공통 ${w.SQ_QUIZ_COMMON.length} · 종목 ${Object.keys(w.SQ_QUIZ_BY_TYPE).length}종) · O ${o} X ${x} · 전부 통과`);
