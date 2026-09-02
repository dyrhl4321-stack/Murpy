// 같이 그리기 저장 포맷: 옛 0~6 그림과 새 0~34 색이 모두 한 글자씩 왕복해야 한다.
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
const hit = src.match(/window\._mwPxV = function[\s\S]*?\n\};/);
assert(hit, 'index.html에서 _mwPxV 디코더를 찾지 못함');

const w = {};
new Function('window', hit[0])(w);
const encode = values => values.map(v => (v || 0).toString(36)).join('');
const decode = px => Array.from({ length: px.length }, (_, i) => w._mwPxV(px, i));

const allColors = Array.from({ length: 1024 }, (_, i) => i % 35);
const encoded = encode(allColors);
assert.strictEqual(encoded.length, 1024, '새 저장값이 픽셀당 한 글자가 아니다');
assert.deepStrictEqual(decode(encoded), allColors, '0~34 색 왕복이 깨졌다');

const legacy = Array.from({ length: 1024 }, (_, i) => i % 7).join('');
assert.deepStrictEqual(decode(legacy), Array.from({ length: 1024 }, (_, i) => i % 7), '옛 0~6 그림 호환이 깨졌다');

const encoders = src.match(/J\.px\.map\(function \(v\) \{ return \(v \|\| 0\)\.toString\(36\); \}\)\.join\(''\)/g) || [];
assert.strictEqual(encoders.length, 2, '같이 그리기 저장 인코더 두 곳 중 base36 누락이 있다');

console.log('art-codec: base36 0~34 · 옛 0~6 · 인코더 2곳 통과');
