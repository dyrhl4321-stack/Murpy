// 도감 보너스 판정 순수함수 테스트 — index.html에서 dogamBonusDue를 추출해 검증
// 실행: node tools/tests/dogam-bonus.test.mjs
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
const m = src.match(/window\.dogamBonusDue = function[\s\S]*?\n};/);
assert(m, 'index.html에서 dogamBonusDue를 찾지 못함');
const w = {};
new Function('window', m[0])(w);
const due = w.dogamBonusDue;

const keys = r => r.map(d => d.key);
const total = r => r.reduce((s, d) => s + d.amount, 0);

// 미달
assert.deepStrictEqual(due(0, {}), []);
assert.deepStrictEqual(due(4, {}), []);
// 단계 도달
assert.deepStrictEqual(keys(due(5, {})), ['b5']);
assert.strictEqual(due(5, {})[0].amount, 20);
assert.deepStrictEqual(keys(due(9, {})), ['b5']);
assert.deepStrictEqual(keys(due(10, {})), ['b5', 'b10']);
assert.deepStrictEqual(keys(due(20, {})), ['b5', 'b10', 'b20']);
assert.strictEqual(total(due(20, {})), 170);
// 1회성: 이미 받은 단계는 제외
assert.deepStrictEqual(keys(due(12, { b5: true })), ['b10']);
assert.deepStrictEqual(due(12, { b5: true, b10: true }), []);
assert.deepStrictEqual(due(25, { b5: true, b10: true, b20: true }), []);
// 중간 건너뛴 계정도 소급 지급
assert.deepStrictEqual(keys(due(20, { b10: true })), ['b5', 'b20']);
// claimed 미전달(undefined) 허용
assert.deepStrictEqual(keys(due(6)), ['b5']);

console.log('dogam-bonus.test.mjs: 12개 단언 전부 통과 ✓');
