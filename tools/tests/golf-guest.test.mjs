// 골프 스윙 게스트 링크 — 순수함수 테스트 (index.html 에서 추출해 검증)
// 실행: node tools/tests/golf-guest.test.mjs
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';
const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
function grab(re, name) { const m = src.match(re); assert(m, `index.html에서 ${name}를 찾지 못함`); return m[0]; }
const w = {};
new Function('window', grab(/window\.GOLF = \{[\s\S]*?\n\};/, 'GOLF'))(w);
new Function('window', grab(/window\.golfParseLink = function[\s\S]*?\n\};/, 'golfParseLink'))(w);
new Function('window', grab(/window\.golfMakeLink = function[\s\S]*?\n\};/, 'golfMakeLink'))(w);

let r = w.golfParseLink('?game=golf&nick=%ED%8C%A8%EC%88%98%ED%98%84&s=120');
assert.strictEqual(r.on, true); assert.strictEqual(r.nick, '패수현'); assert.strictEqual(r.score, 120);
assert.strictEqual(w.golfParseLink('').on, false);
assert.strictEqual(w.golfParseLink('?room=abc').on, false, '방 초대 링크를 골프가 가로챈다');
assert.strictEqual(w.golfParseLink('?game=dodge&s=3').on, false, '덤벨 링크를 골프가 가로챈다');
assert.strictEqual(w.golfParseLink('?game=golf&s=999999').score, w.GOLF.MAX_SCORE);
assert.strictEqual(w.golfParseLink('?game=golf&s=-5').score, 0);
assert.strictEqual(w.golfParseLink('?game=golf&s=abc').score, 0);
const link = w.golfMakeLink('패수현', 5000);
assert(link.startsWith('https://murpy.app/?game=golf&s=' + w.GOLF.MAX_SCORE + '&nick='), link);
assert.strictEqual(w.golfParseLink(link.slice(link.indexOf('?'))).nick, '패수현');
console.log('golf-guest: OK');
