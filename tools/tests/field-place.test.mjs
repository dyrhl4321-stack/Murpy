// 우리 센터 머피들 배치 순수함수 테스트 — index.html에서 mwFieldPlace 추출해 검증
// 실행: node tools/tests/field-place.test.mjs
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
const m = src.match(/window\.mwFieldPlace = function[\s\S]*?\n};/);
assert(m, 'index.html에서 mwFieldPlace를 찾지 못함');
const w = {};
new Function('window', m[0])(w);
const place = w.mwFieldPlace;

const uids = Array.from({ length: 24 }, (_, i) => 'uid' + (i * 7 + 3));
const day = '20260715';

// 1) 결정적: 같은 입력 → 같은 결과 (입력 순서 무관)
const a = place(uids, day);
const b = place([...uids].reverse(), day);
assert.deepStrictEqual(a, b, '입력 순서에 따라 결과가 달라짐');
assert.deepStrictEqual(place(uids, day), a, '재호출 시 결과 불일치');

// 2) 날짜가 바뀌면 배치도 바뀜 (최소 한 명 이상)
const c = place(uids, '20260716');
assert(uids.some(u => a[u].x !== c[u].x || a[u].y !== c[u].y), '날짜가 바뀌어도 배치 동일');

// 3) 안전영역 경계 (x 16~76%, y 56~86%)
for (const u of uids) {
  assert(a[u].x >= 16 && a[u].x <= 76, `x 범위 밖: ${u} ${a[u].x}`);
  assert(a[u].y >= 56 && a[u].y <= 86, `y 범위 밖: ${u} ${a[u].y}`);
}

// 4) 겹침 없음: 24명 전원 서로 다른 셀 → 최소 간격 보장 (셀폭의 20% 이상)
const pts = uids.map(u => a[u]);
for (let i = 0; i < pts.length; i++) for (let j = i + 1; j < pts.length; j++) {
  const dx = pts[i].x - pts[j].x, dy = pts[i].y - pts[j].y;
  assert(Math.sqrt(dx * dx + dy * dy) > 2, `너무 가까움: ${i}-${j} (${dx},${dy})`);
}

// 5) 정원 초과(30명)에도 예외 없이 동작
const many = Array.from({ length: 30 }, (_, i) => 'u' + i);
const r = place(many, day);
assert(Object.keys(r).length === 30);

console.log('field-place.test.mjs: 배치 결정성·경계·간격·초과 전부 통과 ✓');
