// node tools/test/test_eval_hidden.mjs
import assert from 'node:assert';
import { evalHidden } from './eval_hidden_ref.mjs';

const now = new Date('2026-07-27T12:00');

// 교주: 최근 8주 같은 요일 6회 → cult(그 요일). 기대 요일은 base로부터 동적 계산.
const base = new Date('2026-07-21T09:00');
const cultCk = [];
for (let i = 0; i < 6; i++) { const d = new Date(base); d.setDate(d.getDate() - i * 7); cultCk.push({ centerId: 'c1', day: 'x', at: new Date(d) }); }
const expW = '일월화수목금토'[base.getDay()];
assert.deepEqual(evalHidden(cultCk, now), [{ id: 'cult', weekday: expW }], '교주');

// 소믈리에: 서로 다른 센터 5곳
const somm = [1, 2, 3, 4, 5].map(i => ({ centerId: 'c' + i, day: 'x', at: new Date('2026-07-01T09:00') }));
assert.deepEqual(evalHidden(somm, now), [{ id: 'somm' }], '소믈리에');

// 좀비: 31일 공백 후 복귀
const D = (s) => ({ centerId: 'z', day: s, at: new Date(+s.slice(0, 4), +s.slice(4, 6) - 1, +s.slice(6, 8), 9) });
assert.deepEqual(evalHidden([D('20260601'), D('20260702')], now), [{ id: 'zombie' }], '좀비');

// 아무 조건 미충족: 빈 배열
assert.deepEqual(evalHidden([{ centerId: 'a', day: '20260727', at: now }], now), [], '미충족');

console.log('ok — 4 케이스 통과');
