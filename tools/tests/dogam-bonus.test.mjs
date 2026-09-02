// 도감 보너스 판정 순수함수 테스트 — index.html에서 DOGAM_TIERS + dogamBonusDue를 추출해 검증
// 실행: node tools/tests/dogam-bonus.test.mjs
//
// ★9-02 에 지급값이 DOGAM_TIERS 단일 출처로 바뀌었는데(50/100/250 인상, 대표 지시)
//   이 테스트는 옛 하드코딩 값(20/50/100)과 옛 함수 모양을 보고 있어 깨져 있었다(9-03 수리).
//   금액을 여기 다시 적지 않는다 — 그 어긋남이 원래 사고의 원인이다. 값은 배열에서 읽고,
//   테스트는 **판정 로직**(도달·1회성·소급·미전달 허용)만 못박는다.
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
const grab = (re, name) => {
  const m = src.match(re);
  assert(m, `index.html에서 ${name}를 찾지 못함`);
  return m[0];
};
const w = {};
new Function('window', grab(/window\.DOGAM_TIERS = \[[\s\S]*?\];/, 'DOGAM_TIERS'))(w);
new Function('window', grab(/window\.dogamBonusDue = function[\s\S]*?\n};/, 'dogamBonusDue'))(w);
const due = w.dogamBonusDue;
const T = w.DOGAM_TIERS;

assert(Array.isArray(T) && T.length >= 3, 'DOGAM_TIERS 가 배열이 아니거나 단계가 모자란다');
T.forEach(t => { assert(Number.isFinite(t[0]) && typeof t[1] === 'string' && Number.isFinite(t[2]), '단계 모양이 [곳수, 키, 금액] 이 아니다'); });
const [n1, k1, a1] = T[0], [n2, k2] = T[1], [n3, k3] = T[2];

const keys = r => r.map(d => d.key);

// 미달
assert.deepStrictEqual(due(0, {}), []);
assert.deepStrictEqual(due(n1 - 1, {}), []);
// 단계 도달 — 금액은 배열 값 그대로 나와야 한다
assert.deepStrictEqual(keys(due(n1, {})), [k1]);
assert.strictEqual(due(n1, {})[0].amount, a1, '지급액이 DOGAM_TIERS 와 다르다');
assert.deepStrictEqual(keys(due(n2 - 1, {})), [k1]);
assert.deepStrictEqual(keys(due(n2, {})), [k1, k2]);
assert.deepStrictEqual(keys(due(n3, {})), [k1, k2, k3]);
assert.strictEqual(due(n3, {}).reduce((s, d) => s + d.amount, 0),
                   T.reduce((s, t) => s + t[2], 0), '전체 합이 단계 합과 다르다');
// 1회성: 이미 받은 단계는 제외
assert.deepStrictEqual(keys(due(n2 + 2, { [k1]: true })), [k2]);
assert.deepStrictEqual(due(n2 + 2, { [k1]: true, [k2]: true }), []);
assert.deepStrictEqual(due(n3 + 5, { [k1]: true, [k2]: true, [k3]: true }), []);
// 중간 건너뛴 계정도 소급 지급
assert.deepStrictEqual(keys(due(n3, { [k2]: true })), [k1, k3]);
// claimed 미전달(undefined) 허용
assert.deepStrictEqual(keys(due(n1 + 1)), [k1]);

console.log('dogam-bonus.test.mjs: 판정 로직 13개 단언 전부 통과 (단계 ' + T.map(t => t[0] + '곳/' + t[2]).join(' · ') + ')');
